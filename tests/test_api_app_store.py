"""Tests for the app-store view: what exists versus what is installed."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vpath_platform_mgmt.api.app import create_app
from vpath_platform_mgmt.ops import OpsService, SimulatedEngine
from vpath_platform_mgmt.ops.apps import AppCatalog
from vpath_platform_mgmt.ops.engine import EngineFailure
from vpath_platform_mgmt.ops.model import RefusedError

DEV = {"X-Dev-Actor": "alice", "X-Dev-Role": "admin"}
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
