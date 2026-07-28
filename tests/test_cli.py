"""CLI integration tests: `vpath` driving the real API in-process.

The whole stack is exercised — Typer command → OpsClient → FastAPI app →
OpsService → SimulatedEngine — so CLI and console are proven to share one
behavior (decision 3).
"""

from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from vpath_platform_mgmt.api import create_app
from vpath_platform_mgmt.cli import main
from vpath_platform_mgmt.ops import OpsService, SimulatedEngine

runner = CliRunner()


@pytest.fixture()
def wired(monkeypatch: pytest.MonkeyPatch) -> OpsService:
    """Point the CLI at an in-process API; returns the backing service."""
    service = OpsService(SimulatedEngine())
    test_client = TestClient(create_app(service))
    monkeypatch.setattr(main, "make_http_client", lambda url: test_client)
    monkeypatch.setenv("VPATH_MGMT_ACTOR", "alice")
    monkeypatch.setenv("VPATH_MGMT_ROLE", "app-dev")
    return service


def test_deploy_streams_steps_and_exits_zero(wired: OpsService) -> None:
    result = runner.invoke(main.app, ["deploy", "sample-app"])
    assert result.exit_code == 0, result.output
    assert "accepted" in result.output
    assert "redeployApp" in result.output


def test_refused_role_exits_3(
    wired: OpsService, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("VPATH_MGMT_ROLE", "server-dev")
    result = runner.invoke(main.app, ["deploy", "sample-app"])
    assert result.exit_code == main.EXIT_REFUSED
    assert "refused" in result.output


def test_reinstall_without_confirmation_exits_2(
    wired: OpsService, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("VPATH_MGMT_ROLE", "admin")
    result = runner.invoke(main.app, ["reinstall"])
    assert result.exit_code == main.EXIT_CONFIG
    assert "REINSTALL" in result.output


def test_reinstall_with_confirmation_succeeds(
    wired: OpsService, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("VPATH_MGMT_ROLE", "admin")
    result = runner.invoke(main.app, ["reinstall", "--confirm", "REINSTALL"])
    assert result.exit_code == 0, result.output


def test_status_shows_engine_jobs_and_locks(wired: OpsService) -> None:
    job = wired.submit("build", "demo", "alice", "app-dev")
    wired.wait(job.id)
    result = runner.invoke(main.app, ["status"])
    assert result.exit_code == 0
    assert "engine: simulated" in result.output
    assert job.id in result.output
    assert "locks: none held" in result.output


def test_health_prints_gate_steps(wired: OpsService) -> None:
    result = runner.invoke(main.app, ["health"])
    assert result.exit_code == 0
    assert "health-check" in result.output


def test_logs_prints_job_log_and_404_maps_to_config_exit(
    wired: OpsService,
) -> None:
    job = wired.submit("build", "demo", "alice", "app-dev")
    wired.wait(job.id)
    ok = runner.invoke(main.app, ["logs", job.id])
    assert ok.exit_code == 0
    assert "buildApp" in ok.output
    missing = runner.invoke(main.app, ["logs", "nope"])
    assert missing.exit_code == main.EXIT_CONFIG


def test_doctor_reports_all_layers(wired: OpsService) -> None:
    result = runner.invoke(main.app, ["doctor"])
    assert result.exit_code == 0, result.output
    assert "overlay: skipped" in result.output
    assert "api: reachable" in result.output
    assert "auth: valid" in result.output
    assert "engine: simulated" in result.output


def test_doctor_names_auth_as_failing_layer(
    wired: OpsService, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("VPATH_MGMT_ACTOR")
    monkeypatch.setenv("VPATH_MGMT_ACTOR", "")
    result = runner.invoke(main.app, ["doctor"])
    assert result.exit_code == main.EXIT_AUTH
    assert "auth: FAILED" in result.output


def test_unreachable_api_maps_to_config_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_connect(url: str) -> httpx.Client:
        transport = httpx.MockTransport(_refuse)
        return httpx.Client(base_url="http://down", transport=transport)

    monkeypatch.setattr(main, "make_http_client", raise_connect)
    monkeypatch.setenv("VPATH_MGMT_ROLE", "app-dev")
    result = runner.invoke(main.app, ["doctor"])
    assert result.exit_code == main.EXIT_CONFIG
    assert "cannot reach" in result.output


def _refuse(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("connection refused", request=request)
