"""OpsService: the guardrail layer every surface goes through.

Order of gates on submit, per docs/PLATFORM_FUNCTIONS.md: verb exists →
RBAC (refusals audited) → typed confirmation for destructive verbs → lock
acquisition → job created and executed. There is no path around this
service; CLI and console are thin clients of it.
"""

from __future__ import annotations

import threading
import time

from vpath_platform_mgmt.ops.audit import AuditLog
from vpath_platform_mgmt.ops.engine import EngineAdapter, Reach
from vpath_platform_mgmt.ops import tunnel
from vpath_platform_mgmt.ops.job_runner import JobRunner
from vpath_platform_mgmt.ops.locks import LockManager
from vpath_platform_mgmt.ops.publish import PublishPipeline
from vpath_platform_mgmt.ops.tunnel import TunnelConfig, TunnelError
from vpath_platform_mgmt.ops.model import (
    DESTRUCTIVE_VERBS,
    ROLE_RANK,
    VERB_ROLE,
    ConfirmationRequiredError,
    Job,
    RefusedError,
    Role,
    UnknownVerbError,
    Verb,
    lock_scope,
)

MAX_JOBS_KEPT = 100

# The console polls state every second; probing a tunnelled box that often
# would hammer it. A probe older than this is refreshed inline.
PROBE_TTL = 10.0


