"""API contract tests: auth, verb submission, error mapping, console page."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vpath_platform_mgmt.api import create_app
from vpath_platform_mgmt.api.server import build_engine, build_oidc_validator
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


def test_oidc_mode_requires_validator() -> None:
    with pytest.raises(ValueError, match="VPATH_MGMT_OIDC_ISSUER"):
        create_app(OpsService(SimulatedEngine()), auth_mode="oidc")


def test_build_oidc_validator_config() -> None:
    assert build_oidc_validator({}) is None
    with pytest.raises(ValueError, match="VPATH_MGMT_OIDC_ISSUER"):
        build_oidc_validator({"VPATH_MGMT_AUTH": "oidc"})
    validator = build_oidc_validator(
        {
            "VPATH_MGMT_AUTH": "oidc",
            "VPATH_MGMT_OIDC_ISSUER": "https://kc.example/realms/vpath",
            "VPATH_MGMT_OIDC_INSECURE_TLS": "1",
        }
    )
    assert validator is not None


def test_unknown_auth_mode_fails_loud() -> None:
    with pytest.raises(ValueError, match="unknown auth mode"):
        create_app(OpsService(SimulatedEngine()), auth_mode="none")


def _archive(files: dict[str, str]) -> bytes:
    import io
    import tarfile

    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for name, content in files.items():
            data = content.encode()
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def _app_with_materializer(tmp_path: Path) -> TestClient:
    from vpath_platform_mgmt.ops.source import SourceMaterializer

    (tmp_path / "apps_infra" / "apps").mkdir(parents=True)
    service = OpsService(SimulatedEngine())
    return TestClient(create_app(service, materializer=SourceMaterializer(tmp_path)))


def test_source_upload_requires_admin(tmp_path: Path) -> None:
    client = _app_with_materializer(tmp_path)
    body = _archive({"vpath-app.yaml": "kind: VpathApp"})
    refused = client.post("/api/apps/demo/source", content=body, headers=APP_DEV)
    assert refused.status_code == 403
    ok = client.post("/api/apps/demo/source", content=body, headers=ADMIN)
    assert ok.status_code == 201
    assert ok.json()["file_count"] == 1


def test_source_upload_without_checkout_is_409(client: TestClient) -> None:
    body = _archive({"vpath-app.yaml": "kind: VpathApp"})
    response = client.post("/api/apps/demo/source", content=body, headers=ADMIN)
    assert response.status_code == 409
    assert "checkout" in response.json()["detail"]


def test_source_upload_is_audited(tmp_path: Path) -> None:
    client = _app_with_materializer(tmp_path)
    client.post(
        "/api/apps/demo/source",
        content=_archive({"vpath-app.yaml": "kind: VpathApp"}),
        headers={**ADMIN, "X-Source-Ref": "port-x", "X-Source-Commit": "deadbeef1234"},
    )
    audit = client.get("/api/state", headers=ADMIN).json()["audit"]
    assert audit[0]["action"] == "materialize"
    assert "port-x@deadbeef" in audit[0]["result"]


def test_engine_env_passthrough_parsing() -> None:
    """The pipeline needs VPATH_INSTALL_MODE on single-box targets."""
    from vpath_platform_mgmt.api.server import parse_engine_env

    assert parse_engine_env({}) == {}
    assert parse_engine_env({"VPATH_MGMT_ENGINE_ENV": "VPATH_INSTALL_MODE=nuc"}) == {
        "VPATH_INSTALL_MODE": "nuc"
    }
    assert parse_engine_env({"VPATH_MGMT_ENGINE_ENV": "A=1, B=2"}) == {
        "A": "1",
        "B": "2",
    }
    with pytest.raises(ValueError, match="not KEY=VALUE"):
        parse_engine_env({"VPATH_MGMT_ENGINE_ENV": "bogus"})


def test_local_engine_applies_extra_env(tmp_path: Path) -> None:
    """extra_env must reach the subprocess, not just be stored."""
    from vpath_platform_mgmt.ops.engine import LocalEngine

    engine = LocalEngine(tmp_path, extra_env={"VPATH_INSTALL_MODE": "nuc"})
    assert engine._extra_env == {"VPATH_INSTALL_MODE": "nuc"}


def test_build_engine_config_validation() -> None:
    assert build_engine({}).name == "simulated"
    with pytest.raises(ValueError, match="unknown engine mode"):
        build_engine({"VPATH_MGMT_ENGINE": "warp"})
    with pytest.raises(ValueError, match="requires VPATH_MGMT_SERVER_CHECKOUT"):
        build_engine({"VPATH_MGMT_ENGINE": "local"})


GITOPS_ENV = {
    "VPATH_MGMT_ENGINE": "gitops",
    "VPATH_MGMT_GITEA_URL": "https://gitea.internal",
    "VPATH_MGMT_GITEA_TOKEN": "gt",
    "VPATH_MGMT_K8S_URL": "https://10.0.0.4:6443",
    "VPATH_MGMT_K8S_TOKEN": "kt",
}


def test_gitops_engine_is_built_from_env() -> None:
    engine = build_engine(dict(GITOPS_ENV))
    assert engine.name == "gitops"


@pytest.mark.parametrize("missing", sorted(set(GITOPS_ENV) - {"VPATH_MGMT_ENGINE"}))
def test_gitops_engine_fails_hard_on_missing_config(missing: str) -> None:
    env = {key: value for key, value in GITOPS_ENV.items() if key != missing}
    with pytest.raises(ValueError, match=f"requires {missing}"):
        build_engine(env)


def test_dev_auth_is_refused_with_the_gitops_engine() -> None:
    """A header-trust identity must never gate a real deploy."""
    from vpath_platform_mgmt.api.auth import validate_auth_mode

    with pytest.raises(ValueError, match="refusing dev auth with a real engine"):
        validate_auth_mode("dev", "gitops", has_validator=False)
