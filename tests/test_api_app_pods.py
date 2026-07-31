"""Tests for GET /api/apps/{name}/pods — what an app is actually running."""

from __future__ import annotations

from collections.abc import Callable

import httpx
from fastapi.testclient import TestClient

from vpath_platform_mgmt.api.app import create_app
from vpath_platform_mgmt.ops import OpsService, SimulatedEngine
from vpath_platform_mgmt.ops.app_runtime import RuntimeReader
from vpath_platform_mgmt.ops.argocd import ArgoClient
from vpath_platform_mgmt.ops.engine import EngineFailure

DEV = {"X-Dev-Actor": "alice", "X-Dev-Role": "admin"}
APP_DEV = {"X-Dev-Actor": "bob", "X-Dev-Role": "app-dev"}
APP = "vpath-workflow-demo"
PROJECT = f"kp-{APP}-klemens"

Handler = Callable[[httpx.Request], httpx.Response]


class ReportingEngine(SimulatedEngine):
    """Engine that can say which apps the server has installed."""

    def __init__(self, installed: list[str]) -> None:
        super().__init__()
        self._installed = installed

    def installed_apps(self) -> list[str]:
        return list(self._installed)


def reader(handler: Handler) -> RuntimeReader:
    client = httpx.Client(
        base_url="https://k8s.test", transport=httpx.MockTransport(handler)
    )
    return RuntimeReader(ArgoClient("https://k8s.test", "token", client=client))


def running(request: httpx.Request) -> httpx.Response:
    """A cluster where the app runs one web pod and one project runner."""
    path = request.url.path
    if path.endswith("/namespaces"):
        names = [APP, PROJECT, "kp-other-klemens"]
        return httpx.Response(
            200, json={"items": [{"metadata": {"name": n}} for n in names]}
        )
    if path.endswith("/pods"):
        namespace = path.split("/namespaces/")[1].removesuffix("/pods")
        name = "web-1" if namespace == APP else "runner-1"
        return httpx.Response(
            200,
            json={
                "items": [
                    {
                        "metadata": {"name": name},
                        "spec": {"containers": [{"name": "c0"}]},
                        "status": {
                            "phase": "Running",
                            "startTime": "2026-07-27T09:12:44Z",
                            "containerStatuses": [{"ready": True, "restartCount": 0}],
                        },
                    }
                ]
            },
        )
    status = {"sync": {"status": "Synced"}, "health": {"status": "Healthy"}}
    spec = {"destination": {"namespace": APP}}
    return httpx.Response(200, json={"spec": spec, "status": status})


def client_for(runtime: RuntimeReader | None, installed: list[str]) -> TestClient:
    service = OpsService(ReportingEngine(installed))
    return TestClient(create_app(service, runtime=runtime))


def test_a_console_with_no_cluster_refuses_and_names_the_setting() -> None:
    """No fallback: a console that cannot ask must not answer."""
    response = client_for(None, [APP]).get(f"/api/apps/{APP}/pods", headers=DEV)

    assert response.status_code == 409
    assert "VPATH_MGMT_K8S_URL" in response.json()["detail"]


def test_an_app_that_is_not_installed_has_no_pods_to_read() -> None:
    response = client_for(reader(running), ["other"]).get(
        f"/api/apps/{APP}/pods", headers=DEV
    )

    assert response.status_code == 404
    assert APP in response.json()["detail"]


def test_pods_come_back_grouped_by_namespace() -> None:
    response = client_for(reader(running), [APP]).get(
        f"/api/apps/{APP}/pods", headers=DEV
    )

    assert response.status_code == 200
    body = response.json()
    assert body["sync"] == "Synced"
    assert [(n["name"], n["kind"]) for n in body["namespaces"]] == [
        (APP, "application"),
        (PROJECT, "project"),
    ]
    assert body["namespaces"][0]["pods"][0]["name"] == "web-1"


