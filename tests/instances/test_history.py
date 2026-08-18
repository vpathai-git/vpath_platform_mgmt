"""Append-only probe history beside the register."""

from __future__ import annotations

from pathlib import Path

import pytest

from vpath_platform_mgmt.instances import history
from vpath_platform_mgmt.instances.probe import Reading


def test_append_and_read_tail(tmp_path: Path) -> None:
    path = tmp_path / "instances.local.env.history.jsonl"
    reading = Reading("alpha", "standalone", "STOPPED")
    reading.add("running", "no process found", "ps")
    history.append_reading(path, reading)
    reading2 = Reading("alpha", "standalone", "HEALTHY")
    history.append_reading(path, reading2)
    events = history.read_tail(path, name="alpha", limit=10)
    assert len(events) == 2
    assert events[-1]["coarse"] == "HEALTHY"
    assert events[-1]["name"] == "alpha"
    assert "ts" in events[-1]


def test_read_tail_filters_by_name(tmp_path: Path) -> None:
    path = tmp_path / "h.jsonl"
    history.append_reading(path, Reading("alpha", "standalone", "STOPPED"))
    history.append_reading(path, Reading("bravo", "standalone", "PLANNED"))
    only = history.read_tail(path, name="bravo", limit=5)
    assert [e["name"] for e in only] == ["bravo"]


def test_history_path_beside_register(tmp_path: Path) -> None:
    register = tmp_path / "instances.local.env"
    assert (
        history.history_path(register) == tmp_path / "instances.local.env.history.jsonl"
    )


def test_malformed_line_is_skipped(tmp_path: Path) -> None:
    path = tmp_path / "h.jsonl"
    path.write_text("not-json\n", encoding="utf-8")
    history.append_reading(path, Reading("alpha", "standalone", "STOPPED"))
    events = history.read_tail(path, limit=10)
    assert len(events) == 1


def test_history_path_honours_env_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    override = tmp_path / "custom.history.jsonl"
    monkeypatch.setenv(history.HISTORY_ENV_VAR, str(override))
    assert history.history_path(tmp_path / "instances.local.env") == override


def test_read_tail_empty_when_missing_or_limit_zero(tmp_path: Path) -> None:
    missing = tmp_path / "absent.jsonl"
    assert history.read_tail(missing, limit=5) == []
    path = tmp_path / "h.jsonl"
    history.append_reading(path, Reading("alpha", "standalone", "STOPPED"))
    assert history.read_tail(path, limit=0) == []
