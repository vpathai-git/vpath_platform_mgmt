"""Feature contracts for the fleet console shell (HTML + instances.js)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from vpath_platform_mgmt.api import create_app
from vpath_platform_mgmt.ops import OpsService, SimulatedEngine


def _client() -> TestClient:
    return TestClient(create_app(OpsService(SimulatedEngine(), instance_name="sim")))


def test_console_wires_fleet_shell_and_script() -> None:
    client = _client()
    page = client.get("/").text
    assert 'id="instancelist"' in page
    assert 'id="view-instance"' in page
    assert 'id="instance-detail"' in page
    assert 'src="/instances.js"' in page
    js = client.get("/instances.js")
    assert js.status_code == 200
    assert "application/javascript" in js.headers.get("content-type", "")


def test_instances_js_loads_list_and_detail_endpoints() -> None:
    js = _client().get("/instances.js").text
    assert 'fetch("/api/instances"' in js
    assert 'fetch("/api/instances/"' in js
    assert "loadInstances" in js
    assert "showInstance" in js


def test_instances_js_does_not_switch_drive_instance() -> None:
    js = _client().get("/instances.js").text
    assert "ops drive" in js.lower() or "does not switch" in js
    assert "instances.local.env" in js
    assert "--instance" not in js


def test_instances_js_empty_state_explains_fleet_vs_drive() -> None:
    js = _client().get("/instances.js").text
    assert "inst-empty" in js
    assert "ops drive" in js


def test_instances_js_renders_history_and_ontogate() -> None:
    js = _client().get("/instances.js").text
    assert "instance-history" in js
    assert "instance-ontogate" in js
    assert "OntoGate not available" in js
    assert "ontogate_url" in js


def test_show_dash_clears_instance_view() -> None:
    js = _client().get("/console.js").text
    assert "view-instance" in js
    assert "inst-row" in js


def test_console_ux_operate_and_danger_zone() -> None:
    page = _client().get("/").text
    assert ">Operate<" in page
    assert "Danger zone" in page
    assert 'id="ops-drive"' in page
    assert "catalog-hint" in page
    assert "Platform health, locks, audit" in page


def test_console_js_honest_signin_labels() -> None:
    js = _client().get("/console.js").text
    assert "signInFailureLabel" in js
    assert "Keycloak unreachable" in js
    assert "Reload to retry" in js
    assert "ops-drive" in js


def test_instances_js_keyboard_rows() -> None:
    js = _client().get("/instances.js").text
    assert 'role="button"' in js
    assert "keydown" in js
    assert "coarseChip" in js
    assert "tabindex=" in js
