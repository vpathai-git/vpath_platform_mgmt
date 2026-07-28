"""OpsService: the guardrail layer every surface goes through.

Order of gates on submit, per docs/PLATFORM_FUNCTIONS.md: verb exists →
RBAC (refusals audited) → typed confirmation for destructive verbs → lock
acquisition → job created and executed. There is no path around this
service; CLI and console are thin clients of it.
"""

from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from _thread import RLock as RLockT

from vpath_platform_mgmt.ops.audit import AuditLog
from vpath_platform_mgmt.ops.engine import EngineAdapter, EngineFailure
from vpath_platform_mgmt.ops.locks import LockManager
from vpath_platform_mgmt.ops.model import (
    DESTRUCTIVE_VERBS,
    ROLE_RANK,
    VERB_ROLE,
    ConfirmationRequiredError,
    Job,
    JobState,
    RefusedError,
    Role,
    UnknownVerbError,
    Verb,
    lock_scope,
)

MAX_JOBS_KEPT = 100


class OpsService:
    """Submits, guards, executes, and reports jobs."""

    def __init__(
        self,
        engine: EngineAdapter,
        locks: LockManager | None = None,
        audit: AuditLog | None = None,
    ) -> None:
        self._engine = engine
        self._locks = locks or LockManager()
        self._audit = audit or AuditLog()
        self._jobs: list[Job] = []
        self._threads: dict[str, threading.Thread] = {}
        self._health: dict[str, object] | None = None
        self._sources: dict[str, dict[str, object]] = {}
        self._mutex = threading.RLock()

    @property
    def engine_name(self) -> str:
        """Which adapter executes verbs (shown in every console view)."""
        return self._engine.name

    def submit(
        self, verb_name: str, app: str, actor: str, role_name: str, confirm: str = ""
    ) -> Job:
        """Run all gates, then start the job. Raises typed ``OpsError``s."""
        verb = self._parse_verb(verb_name)
        role = self._parse_role(role_name, actor, verb_name, app)
        self._check_rbac(verb, role, actor, app)
        self._check_confirmation(verb, confirm)
        scope = lock_scope(verb, app)
        job = Job(verb=verb, app=app, actor=actor, role=role, engine=self._engine.name)
        if scope is not None:
            self._locks.acquire(scope, actor, job.id)
        with self._mutex:
            self._jobs.insert(0, job)
            del self._jobs[MAX_JOBS_KEPT:]
        thread = threading.Thread(
            target=self._run, args=(job, scope), daemon=True, name=f"job-{job.id}"
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

    def _run(self, job: Job, scope: str | None) -> None:
        emit = self._emitter(job)
        with self._mutex:
            job.state = JobState.RUNNING
        if job.engine == "simulated":
            emit("SIMULATED RUN — no real server contact, nothing is deployed")
        try:
            result = self._engine.run(job, emit)
        except EngineFailure as exc:
            self._finish(job, scope, JobState.FAILED, str(exc))
            return
        with self._mutex:
            job.result = result
            if job.verb in (Verb.HEALTH, Verb.REINSTALL) and result is not None:
                self._health = dict(result, at=time.time())
        self._finish(job, scope, JobState.SUCCEEDED, "succeeded")

    def _emitter(self, job: Job) -> "_Emit":
        return _Emit(job, self._mutex)

    def _finish(
        self, job: Job, scope: str | None, state: JobState, message: str
    ) -> None:
        with self._mutex:
            job.state = state
            job.step = "done" if state is JobState.SUCCEEDED else "failed"
            job.log.append(message)
        if scope is not None:
            self._locks.release(scope)
        self._audit.record(
            job.actor, job.role.value, job.verb.value, job.app, state.value
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

    def state(self) -> dict[str, object]:
        """One snapshot for the console: jobs, locks, audit, health, engine."""
        with self._mutex:
            jobs = [job.to_dict() for job in self._jobs]
            health = self._health
        return {
            "engine": self.engine_name,
            "jobs": jobs,
            "locks": self._locks.snapshot(),
            "audit": self._audit.entries(),
            "health": health,
        }


class _Emit:
    """Step emitter bound to a job; safe to call from the worker thread."""

    def __init__(self, job: Job, mutex: RLockT) -> None:
        self._job = job
        self._mutex = mutex

    def __call__(self, step: str) -> None:
        stamp = time.strftime("%H:%M:%S")
        with self._mutex:
            self._job.step = step
            self._job.log.append(f"[{stamp}] {step}")
