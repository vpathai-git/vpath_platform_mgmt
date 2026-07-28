"""Behavior tests for the guardrail layer (RBAC, confirm, lifecycle, audit)."""

from __future__ import annotations

import threading

import pytest

from vpath_platform_mgmt.ops import (
    ConfirmationRequiredError,
    EngineFailure,
    JobState,
    LockHeldError,
    OpsService,
    RefusedError,
    SimulatedEngine,
    UnknownVerbError,
)
from vpath_platform_mgmt.ops.engine import StepEmitter
from vpath_platform_mgmt.ops.model import Job


class GateEngine:
    """Engine that blocks until released — makes lock tests deterministic."""

    name = "gate"

    def __init__(self) -> None:
        self.release = threading.Event()

    def run(self, job: Job, emit: StepEmitter) -> dict[str, object] | None:
        emit("waiting")
        assert self.release.wait(timeout=5.0), "gate never released"
        return None


class FailingEngine:
    """Engine whose verbs always fail."""

    name = "failing"

    def run(self, job: Job, emit: StepEmitter) -> dict[str, object] | None:
        emit("about to fail")
        raise EngineFailure("boom: exit 1")


def make_service() -> OpsService:
    return OpsService(SimulatedEngine())


def test_deploy_runs_to_success_and_releases_lock() -> None:
    service = make_service()
    job = service.submit("deploy", "sample-app", "alice", "app-dev")
    service.wait(job.id)
    assert job.state is JobState.SUCCEEDED
    assert service.state()["locks"] == []
    assert any("redeployApp" in line for line in job.log)


def test_refused_verb_for_low_role_is_audited() -> None:
    service = make_service()
    with pytest.raises(RefusedError):
        service.submit("deploy", "sample-app", "sam", "server-dev")
    audit = service.state()["audit"]
    assert audit[0]["result"] == "REFUSED (role)"
    assert audit[0]["actor"] == "sam"


def test_unknown_role_is_refused_and_audited() -> None:
    service = make_service()
    with pytest.raises(RefusedError):
        service.submit("deploy", "sample-app", "eve", "superuser")
    assert service.state()["audit"][0]["result"] == "REFUSED (unknown role)"


def test_unknown_verb_is_rejected() -> None:
    service = make_service()
    with pytest.raises(UnknownVerbError):
        service.submit("teleport", "sample-app", "alice", "admin")


def test_destructive_verb_requires_typed_confirmation() -> None:
    service = make_service()
    with pytest.raises(ConfirmationRequiredError):
        service.submit("reinstall", "server", "root", "admin")
    job = service.submit("reinstall", "server", "root", "admin", confirm="REINSTALL")
    service.wait(job.id)
    assert job.state is JobState.SUCCEEDED


def test_destructive_verb_refused_before_confirmation_check() -> None:
    service = make_service()
    with pytest.raises(RefusedError):
        service.submit("erase", "server", "alice", "app-dev", confirm="ERASE")


def test_same_app_serializes_and_different_app_runs_concurrently() -> None:
    engine = GateEngine()
    service = OpsService(engine)
    first = service.submit("deploy", "sample-app", "alice", "app-dev")
    with pytest.raises(LockHeldError):
        service.submit("deploy", "sample-app", "bob", "app-dev")
    other = service.submit("deploy", "other-app", "bob", "app-dev")
    engine.release.set()
    service.wait(first.id)
    service.wait(other.id)
    assert first.state is JobState.SUCCEEDED
    assert other.state is JobState.SUCCEEDED


def test_cluster_lock_is_exclusive_against_app_jobs() -> None:
    engine = GateEngine()
    service = OpsService(engine)
    service.submit("deploy", "sample-app", "alice", "app-dev")
    with pytest.raises(LockHeldError):
        service.submit("reinstall", "server", "root", "admin", confirm="REINSTALL")
    engine.release.set()


def test_read_verbs_take_no_lock() -> None:
    engine = GateEngine()
    service = OpsService(engine)
    running = service.submit("deploy", "sample-app", "alice", "app-dev")
    health = service.submit("health", "", "sam", "server-dev")
    engine.release.set()
    service.wait(running.id)
    service.wait(health.id)
    assert health.state is JobState.SUCCEEDED


def test_engine_failure_marks_job_failed_and_releases_lock() -> None:
    service = OpsService(FailingEngine())
    job = service.submit("deploy", "sample-app", "alice", "app-dev")
    service.wait(job.id)
    assert job.state is JobState.FAILED
    assert "boom" in job.log[-1]
    assert service.state()["locks"] == []
    assert service.state()["audit"][0]["result"] == "failed"


def test_health_verdict_is_captured_in_state() -> None:
    service = make_service()
    job = service.submit("health", "", "sam", "server-dev")
    service.wait(job.id)
    health = service.state()["health"]
    assert isinstance(health, dict)
    assert health["verdict"] == "healthy"


def test_simulated_jobs_are_labelled_everywhere() -> None:
    """A simulated run must never be mistakable for a real deployment."""
    service = make_service()
    job = service.submit("deploy", "sample-app", "alice", "app-dev")
    service.wait(job.id)
    assert job.engine == "simulated"
    assert job.to_dict()["engine"] == "simulated"
    assert any("SIMULATED RUN" in line for line in job.log)


def test_real_engine_jobs_carry_engine_name_without_simulation_notice() -> None:
    class RealishEngine(SimulatedEngine):
        name = "local"

    service = OpsService(RealishEngine())
    job = service.submit("deploy", "sample-app", "alice", "app-dev")
    service.wait(job.id)
    assert job.to_dict()["engine"] == "local"
    assert not any("SIMULATED RUN" in line for line in job.log)


def test_job_lookup_and_state_shape() -> None:
    service = make_service()
    job = service.submit("build", "sample-app", "alice", "app-dev")
    service.wait(job.id)
    assert service.job(job.id) is job
    assert service.job("nope") is None
    snapshot = service.state()
    assert snapshot["engine"] == "simulated"
    assert snapshot["jobs"][0]["id"] == job.id