def test_an_unreachable_cluster_reports_the_reason_not_an_empty_list() -> None:
    def down(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route to host")

    response = client_for(reader(down), [APP]).get(f"/api/apps/{APP}/pods", headers=DEV)

    assert response.status_code == 502
    assert "no route to host" in response.json()["detail"]


def test_an_unreadable_installed_set_refuses_rather_than_guessing() -> None:
    """Without the InstalledSet we cannot tell 'not installed' from 'cannot ask'."""

    class BrokenEngine(SimulatedEngine):
        def installed_apps(self) -> list[str]:
            raise EngineFailure("gitea unreachable")

    service = OpsService(BrokenEngine())
    client = TestClient(create_app(service, runtime=reader(running)))
    response = client.get(f"/api/apps/{APP}/pods", headers=DEV)

    assert response.status_code == 502
    assert "gitea unreachable" in response.json()["detail"]


def test_reading_pods_needs_no_more_than_the_right_to_list_apps() -> None:
    """Pod state is read-only cluster state; it is not an admin secret."""
    response = client_for(reader(running), [APP]).get(
        f"/api/apps/{APP}/pods", headers=APP_DEV
    )

    assert response.status_code == 200


def test_pods_still_need_an_identity() -> None:
    response = client_for(reader(running), [APP]).get(f"/api/apps/{APP}/pods")

    assert response.status_code == 401


# --- wiring -----------------------------------------------------------------


def test_no_runtime_reader_without_a_cluster_to_read() -> None:
    """A console lacking either Kubernetes setting declines the capability."""
    from vpath_platform_mgmt.api.builders import build_runtime_reader

    assert build_runtime_reader({}) is None
    assert build_runtime_reader({"VPATH_MGMT_K8S_URL": "https://10.0.0.4:6443"}) is None
    assert build_runtime_reader({"VPATH_MGMT_K8S_TOKEN": "kt"}) is None


def test_a_runtime_reader_is_built_from_the_cluster_settings() -> None:
    from vpath_platform_mgmt.api.builders import build_runtime_reader

    built = build_runtime_reader(
        {"VPATH_MGMT_K8S_URL": "https://10.0.0.4:6443", "VPATH_MGMT_K8S_TOKEN": "kt"}
    )

    assert isinstance(built, RuntimeReader)


def test_the_app_list_names_everything_the_server_has_installed() -> None:
    """The catalog is this repo's apps/ folder; the server runs its own set.

    On vm5 the two overlap in exactly one app out of eighteen, so a runtime
    view built from the catalog alone shows 1/18 of what is running.
    """
    service = OpsService(ReportingEngine(["vpath-explorer", "vpath-web"]))
    client = TestClient(create_app(service))

    body = client.get("/api/apps", headers=DEV).json()

    assert body["installed_apps"] == ["vpath-explorer", "vpath-web"]


def test_an_unknown_installed_set_is_null_not_an_empty_list() -> None:
    """[] would say 'the server runs nothing', which nobody established."""
    client = TestClient(create_app(OpsService(SimulatedEngine())))

    assert client.get("/api/apps", headers=DEV).json()["installed_apps"] is None


# --- the console surface ----------------------------------------------------


def console() -> TestClient:
    return TestClient(create_app(OpsService(SimulatedEngine())))


def test_the_dashboard_carries_a_running_applications_section() -> None:
    page = console().get("/").text

    assert 'id="running"' in page
    assert 'id="running-count"' in page
    assert '<script src="/runtime.js"></script>' in page


def test_the_runtime_script_is_served_as_javascript() -> None:
    response = console().get("/runtime.js")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/javascript")


def test_pods_are_read_only_while_a_row_is_expanded() -> None:
    """A collapsed list must cost the cluster nothing."""
    script = console().get("/runtime.js").text

    assert "function toggleApp(" in script
    assert "/pods" in script
    assert "clearTimeout(podTimer)" in script
    assert "if (openApp === name) podTimer = setTimeout(" in script


def test_a_namespace_that_could_not_be_read_is_never_drawn_as_empty() -> None:
    """'we could not ask' and 'nothing runs here' must not look alike."""
    script = console().get("/runtime.js").text

    unreadable = script.index("ns.pods === null")
    empty = script.index("No pods running")
    assert unreadable < empty  # the error branch wins before emptiness is claimed


def test_an_app_whose_install_state_is_unknown_is_still_listed() -> None:
    """Hiding it would assert it is not running, which nobody established."""
    script = console().get("/runtime.js").text

    assert "a.installed !== false" in script
    assert "install state unknown" in script


def test_a_succeeded_pod_is_not_coloured_as_a_failure() -> None:
    """vm5 runs completed Jobs (…-gateway-mint-…) that sit in Succeeded.
    That is a normal terminal state, and red would report 5 healthy
    installations as broken."""
    script = console().get("/runtime.js").text

    assert "const PHASE = {" in script
    assert "Succeeded:" in script
    assert 'Running: "ok"' in script


def test_the_section_lists_installed_apps_the_catalog_has_never_heard_of() -> None:
    """17 of vm5's 18 installed apps have no entry in this repo's apps/."""
    script = console().get("/runtime.js").text

    assert "function runningRows(" in script
    assert "INSTALLED" in script  # the server's set drives the list
    assert "not in the catalog" in script  # and says so for the strangers
