"""Tests for engine adapters: simulated results, local validation + commands."""

from __future__ import annotations

from pathlib import Path

import pytest

from vpath_platform_mgmt.ops import LocalEngine, SimulatedEngine
from vpath_platform_mgmt.ops.engine import ENGINE_COMMANDS, HEALTH_GATES
from vpath_platform_mgmt.ops.model import Job, Role, Verb


def run_collecting(engine: SimulatedEngine, verb: Verb) -> tuple[list[str], object]:
    steps: list[str] = []
    job = Job(verb=verb, app="demo", actor="alice", role=Role.APP_DEV)
    result = engine.run(job, steps.append)
    return steps, result


def test_simulated_build_returns_digest() -> None:
    steps, result = run_collecting(SimulatedEngine(), Verb.BUILD)
    assert steps
    assert isinstance(result, dict)
    assert str(result["digest"]).startswith("sha256:")


def test_simulated_health_passes_all_gates() -> None:
    _, result = run_collecting(SimulatedEngine(), Verb.HEALTH)
    assert isinstance(result, dict)
    assert set(result["gates"]) == set(HEALTH_GATES)  # type: ignore[index]


def test_simulated_deploy_returns_no_result() -> None:
    _, result = run_collecting(SimulatedEngine(), Verb.DEPLOY)
    assert result is None


def test_local_engine_requires_existing_checkout(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="server checkout not found"):
        LocalEngine(tmp_path / "missing")


def test_simulated_engine_is_always_reachable() -> None:
    assert SimulatedEngine().probe().ok is True


def test_local_engine_probe_names_the_missing_checkout(tmp_path: Path) -> None:
    """A red badge must say what broke, not just that something did."""
    from vpath_platform_mgmt.ops.engine import REACH_NO_CHECKOUT

    checkout = tmp_path / "workspace"
    checkout.mkdir()
    engine = LocalEngine(checkout)
    assert engine.probe().ok is True

    checkout.rmdir()
    gone = engine.probe()
    assert gone.ok is False
    assert gone.reason == REACH_NO_CHECKOUT
    assert str(checkout) in gone.detail


def test_local_engine_command_substitutes_app(tmp_path: Path) -> None:
    engine = LocalEngine(tmp_path)
    assert engine.command(Verb.DEPLOY, "my-app") == [
        "./gradlew",
        "redeployApp",
        "-Papp=my-app",
    ]
    assert engine.command(Verb.UNINSTALL, "my-app")[-1] == "my-app"


def test_every_verb_has_an_engine_command() -> None:
    assert set(ENGINE_COMMANDS) == set(Verb)


def test_local_engine_runs_real_subprocess_and_fails_loud(tmp_path: Path) -> None:
    engine = LocalEngine(tmp_path)
    job = Job(verb=Verb.STATUS, app="", actor="alice", role=Role.ADMIN)
    steps: list[str] = []
    with pytest.raises(Exception):
        engine.run(job, steps.append)
    assert steps, "command line must be emitted before execution"
