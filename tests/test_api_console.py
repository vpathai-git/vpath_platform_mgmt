"""API contract tests: auth, verb submission, error mapping, console page."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vpath_platform_mgmt.api import create_app
from vpath_platform_mgmt.api.builders import GITOPS_KEYS, build_engine
from vpath_platform_mgmt.api.server import build_oidc_validator
from vpath_platform_mgmt.ops import OpsService, SimulatedEngine

APP_DEV = {"X-Dev-Actor": "alice", "X-Dev-Role": "app-dev"}
ADMIN = {"X-Dev-Actor": "root", "X-Dev-Role": "admin"}
SERVER_DEV = {"X-Dev-Actor": "sam", "X-Dev-Role": "server-dev"}


@pytest.fixture()
def client() -> TestClient:
    return TestClient(create_app(OpsService(SimulatedEngine(), instance_name="sim")))


def test_requests_without_dev_headers_are_401(client: TestClient) -> None:
    assert client.get("/api/state").status_code == 401
    assert client.post("/api/jobs", json={"verb": "deploy"}).status_code == 401


def test_console_page_serves(client: TestClient) -> None:
    page = client.get("/")
    assert page.status_code == 200
    assert "VPath Console" in page.text
    assert 'id="engine"' not in page.text  # the conn badge names the instance now


def test_header_shows_connection_status_with_synced_connect_button(
    client: TestClient,
) -> None:
    """Badge and Connect button are two halves of one state machine."""
    page = client.get("/").text
    assert '<span id="conn"' in page
    assert '<button id="connect" onclick="connectNow()"' in page
    console = client.get("/console.js").text
    assert 'const down = state === "disconnected" || state === "unreachable"' in console
    assert '$("connect").hidden = !down' in console
    assert "function connectNow()" in console
    assert 'next = inst.reachable ? "connected" : "unreachable"' in console
    assert 'CONN[state][0] + " · " + instance' in console  # instance name shown
    assert '"?fresh=1"' in console  # Connect forces a real re-probe


def test_state_names_the_instance_and_its_reachability(client: TestClient) -> None:
    state = client.get("/api/state", headers=APP_DEV).json()
    assert state["instance"]["name"] == "sim"
    assert state["instance"]["reachable"] is True


def test_state_fresh_query_bypasses_the_probe_cache() -> None:
    from vpath_platform_mgmt.ops.engine import Reach

    class CountingEngine(SimulatedEngine):
        probes = 0

        def probe(self) -> Reach:
            type(self).probes += 1
            return Reach(True)

    engine = CountingEngine()
    client = TestClient(create_app(OpsService(engine, instance_name="sim")))
    client.get("/api/state", headers=APP_DEV)
    client.get("/api/state", headers=APP_DEV)
    assert CountingEngine.probes == 1  # second read served from cache
    client.get("/api/state?fresh=1", headers=APP_DEV)
    assert CountingEngine.probes == 2


def test_starting_a_tunnel_needs_admin_and_is_audited(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The one action that spawns a process is gated like a destructive verb."""
    from vpath_platform_mgmt.ops import tunnel as tunnel_module
    from vpath_platform_mgmt.ops.tunnel import TunnelConfig

    started: list[TunnelConfig] = []
    monkeypatch.setattr(
        tunnel_module, "start", lambda config: (started.append(config), "started")[1]
    )
    service = OpsService(
        SimulatedEngine(),
        instance_name="vm5",
        tunnel_config=TunnelConfig("h", "u", "/k.pem"),
    )
    client = TestClient(create_app(service))

    refused = client.post("/api/instance/tunnel", headers=APP_DEV)
    assert refused.status_code == 403
    assert started == []  # a refusal spawns nothing
    audit = client.get("/api/state", headers=ADMIN).json()["audit"]
    assert audit[0]["action"] == "tunnel" and "REFUSED" in audit[0]["result"]

    ok = client.post("/api/instance/tunnel", headers=ADMIN)
    assert ok.status_code == 200 and ok.json()["result"] == "started"
    assert len(started) == 1
    after = client.get("/api/state", headers=ADMIN).json()["audit"]
    assert after[0]["action"] == "tunnel" and after[0]["result"] == "started"