class OpsService:
    """Submits, guards, executes, and reports jobs."""

    def __init__(
        self,
        engine: EngineAdapter,
        locks: LockManager | None = None,
        audit: AuditLog | None = None,
        instance_name: str = "",
        tunnel_config: TunnelConfig | None = None,
        publish: PublishPipeline | None = None,
    ) -> None:
        self._engine = engine
        self._locks = locks or LockManager()
        self._audit = audit or AuditLog()
        self._instance = instance_name
        self._tunnel = tunnel_config
        self._publish = publish
        self._reach: Reach | None = None
        self._probe_at = 0.0
        self._jobs: list[Job] = []
        self._threads: dict[str, threading.Thread] = {}
        self._health: dict[str, object] | None = None
        self._sources: dict[str, dict[str, object]] = {}
        self._mutex = threading.RLock()
        self._runner = JobRunner(
            engine=engine,
            locks=self._locks,
            audit=self._audit,
            mutex=self._mutex,
            publish=publish,
            on_health=self._record_health,
        )

    def _record_health(self, health: dict[str, object]) -> None:
        with self._mutex:
            self._health = health

    @property
    def engine_name(self) -> str:
        """Which adapter executes verbs (shown in every console view)."""
        return self._engine.name

    def submit(
        self,
        verb_name: str,
        app: str,
        actor: str,
        role_name: str,
        confirm: str = "",
        payload: dict[str, object] | None = None,
    ) -> Job:
        """Run all gates, then start the job. Raises typed ``OpsError``s."""
        verb = self._parse_verb(verb_name)
        role = self._parse_role(role_name, actor, verb_name, app)
        self._check_rbac(verb, role, actor, app)
        self._check_confirmation(verb, confirm)
        scope = lock_scope(verb, app)
        job = Job(
            verb=verb,
            app=app,
            actor=actor,
            role=role,
            engine=self._engine.name,
            payload=payload,
        )
        if scope is not None:
            self._locks.acquire(scope, actor, job.id)
        with self._mutex:
            self._jobs.insert(0, job)
            del self._jobs[MAX_JOBS_KEPT:]
        thread = threading.Thread(
            target=self._runner.run,
            args=(job, scope),
            daemon=True,
            name=f"job-{job.id}",
        )
        self._threads[job.id] = thread
        thread.start()
        return job

    def _parse_verb(self, verb_name: str) -> Verb:
        try:
            return Verb(verb_name)
        except ValueError as exc:
            raise UnknownVerbError(f"unknown verb '{verb_name}'") from exc

    def _parse_role(self, role_name: str, actor: str, verb: str, app: str) -> Role:
        try:
            return Role(role_name)
        except ValueError as exc:
            self._audit.record(actor, role_name, verb, app, "REFUSED (unknown role)")
            raise RefusedError(f"unknown role '{role_name}'") from exc

    def _check_rbac(self, verb: Verb, role: Role, actor: str, app: str) -> None:
        if ROLE_RANK[role] < ROLE_RANK[VERB_ROLE[verb]]:
            self._audit.record(actor, role.value, verb.value, app, "REFUSED (role)")
            raise RefusedError(
                f"'{verb.value}' requires role {VERB_ROLE[verb].value} — "
                "refused and audited"
            )

    def _check_confirmation(self, verb: Verb, confirm: str) -> None:
        if verb in DESTRUCTIVE_VERBS and confirm != verb.value.upper():
            raise ConfirmationRequiredError(
                f"type {verb.value.upper()} to confirm this destructive action"
            )

    def record_source(
        self, app: str, actor: str, role: str, summary: dict[str, object]
    ) -> None:
        """Audit a source materialization and remember it for the next deploy."""
        source = summary.get("source", {})
        ref = source.get("ref", "?") if isinstance(source, dict) else "?"
        commit = source.get("commit", "?") if isinstance(source, dict) else "?"
        with self._mutex:
            self._sources[app] = summary
        self._audit.record(
            actor,
            role,
            "materialize",
            app,
            f"{summary.get('file_count', 0)} files from {ref}@{str(commit)[:8]}",
        )

    def start_tunnel(self, actor: str, role_name: str) -> str:
        """Open the instance's SSH tunnel. Admin only, and always audited.

        This is the one action that starts a process on the console's host, so
        it is gated exactly like a destructive verb: a refusal is recorded, and
        so is every success.
        """
        role = self._parse_role(role_name, actor, "tunnel", self._instance)
        if role is not Role.ADMIN:
            self._audit.record(
                actor, role.value, "tunnel", self._instance, "REFUSED (role)"
            )
            raise RefusedError("'tunnel' requires role admin — refused and audited")
        if self._tunnel is None:
            raise TunnelError(
                f"instance '{self._instance}' declares no tunnel; it is either "
                "reached directly or the console runs on the box itself"
            )
        outcome = tunnel.start(self._tunnel)
        self._audit.record(actor, role.value, "tunnel", self._instance, outcome)
        with self._mutex:
            self._reach = None  # the next poll must look again, not read a cache
        return outcome

    def installed_apps(self) -> list[str] | None:
        """Apps installed on the server, or ``None`` if the engine cannot say.

        Only a real engine knows the server's installed set; the simulated one
        has no server to ask. ``None`` means *unknown*, which callers must
        render as unknown — never as "not installed", which would invite an
        install of something already running.
        """
        reporter = getattr(self._engine, "installed_apps", None)
        if reporter is None:
            return None
        return [str(name) for name in reporter()]

    def source_of(self, app: str) -> dict[str, object] | None:
        """Provenance of the last source materialized for an app."""
        with self._mutex:
            return self._sources.get(app)

    def wait(self, job_id: str, timeout: float = 10.0) -> None:
        """Block until a job's thread finishes (used by tests and CLI)."""
        thread = self._threads.get(job_id)
        if thread is not None:
            thread.join(timeout)

    def job(self, job_id: str) -> Job | None:
        """Look up one job by id."""
        with self._mutex:
            return next((job for job in self._jobs if job.id == job_id), None)

    def state(self, fresh: bool = False) -> dict[str, object]:
        """One snapshot for the console: jobs, locks, audit, health, instance.

        ``fresh`` bypasses the probe cache — the console's Connect button
        must be able to force a real look at the box, not read a stale verdict.
        """
        with self._mutex:
            jobs = [job.to_dict() for job in self._jobs]
            health = self._health
        return {
            "engine": self.engine_name,
            "instance": self._instance_state(fresh),
            "jobs": jobs,
            "locks": self._locks.snapshot(),
            "audit": self._audit.entries(),
            "health": health,
        }

    def _instance_state(self, fresh: bool) -> dict[str, object]:
        """Name and cached reachability of the instance this engine drives."""
        if fresh or self._reach is None or time.time() - self._probe_at > PROBE_TTL:
            self._reach = self._engine.probe()
            self._probe_at = time.time()
        return {
            "name": self._instance,
            "reachable": self._reach.ok,
            "reason": self._reach.reason,
            "detail": self._reach.detail,
            "checked_at": self._probe_at,
        }
