"""Tests for the app-store view: what exists versus what is installed."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vpath_platform_mgmt.api.app import create_app
from vpath_platform_mgmt.ops import OpsService, SimulatedEngine
from vpath_platform_mgmt.ops.app_registry import Generated
from vpath_platform_mgmt.ops.apps import AppCatalog
from vpath_platform_mgmt.ops.engine import EngineFailure
from vpath_platform_mgmt.ops.model import RefusedError

DEV = {"X-Dev-Actor": "alice", "X-Dev-Role": "admin"}
APP_DEV = {"X-Dev-Actor": "bob", "X-Dev-Role": "app-dev"}
MANIFEST = """
apiVersion: vpath/v1
kind: VpathApp
metadata:
  name: {name}
spec:
  type: web
  ui:
    title: {title}
"""


def catalog_with(tmp_path: Path, names: dict[str, str]) -> AppCatalog:
    for name, title in names.items():
        folder = tmp_path / name
        folder.mkdir()
        (folder / "vpath-app.yaml").write_text(
            MANIFEST.format(name=name, title=title), encoding="utf-8"
        )
    return AppCatalog(tmp_path)


def _served(handler: object) -> object:
    import httpx

    from vpath_platform_mgmt.ops.served_catalog import ServedCatalogReader

    return ServedCatalogReader(
        "https://platform",
        client=httpx.Client(transport=httpx.MockTransport(handler)),  # type: ignore
    )


def _state(tmp_path: Path, served: object | None) -> dict:
    app = create_app(
        OpsService(SimulatedEngine()),
        catalog=catalog_with(tmp_path, {"vpath-explorer": "Explorer"}),
        served_catalog=served,  # type: ignore[arg-type]
    )
    return TestClient(app).get("/api/apps", headers=DEV).json()["catalog"]


def test_catalog_state_reports_counts_and_the_platform_catalog(tmp_path: Path) -> None:
    """The Applications view must show both catalogs, kept apart."""
    import httpx

    state = _state(
        tmp_path,
        _served(
            lambda _: httpx.Response(
                200, json=[{"name": "vpath-explorer", "label": "Renamed"}]
            )
        ),
    )
    assert state["total"] == 1
    assert state["platform"]["served_total"] == 1
    assert state["platform"]["shared"] == 1
    # The drift /api/version can never show: same app, different label.
    assert state["platform"]["label_mismatches"][0]["platform"] == "Renamed"


def test_an_unreadable_platform_catalog_says_so_instead_of_showing_none(
    tmp_path: Path,
) -> None:
    """'Offers nothing' and 'could not ask' mean opposite things."""
    import httpx

    def down(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route to host")

    state = _state(tmp_path, _served(down))
    assert state["platform"] is None
    assert "did not answer" in state["platform_error"]


def test_catalog_state_without_a_platform_url_names_the_reason(
    tmp_path: Path,
) -> None:
    state = _state(tmp_path, None)
    assert state["platform"] is None
    assert state["platform_error"] == "no platform URL configured"


class ReportingEngine(SimulatedEngine):
    """Simulated engine that also reports an installed set.

    Keeps the ``simulated`` name so dev auth stays permitted — the auth gate
    refuses header identity in front of anything else, by design.
    """

    def __init__(self, installed: list[str]) -> None:
        super().__init__()
        self._installed = installed

    def installed_apps(self) -> list[str]:
        return list(self._installed)


class BrokenEngine(SimulatedEngine):
    """Engine whose installed set cannot be read right now."""

    def installed_apps(self) -> list[str]:
        raise EngineFailure("gitea unreachable")


def client_for(catalog: AppCatalog, engine: SimulatedEngine) -> TestClient:
    return TestClient(create_app(OpsService(engine), catalog=catalog))


def test_apps_report_whether_the_server_has_them_installed(tmp_path: Path) -> None:
    catalog = catalog_with(tmp_path, {"alpha": "Alpha", "beta": "Beta"})
    client = client_for(catalog, ReportingEngine(["alpha"]))
    body = client.get("/api/apps", headers=DEV).json()
    installed = {app["name"]: app["installed"] for app in body["apps"]}
    assert installed == {"alpha": True, "beta": False}
    assert body["installed_known"] is True


def test_installed_is_unknown_when_the_engine_cannot_say(tmp_path: Path) -> None:
    """The simulated engine has no server to ask; unknown is not 'not installed'."""
    catalog = catalog_with(tmp_path, {"alpha": "Alpha"})
    body = client_for(catalog, SimulatedEngine()).get("/api/apps", headers=DEV).json()
    assert body["apps"][0]["installed"] is None
    assert body["installed_known"] is False


def test_a_failing_engine_leaves_the_store_usable_but_honest(tmp_path: Path) -> None:
    """A Gitea outage must not render every app as 'not installed'."""
    catalog = catalog_with(tmp_path, {"alpha": "Alpha"})
    body = client_for(catalog, BrokenEngine()).get("/api/apps", headers=DEV).json()
    assert body["apps"][0]["installed"] is None
    assert body["installed_known"] is False


def test_service_reports_none_for_an_engine_without_the_capability() -> None:
    assert OpsService(SimulatedEngine()).installed_apps() is None


def test_service_passes_through_the_engines_installed_set() -> None:
    service = OpsService(ReportingEngine(["alpha", "beta"]))
    assert service.installed_apps() == ["alpha", "beta"]


def test_gitops_engine_reports_its_installed_set() -> None:
    from tests.test_ops_gitops_engine import FakeRecord, engine_for

    engine = engine_for(FakeRecord(apps=["one", "two"], rendered=["one"]))
    assert engine.installed_apps() == ["one", "two"]


def test_uninstall_is_still_gated_by_role() -> None:
    """The store button is convenience; the refusal lives in the service."""
    service = OpsService(ReportingEngine(["alpha"]))
    with pytest.raises(RefusedError):
        service.submit("uninstall", "alpha", "eve", "server-dev")


def client_for_publish() -> TestClient:
    return TestClient(create_app(OpsService(SimulatedEngine())))


def test_publish_submits_a_job_and_returns_it() -> None:
    response = client_for_publish().post(
        "/api/apps/publish",
        json={"url": "github.com/org/demo-app", "ref": "main", "name": "demo-app"},
        headers=DEV,
    )

    assert response.status_code == 202
    body = response.json()
    assert body["verb"] == "publish"
    assert body["app"] == "demo-app"


def test_publish_refuses_a_non_admin() -> None:
    response = client_for_publish().post(
        "/api/apps/publish",
        json={"url": "github.com/org/demo-app", "ref": "main", "name": "demo-app"},
        headers=APP_DEV,
    )

    assert response.status_code == 403


def test_publish_refuses_a_request_without_a_url() -> None:
    response = client_for_publish().post(
        "/api/apps/publish", json={"ref": "main", "name": "demo-app"}, headers=DEV
    )

    assert response.status_code == 400
    assert "url" in response.json()["detail"]


def test_publish_refuses_a_request_without_a_name() -> None:
    response = client_for_publish().post(
        "/api/apps/publish", json={"url": "github.com/org/demo-app"}, headers=DEV
    )

    assert response.status_code == 400
    assert "name" in response.json()["detail"]


GENERATE = {
    "name": "demo-app",
    "port": 8080,
    "base_path": "/demo-app",
    "title": "Demo App",
}


def service_and_client() -> tuple[OpsService, TestClient]:
    service = OpsService(SimulatedEngine())
    return service, TestClient(create_app(service))


def test_a_generate_block_reaches_the_job_as_the_registrys_own_type() -> None:
    """A dict here dies at ``request.generate.runtime`` on the worker thread."""
    service, client = service_and_client()

    response = client.post(
        "/api/apps/publish",
        json={
            "url": "github.com/org/demo-app",
            "name": "demo-app",
            "generate": GENERATE,
        },
        headers=DEV,
    )

    assert response.status_code == 202
    job = service.job(response.json()["id"])
    assert job is not None and job.payload is not None
    generated = job.payload["generate"]
    assert isinstance(generated, Generated)
    assert (generated.name, generated.port) == ("demo-app", 8080)


@pytest.mark.parametrize("absent", sorted(GENERATE))
def test_an_incomplete_generate_block_is_a_400_naming_the_gap(absent: str) -> None:
    block = {key: value for key, value in GENERATE.items() if key != absent}
    _, client = service_and_client()

    response = client.post(
        "/api/apps/publish",
        json={"url": "github.com/org/demo-app", "name": "demo-app", "generate": block},
        headers=DEV,
    )

    assert response.status_code == 400
    assert absent in response.json()["detail"]


def test_a_generate_port_that_is_not_a_number_is_a_400() -> None:
    _, client = service_and_client()

    response = client.post(
        "/api/apps/publish",
        json={
            "url": "github.com/org/demo-app",
            "name": "demo-app",
            "generate": dict(GENERATE, port="eighty"),
        },
        headers=DEV,
    )

    assert response.status_code == 400
    assert "eighty" in response.json()["detail"]


def test_a_generate_block_that_is_not_an_object_is_a_400() -> None:
    _, client = service_and_client()

    response = client.post(
        "/api/apps/publish",
        json={"url": "github.com/org/demo-app", "name": "demo-app", "generate": "yes"},
        headers=DEV,
    )

    assert response.status_code == 400
    assert "object" in response.json()["detail"]


def test_a_ref_that_would_hijack_the_api_url_is_refused_at_the_boundary() -> None:
    """``ref`` becomes a path segment in repos/<slug>/commits/<ref>."""
    _, client = service_and_client()

    response = client.post(
        "/api/apps/publish",
        json={
            "url": "github.com/org/demo-app",
            "name": "demo-app",
            "ref": "main?ref=other",
        },
        headers=DEV,
    )

    assert response.status_code == 400
    assert "not a usable ref" in response.json()["detail"]


def test_the_state_view_never_echoes_what_was_typed_into_the_publish_form() -> None:
    """Any authenticated role reads /api/state; payload carries repo URLs."""
    service, client = service_and_client()
    service.submit(
        "publish",
        "demo-app",
        "alice",
        "admin",
        payload={"url": "https://user:secret@github.internal/org/demo-app"},
    )

    body = client.get("/api/state", headers=APP_DEV).text

    assert "github.internal" not in body
    assert "payload" not in body