def test_an_instance_without_a_tunnel_says_so(client: TestClient) -> None:
    response = client.post("/api/instance/tunnel", headers=ADMIN)
    assert response.status_code == 409
    assert "declares no tunnel" in response.json()["detail"]


def test_a_dead_backend_explains_itself_like_every_other_failure(
    client: TestClient,
) -> None:
    """The commonest failure of all said nothing: /api/state carries no
    diagnosis when the console's own backend is the thing that is gone, so
    the badge went red with an empty detail and the button looked broken."""
    console = client.get("/console.js").text
    assert "detail || CONN[state][2]" in console  # per-state fallback
    assert "vpath-console still running" in console


def test_the_console_offers_the_tunnel_only_for_a_routing_failure(
    client: TestClient,
) -> None:
    """A rejected token is a red badge that starting a tunnel will not fix."""
    console = client.get("/console.js").text
    assert '$("tunnel").hidden = reason !== "no-route"' in console
    assert "function startTunnel()" in console
    assert 'id="conn-detail"' in client.get("/").text


def test_instance_profile_is_loaded_without_overriding_the_environment(
    tmp_path: Path,
) -> None:
    """`--instance vm5` reads .env.vm5; an explicit env var still wins."""
    from vpath_platform_mgmt.api.server import load_profile

    (tmp_path / ".env.vm5").write_text(
        "VPATH_MGMT_ENGINE=gitops\nVPATH_MGMT_GITEA_TOKEN=from-file\n",
        encoding="utf-8",
    )
    env = {"VPATH_MGMT_GITEA_TOKEN": "from-command-line"}
    loaded = load_profile("vm5", env, root=tmp_path)

    assert loaded == tmp_path / ".env.vm5"
    assert env["VPATH_MGMT_ENGINE"] == "gitops"
    assert env["VPATH_MGMT_GITEA_TOKEN"] == "from-command-line"
    assert env["VPATH_MGMT_INSTANCE"] == "vm5"  # derived from the flag


def test_no_instance_flag_leaves_the_environment_alone(tmp_path: Path) -> None:
    from vpath_platform_mgmt.api.server import load_profile

    env: dict[str, str] = {}
    assert load_profile("", env, root=tmp_path) is None
    assert env == {}


def test_a_missing_profile_fails_rather_than_simulating(tmp_path: Path) -> None:
    """Asking for a real instance must never silently serve a simulation."""
    from vpath_platform_mgmt.api.server import load_profile

    with pytest.raises(ValueError, match="no profile for instance 'vm5'"):
        load_profile("vm5", {}, root=tmp_path)


def test_real_engines_must_name_their_instance() -> None:
    from vpath_platform_mgmt.api.builders import resolve_instance_name

    assert resolve_instance_name({}, "simulated") == "sim"
    assert resolve_instance_name({"VPATH_MGMT_INSTANCE": "vm5"}, "gitops") == "vm5"
    with pytest.raises(ValueError, match="requires VPATH_MGMT_INSTANCE"):
        resolve_instance_name({}, "gitops")
    with pytest.raises(ValueError, match="requires VPATH_MGMT_INSTANCE"):
        resolve_instance_name({}, "local")


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
    from vpath_platform_mgmt.api.builders import parse_engine_env

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


def test_no_publish_pipeline_without_a_checkout() -> None:
    from vpath_platform_mgmt.api.builders import build_publish_pipeline

    assert build_publish_pipeline({"VPATH_MGMT_GITEA_URL": "https://gitea"}) is None


def test_no_publish_pipeline_without_the_deploy_record(tmp_path: Path) -> None:
    from vpath_platform_mgmt.api.builders import build_publish_pipeline

    assert build_publish_pipeline({"VPATH_MGMT_SERVER_CHECKOUT": str(tmp_path)}) is None


