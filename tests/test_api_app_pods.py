"""Tests for GET /api/apps/{name}/pods — what an app is actually running."""

from __future__ import annotations

from collections.abc import Callable

import httpx
from fastapi.testclient import TestClient

from vpath_platform_mgmt.api.app import create_app
from vpath_platform_mgmt.ops import OpsService, SimulatedEngine
from vpath_platform_mgmt.ops.app_runtime import RuntimeReader
from vpath_platform_mgmt.ops.argocd import ArgoClient

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
    return httpx.Response(200, json={"status": status})


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
