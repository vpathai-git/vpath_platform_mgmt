"""Register write path: create / update / remove against a temp register."""

from __future__ import annotations

from pathlib import Path

import pytest

from vpath_platform_mgmt.instances import crud
from vpath_platform_mgmt.instances.registry import RegistryError, load


def test_create_standalone_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "instances.local.env"
    crud.create(
        path,
        "alpha",
        "standalone",
        {"APP_ROOT": str(tmp_path / "app"), "HOME": str(tmp_path / "home")},
    )
    inst = load(path).get("alpha")
    assert inst.kind == "standalone"
    assert inst.app_root == str(tmp_path / "app")


def test_create_refuses_missing_required_field(tmp_path: Path) -> None:
    path = tmp_path / "instances.local.env"
    with pytest.raises(RegistryError, match="APP_ROOT"):
        crud.create(path, "alpha", "standalone", {"HOME": str(tmp_path / "home")})


def test_create_server_cloud_vm(tmp_path: Path) -> None:
    path = tmp_path / "instances.local.env"
    crud.create(
        path,
        "terra",
        "server-cloud-vm",
        {
            "SSH_HOST": "203.0.113.7",
            "SSH_USER": "cloud",
            "ENV_PROFILE": "vm5",
            "CHECKOUT": "/workspace",
        },
    )
    assert load(path).get("terra").kind == "server-cloud-vm"


def test_update_changes_notes(tmp_path: Path) -> None:
    path = tmp_path / "instances.local.env"
    crud.create(
        path,
        "alpha",
        "standalone",
        {"APP_ROOT": str(tmp_path / "app"), "HOME": str(tmp_path / "home")},
    )
    crud.update(path, "alpha", {"NOTES": "nato first"})
    assert load(path).get("alpha").notes == "nato first"


def test_remove_drops_instance(tmp_path: Path) -> None:
    path = tmp_path / "instances.local.env"
    crud.create(
        path,
        "alpha",
        "standalone",
        {"APP_ROOT": str(tmp_path / "app"), "HOME": str(tmp_path / "home")},
    )
    crud.create(
        path,
        "bravo",
        "standalone",
        {"APP_ROOT": str(tmp_path / "app2"), "HOME": str(tmp_path / "home2")},
        lifecycle="planned",
    )
    crud.remove(path, "alpha")
    names = load(path).names()
    assert names == ("bravo",)


def test_create_duplicate_name_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "instances.local.env"
    fields = {"APP_ROOT": str(tmp_path / "a"), "HOME": str(tmp_path / "h")}
    crud.create(path, "alpha", "standalone", fields)
    with pytest.raises(RegistryError, match="already declared"):
        crud.create(path, "alpha", "standalone", fields)
