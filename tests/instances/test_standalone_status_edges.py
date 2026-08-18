"""Unit edges for the standalone supervisor status-file contract."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vpath_platform_mgmt.instances.standalone_status import (
    STATUS_REL,
    StatusFileError,
    parse_status,
    status_path,
)


def _write(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_status_path_is_under_home_runtime(tmp_path: Path) -> None:
    assert status_path(tmp_path) == tmp_path / STATUS_REL


def test_accepts_ports_and_build_id(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "s.json",
        {
            "pid": 1,
            "ports": [3000, 3001],
            "started_at": "2026-08-10T10:00:00Z",
            "build_id": "abcdef0123456789",
        },
    )
    data = parse_status(path)
    assert data["ports"] == [3000, 3001]
    assert data["build_id"].startswith("abcdef")


def test_refuses_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "s.json"
    path.write_text("{nope", encoding="utf-8")
    with pytest.raises(StatusFileError, match="not valid JSON"):
        parse_status(path)


def test_refuses_non_object(tmp_path: Path) -> None:
    path = tmp_path / "s.json"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(StatusFileError, match="JSON object"):
        parse_status(path)


def test_refuses_missing_port_and_ports(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "s.json",
        {"pid": 1, "started_at": "t", "version": "v"},
    )
    with pytest.raises(StatusFileError, match="port or ports"):
        parse_status(path)


def test_refuses_missing_version_keys(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "s.json",
        {"pid": 1, "port": 9, "started_at": "t"},
    )
    with pytest.raises(StatusFileError, match="version or build_id"):
        parse_status(path)


def test_refuses_missing_file(tmp_path: Path) -> None:
    with pytest.raises(StatusFileError, match="missing status file"):
        parse_status(tmp_path / "absent.json")
