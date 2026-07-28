"""API contract tests: auth, verb submission, error mapping, console page."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from vpath_platform_mgmt.api import create_app
from vpath_platform_mgmt.api.server import build_engine
from vpath_platform_mgmt.ops import OpsService, SimulatedEngine

APP_DEV = {"X-Dev-Actor": "alice", "X-Dev-Role": "app-dev"}
ADMIN = {"X-Dev-Actor": "root", "X-Dev-Role": "admin"}
SERVER_DEV = {"X-Dev-Actor": "sam", "X-Dev-Role": "server-dev"}


@pytest.fixture()
def client() -> TestClient:
    return TestClient(create_app(OpsService(SimulatedEngine())))


def test_requests_without_dev_headers_are_401(client: TestClient) -> None:
    assert client.get("/api/state").status_code == 401
    assert client.post("/api/jobs", json={"verb": "deploy"}).status_code == 401


def test_console_page_serves_and_names_the_engine(client: TestClient) -> None:
    page = client.get("/")
    assert page.status_code == 200
    assert "vpath console" in page.text


def test_submit_deploy_returns_job_id_and_state_lists_it(
    client: TestClient,
) -> None:
    accepted = client.post(
        "/api/jobs", json={"verb": "deploy", "app": "demo"}, headers=APP_DEV
    )
    assert accepted.status_code == 202
    job_id = accepted.json()["job"]
    state = client.get("/api/state", headers=APP_DEV).json()
    assert state["engine"] == "simulated"
    assert any(job["id"] == job_id for job in state["jobs"])


def test_refused_role_maps_to_403(client: TestClient) -> None:
    response = client.post(
        "/api/jobs", json={"verb": "deploy", "app": "demo"}, headers=SERVER_DEV
    )
    assert response.status_code == 403
    assert "refused" in response.json()["detail"]


def test_missing_confirmation_maps_to_400(client: TestClient) -> None:
    response = client.post(
        "/api/jobs", json={"verb": "erase", "app": "server"}, headers=ADMIN
    )
    assert response.status_code == 400
    assert "ERASE" in response.json()["detail"]


def test_unknown_verb_maps_to_400(client: TestClient) -> None:
    response = client.post("/api/jobs", json={"verb": "teleport"}, headers=APP_DEV)
    assert response.status_code == 400


def test_job_detail_and_404(client: TestClient) -> None:
    job_id = client.post(
        "/api/jobs", json={"verb": "build", "app": "demo"}, headers=APP_DEV
    ).json()["job"]
    assert client.get(f"/api/jobs/{job_id}", headers=APP_DEV).status_code == 200
    assert client.get("/api/jobs/nope", headers=APP_DEV).status_code == 404


def test_dev_auth_with_real_engine_is_refused(tmp_path: object) -> None:
    class RealishEngine(SimulatedEngine):
        name = "local"

    with pytest.raises(ValueError, match="refusing dev auth"):
        create_app(OpsService(RealishEngine()))


def test_oidc_mode_fails_loud_until_implemented() -> None:
    with pytest.raises(NotImplementedError, match="oidc"):
        create_app(OpsService(SimulatedEngine()), auth_mode="oidc")


def test_unknown_auth_mode_fails_loud() -> None:
    with pytest.raises(ValueError, match="unknown auth mode"):
        create_app(OpsService(SimulatedEngine()), auth_mode="none")


def test_build_engine_config_validation() -> None:
    assert build_engine({}).name == "simulated"
    with pytest.raises(ValueError, match="unknown engine mode"):
        build_engine({"VPATH_MGMT_ENGINE": "warp"})
    with pytest.raises(ValueError, match="requires VPATH_MGMT_SERVER_CHECKOUT"):
        build_engine({"VPATH_MGMT_ENGINE": "local"})
