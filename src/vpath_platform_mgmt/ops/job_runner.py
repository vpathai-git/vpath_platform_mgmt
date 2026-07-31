"""Executes one submitted job and reports how it went.

Split out of ``service.py`` along the seam between "how one job actually
runs" (this module) and "the gates and registry every submission goes
through" (``OpsService`` itself), to keep each module under the project's
line limit.

``JobRunner.run`` is what a worker thread's target is bound to; everything
below it exists to guarantee the one thing that thread must never fail to
do -- release the app or cluster lock it holds, on every exit path, typed
failure, catch-all failure, ``_finish`` itself raising, or worse.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from _thread import RLock as RLockT

from vpath_platform_mgmt.ops.app_registry import Generated
from vpath_platform_mgmt.ops.audit import AuditLog
from vpath_platform_mgmt.ops.engine import EngineAdapter, EngineFailure
from vpath_platform_mgmt.ops.locks import LockManager
from vpath_platform_mgmt.ops.model import Job, JobState, Verb
from vpath_platform_mgmt.ops.publish import (
    PublishError,
    PublishPipeline,
    PublishRequest,
)


class _Emit:
    """Step emitter bound to a job; safe to call from the worker thread."""

    def __init__(self, job: Job, mutex: "RLockT") -> None:
        self._job = job
        self._mutex = mutex

    def __call__(self, step: str) -> None:
        stamp = time.strftime("%H:%M:%S")
        with self._mutex:
            self._job.step = step
            self._job.log.append(f"[{stamp}] {step}")


class JobRunner:
    """Runs one job to completion; holds the same collaborators OpsService does.

    Constructed once per ``OpsService`` with references to its engine, lock
    manager, audit log and mutex -- never its own copies -- so a lock this
    runner releases and a job list ``OpsService`` reads stay the same objects.
    """

    def __init__(
        self,
        engine: EngineAdapter,
        locks: LockManager,
        audit: AuditLog,
        mutex: "RLockT",
        publish: PublishPipeline | None,
        on_health: Callable[[dict[str, object]], None],
    ) -> None:
        self._engine = engine
        self._locks = locks
        self._audit = audit
        self._mutex = mutex
        self._publish = publish
        self._on_health = on_health

    def run(self, job: Job, scope: str | None) -> None:
        """Execute one job, releasing its lock whatever happens inside.

        The release lives here rather than in ``_finish`` because a lock that
        outlives its job blocks every later publish *and* deploy of that app
        until the process restarts — the one failure the worker thread must
        not be able to cause.
        """
        try:
            self._execute(job)
        finally:
            if scope is not None:
                self._locks.release(scope)

    def _execute(self, job: Job) -> None:
        """Run the verb and record how it went; nothing escapes this method.

        The typed failures report exactly as they always have. The wider
        catch is a backstop, not a replacement: the publish path reaches
        ``gh`` not being installed, a subprocess timeout and a corrupt
        provenance file, none of which are ``EngineFailure``, and a thread
        that dies on one of those leaves the job RUNNING forever with no
        message at all.
        """
        emit = self._emitter(job)
        with self._mutex:
            job.state = JobState.RUNNING
        if job.engine == "simulated":
            emit("SIMULATED RUN — no real server contact, nothing is deployed")
        try:
            if job.verb is Verb.PUBLISH:
                result = self._run_publish(job, emit)
            else:
                result = self._engine.run(job, emit)
        except (EngineFailure, PublishError) as exc:
            self._finish(job, JobState.FAILED, str(exc))
            return
        except Exception as exc:
            self._finish(job, JobState.FAILED, f"{type(exc).__name__}: {exc}")
            return
        with self._mutex:
            job.result = result
            if job.verb in (Verb.HEALTH, Verb.REINSTALL) and result is not None:
                self._on_health(dict(result, at=time.time()))
        self._finish(job, JobState.SUCCEEDED, "succeeded")

    def _run_publish(self, job: Job, emit: "_Emit") -> dict[str, object] | None:
        """Publish is the one verb an engine cannot serve: it spans two.

        Rendering runs on the local engine and installing on the GitOps one,
        so the pipeline holds both. A console configured for neither says so
        rather than failing somewhere less obvious.
        """
        if self._publish is None:
            raise PublishError(
                "publish needs both a server checkout and the Deploy-of-Record; "
                "this console is configured for neither, so it runs on the box's "
                "Ops API"
            )
        payload = job.payload or {}
        generate = payload.get("generate")
        if generate is not None and not isinstance(generate, Generated):
            raise PublishError(
                "publish: 'generate' reached the pipeline as "
                f"{type(generate).__name__}, not the registry's Generated — "
                "the surface that submitted this job did not marshal it"
            )
        request = PublishRequest(
            url=str(payload.get("url", "")),
            ref=str(payload.get("ref", "") or "main"),
            name=job.app,
            path=str(payload.get("path", "")),
            generate=generate,
            replace=bool(payload.get("replace", False)),
        )
        return self._publish.run(request, job.actor, job.role, emit)

    def _emitter(self, job: Job) -> "_Emit":
        return _Emit(job, self._mutex)

    def _finish(self, job: Job, state: JobState, message: str) -> None:
        with self._mutex:
            job.state = state
            job.step = "done" if state is JobState.SUCCEEDED else "failed"
            job.log.append(message)
        self._audit.record(
            job.actor, job.role.value, job.verb.value, job.app, state.value
        )
