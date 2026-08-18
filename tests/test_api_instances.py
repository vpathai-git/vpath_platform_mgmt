"""Fleet /api/instances list and detail."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vpath_platform_mgmt.api import create_app
from vpath_platform_mgmt.instances import crud
from vpath_platform_mgmt.ops import OpsService, SimulatedEngine

APP_DEV = {"X-Dev-Actor": "alice", "X-Dev-Role": "app-dev"}


@pytest.fixture()
def register(tmp_path: Path) -> Path:
    path = tmp_path / "instances.local.env"
    crud.create(
        path,
        "alpha",
        "standalone",
        {"APP_ROOT": str(tmp_path / "app"), "HOME": str(tmp_path / "home")},
    )
    (tmp_path / "app" / "kit").mkdir(parents=True)
    (tmp_path / "app" / "kit" / "VERSION").write_text(
        "source_sha: abcdef0123456789\n", encoding="utf-8"
    )
    (tmp_path / "home" / "runtime").mkdir(parents=True)
    crud.create(
        path,
        "boxone",
        "server-nuc",
        {
            "SSH_HOST": "10.0.0.1",
            "SSH_USER": "boxuser",
            "SSH_KEY": str(tmp_path / "missing.key"),
            "ENV_PROFILE": "nuc",
            "CHECKOUT": "/workspace",
        },
        lifecycle="planned",
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


def test_missing_register_lists_empty(tmp_path: Path) -> None:
    client = TestClient(
        create_app(
            OpsService(SimulatedEngine(), instance_name="sim"),
            instances_register=tmp_path / "nope.env",
        )
    )
    response = client.get("/api/instances", headers=APP_DEV)
    assert response.status_code == 200
    assert response.json() == []


def test_list_includes_kinds(client: TestClient) -> None:
    rows = client.get("/api/instances", headers=APP_DEV).json()
    by_name = {row["name"]: row for row in rows}
    assert by_name["alpha"]["kind"] == "standalone"
    assert by_name["boxone"]["kind"] == "server-nuc"
    assert "coarse" in by_name["alpha"]


def test_detail_masks_ssh_key(client: TestClient) -> None:
    detail = client.get("/api/instances/boxone", headers=APP_DEV).json()
    assert detail["fields"]["SSH_KEY"] == "<masked>"
    assert detail["probe"]["verdict"]
    assert isinstance(detail["history"], list)


def test_detail_unknown_is_404(client: TestClient) -> None:
    assert client.get("/api/instances/mars", headers=APP_DEV).status_code == 404


def test_requires_auth(client: TestClient) -> None:
    assert client.get("/api/instances").status_code == 401


def test_detail_exposes_ontogate_or_null(client: TestClient, register: Path) -> None:
    from vpath_platform_mgmt.instances import crud

    crud.update(register, "alpha", {"ONTOGATE_URL": "https://ontogate.example/alpha"})
    detail = client.get("/api/instances/alpha", headers=APP_DEV).json()
    assert detail["ontogate_url"] == "https://ontogate.example/alpha"
    crud.update(register, "alpha", {"ONTOGATE_URL": ""})
    detail2 = client.get("/api/instances/alpha", headers=APP_DEV).json()
    assert detail2["ontogate_url"] in (None, "")