def test_publish_pipeline_is_built_when_both_halves_exist(tmp_path: Path) -> None:
    from vpath_platform_mgmt.api.builders import build_publish_pipeline
    from vpath_platform_mgmt.ops.publish import PublishPipeline

    env = dict(GITOPS_ENV, VPATH_MGMT_SERVER_CHECKOUT=str(tmp_path))
    pipeline = build_publish_pipeline(env)

    assert isinstance(pipeline, PublishPipeline)


def test_publish_pipeline_send_stage_honours_the_overridden_apps_root(
    tmp_path: Path,
) -> None:
    """The registry and the send stage must read from the same apps root.

    A console that overrides ``VPATH_MGMT_APPS_DIR`` writes a registered
    app's manifest there; if the send stage's ``place`` collaborator were
    left unbound, it would fall back to the hardcoded default root instead
    and the publish job would die at 'send' looking in the wrong place.
    """
    from vpath_platform_mgmt.api.builders import build_publish_pipeline

    apps_dir = tmp_path / "apps"
    (apps_dir / "demo-app").mkdir(parents=True)
    (apps_dir / "demo-app" / "vpath-app.yaml").write_text(
        "kind: VpathApp", encoding="utf-8"
    )
    (apps_dir / "demo-app" / "vpath-source.yaml").write_text(
        "repo: x", encoding="utf-8"
    )
    checkout_dir = tmp_path / "checkout"
    checkout_dir.mkdir()
    env = dict(
        GITOPS_ENV,
        VPATH_MGMT_SERVER_CHECKOUT=str(checkout_dir),
        VPATH_MGMT_APPS_DIR=str(apps_dir),
    )

    pipeline = build_publish_pipeline(env)
    assert pipeline is not None

    payload = tmp_path / "payload"
    payload.mkdir()
    pipeline._place("demo-app", payload)  # type: ignore[attr-defined]

    assert (payload / "vpath-app.yaml").read_text(encoding="utf-8") == "kind: VpathApp"


def test_dev_auth_is_refused_with_the_gitops_engine() -> None:
    """A header-trust identity must never gate a real deploy."""
    from vpath_platform_mgmt.api.auth import validate_auth_mode

    with pytest.raises(ValueError, match="refusing dev auth with a real engine"):
        validate_auth_mode("dev", "gitops", has_validator=False)


def test_the_console_offers_an_add_app_form(client: TestClient) -> None:
    page = client.get("/").text
    assert 'id="add-app"' in page
    assert 'id="add-app-url"' in page
    assert 'id="add-app-name"' in page


def test_the_console_posts_to_the_publish_route(client: TestClient) -> None:
    script = client.get("/console.js").text
    assert "/api/apps/publish" in script


@pytest.mark.parametrize("missing", GITOPS_KEYS)
def test_every_key_the_pipeline_gate_asks_for_is_really_required(missing: str) -> None:
    """Keeps ``missing_gitops_keys`` from drifting away from what it gates."""
    from vpath_platform_mgmt.api.builders import build_gitops_engine

    env = {key: "x" for key in GITOPS_KEYS if key != missing}

    with pytest.raises(ValueError, match=f"requires {missing}"):
        build_gitops_engine(env)


@pytest.mark.parametrize("missing", GITOPS_KEYS)
def test_an_incomplete_gitops_config_declines_publish_instead_of_aborting(
    tmp_path: Path, missing: str
) -> None:
    """A local-engine console with a checkout must still start.

    Gating on the Gitea URL alone let ``build_gitops_engine`` raise at import
    time for a box that has no Kubernetes token, taking the whole console
    down instead of leaving publish unavailable.
    """
    from vpath_platform_mgmt.api.builders import build_publish_pipeline

    env = {key: value for key, value in GITOPS_ENV.items() if key != missing}
    env["VPATH_MGMT_SERVER_CHECKOUT"] = str(tmp_path)

    assert build_publish_pipeline(env) is None
