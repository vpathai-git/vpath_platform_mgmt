"""Integration: register → probe CLI → history → fleet API detail."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vpath_platform_mgmt.api import create_app
from vpath_platform_mgmt.instances import crud, history, probe
from vpath_platform_mgmt.ops import OpsService, SimulatedEngine

pytestmark = pytest.mark.integration

APP_DEV = {"X-Dev-Actor": "alice", "X-Dev-Role": "app-dev"}


@pytest.fixture()
def fleet(tmp_path: Path) -> tuple[Path, Path]:
    register = tmp_path / "instances.local.env"
    app = tmp_path / "app"
    home = tmp_path / "home"
    (app / "kit").mkdir(parents=True)
    (app / "kit" / "VERSION").write_text(
        "source_sha: 1122334455667788\n", encoding="utf-8"
    )
    (home / "runtime").mkdir(parents=True)
    crud.create(
        register,
        "alpha",
        "standalone",
        {"APP_ROOT": str(app), "HOME": str(home)},
    )
    return register, home


def test_probe_cli_writes_history_consumed_by_api(fleet: tuple[Path, Path]) -> None:
    register, _home = fleet
    code = probe.main(["--register", str(register), "--instance", "alpha"])
    assert code in (0, 1, 2, 3)
    hist = history.history_path(register)
    assert hist.is_file()
    events = history.read_tail(hist, name="alpha", limit=5)
    assert events
    assert events[-1]["coarse"]

    client = TestClient(
        create_app(
            OpsService(SimulatedEngine(), instance_name="sim"),
            instances_register=register,
            instances_probe_timeout=2,
        )
    )
    detail = client.get("/api/instances/alpha", headers=APP_DEV).json()
    assert detail["name"] == "alpha"
    assert detail["history"]
    assert any(e["name"] == "alpha" for e in detail["history"])


def test_crud_update_visible_through_api(fleet: tuple[Path, Path]) -> None:
    register, _home = fleet
    crud.update(
        register,
        "alpha",
        {"NOTES": "integration-note", "ONTOGATE_URL": "https://og.test/x"},
    )
    client = TestClient(
        create_app(
            OpsService(SimulatedEngine(), instance_name="sim"),
            instances_register=register,
            instances_probe_timeout=2,
        )
    )
    detail = client.get("/api/instances/alpha", headers=APP_DEV).json()
    assert detail["fields"]["NOTES"] == "integration-note"
    assert detail["ontogate_url"] == "https://og.test/x"


def test_status_file_makes_probe_healthy_and_api_coarse(
    fleet: tuple[Path, Path],
) -> None:
    register, home = fleet
    status = home / "runtime" / "vpath-standalone.status.json"
    status.write_text(
        json.dumps(
            {
                "pid": 99,
                "port": 40123,
                "started_at": "2026-08-10T12:00:00Z",
                "version": "deadbeefcafe01",
            }
        ),
        encoding="utf-8",
    )
    client = TestClient(
        create_app(
            OpsService(SimulatedEngine(), instance_name="sim"),
            instances_register=register,
            instances_probe_timeout=2,
        )
    )
    rows = {r["name"]: r for r in client.get("/api/instances", headers=APP_DEV).json()}
    assert rows["alpha"]["coarse"] == "HEALTHY"
    detail = client.get("/api/instances/alpha", headers=APP_DEV).json()
    labels = {f["label"]: f["value"] for f in detail["probe"]["facts"]}
    assert labels["port"] == "40123"
    assert labels["pid"] == "99"
