"""Standalone probe reads supervisor status file under HOME when present."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vpath_platform_mgmt.instances.probe import HEALTHY, STOPPED, read_instance
from vpath_platform_mgmt.instances.registry import Instance
from vpath_platform_mgmt.instances.standalone_status import (
    STATUS_REL,
    StatusFileError,
    parse_status,
)
from vpath_platform_mgmt.instances.transport import CommandResult


def _runner_empty(argv, timeout):
    return CommandResult(argv=tuple(argv), returncode=0, stdout="", stderr="")


def test_parse_status_requires_keys(tmp_path: Path) -> None:
    path = tmp_path / "s.json"
    path.write_text("{}", encoding="utf-8")
    with pytest.raises(StatusFileError, match="missing required key"):
        parse_status(path)


def test_probe_uses_status_file_when_present(tmp_path: Path) -> None:
    home = tmp_path / "home"
    app = tmp_path / "app"
    (app / "kit").mkdir(parents=True)
    (app / "kit" / "VERSION").write_text("source_sha: deadbeefcafe\n", encoding="utf-8")
    status = home / STATUS_REL
    status.parent.mkdir(parents=True)
    status.write_text(
        json.dumps(
            {
                "pid": 4242,
                "port": 38471,
                "started_at": "2026-08-10T10:00:00Z",
                "version": "1a2b3c4d5e6f",
            }
        ),
        encoding="utf-8",
    )
    inst = Instance(
        name="alpha",
        kind="standalone",
        lifecycle="live",
        fields={"KIND": "standalone", "APP_ROOT": str(app), "HOME": str(home)},
        source="t",
    )
    reading = read_instance(inst, timeout=1, runner=_runner_empty)
    assert reading.verdict == HEALTHY
    labels = {f.label: f.value for f in reading.facts}
    assert labels["pid"] == "4242"
    assert labels["port"] == "38471"
    assert labels["version"] == "1a2b3c4d5e6f"
    assert not any(g.label == "health / running version" for g in reading.gaps)


def test_probe_keeps_gap_without_status_file(tmp_path: Path) -> None:
    home = tmp_path / "home"
    app = tmp_path / "app"
    home.mkdir()
    (app / "kit").mkdir(parents=True)
    (app / "kit" / "VERSION").write_text("source_sha: deadbeefcafe\n", encoding="utf-8")
    inst = Instance(
        name="alpha",
        kind="standalone",
        lifecycle="live",
        fields={"KIND": "standalone", "APP_ROOT": str(app), "HOME": str(home)},
        source="t",
    )
    reading = read_instance(inst, timeout=1, runner=_runner_empty)
    assert reading.verdict == STOPPED
    assert any(g.label == "health / running version" for g in reading.gaps)
