"""Feature-level fleet API scenarios over a temp register."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vpath_platform_mgmt.api import create_app
from vpath_platform_mgmt.instances import crud, history
from vpath_platform_mgmt.ops import OpsService, SimulatedEngine

APP_DEV = {"X-Dev-Actor": "alice", "X-Dev-Role": "app-dev"}


@pytest.fixture()
def register(tmp_path: Path) -> Path:
    path = tmp_path / "instances.local.env"
    app = tmp_path / "app"
    home = tmp_path / "home"
    (app / "kit").mkdir(parents=True)
    (app / "kit" / "VERSION").write_text(
        "source_sha: abcdef0123456789\n", encoding="utf-8"
    )
    home.mkdir()
    crud.create(
        path,
        "alpha",
        "standalone",
        {
            "APP_ROOT": str(app),
            "HOME": str(home),
            "ONTOGATE_URL": "https://og.example/a",
        },
    )
    crud.create(
        path,
        "claas",
        "remote",
        {"NOTES": "unproven"},
        lifecycle="live",
    )
    return path


@pytest.fixture()
def client(register: Path) -> TestClient:
    return TestClient(
        create_app(
            OpsService(SimulatedEngine(), instance_name="sim"),
            instances_register=register,
            instances_probe_timeout=2,
        )
    )


def test_list_includes_remote_with_unproven_coarse(client: TestClient) -> None:
    rows = {r["name"]: r for r in client.get("/api/instances", headers=APP_DEV).json()}
    assert rows["claas"]["kind"] == "remote"
    assert rows["claas"]["coarse"] == "UNPROVEN"
    assert rows["alpha"]["kind"] == "standalone"


def test_list_and_detail_append_history(client: TestClient, register: Path) -> None:
    client.get("/api/instances", headers=APP_DEV)
    hist = history.history_path(register)
    assert hist.is_file()
    before = len(history.read_tail(hist, name="alpha", limit=100))
    detail = client.get("/api/instances/alpha", headers=APP_DEV).json()
    after = history.read_tail(hist, name="alpha", limit=100)
    assert len(after) >= before
    assert detail["history"]
    assert detail["history"][-1]["name"] == "alpha"
    assert detail["ontogate_url"] == "https://og.example/a"


def test_corrupt_register_lists_as_400(tmp_path: Path) -> None:
    path = tmp_path / "bad.env"
    path.write_text("VPATH_INSTANCES=\nnot-an-assignment\n", encoding="utf-8")
    client = TestClient(
        create_app(
            OpsService(SimulatedEngine(), instance_name="sim"),
            instances_register=path,
        )
    )
    assert client.get("/api/instances", headers=APP_DEV).status_code == 400
