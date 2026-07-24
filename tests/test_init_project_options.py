"""Tests for optional global setup items in scripts/init_project.py."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import init_project as initp  # noqa: E402


def test_completion_chime_decline_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("builtins.input", lambda *a, **k: "n")
    initp.optional_setup_completion_chime()
    assert not (tmp_path / ".claude").exists()


def test_completion_chime_consent_preserves_existing_stop_hook(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(initp, "completion_chime_supported", lambda: True)
    claude = tmp_path / ".claude"
    claude.mkdir()
    (claude / "settings.json").write_text(
        '{"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "beep"}]}]}}\n',
        encoding="utf-8",
    )
    monkeypatch.setattr("builtins.input", lambda *a, **k: "y")
    initp.optional_setup_completion_chime()
    data = json.loads((claude / "settings.json").read_text(encoding="utf-8"))
    cmds = [h["command"] for e in data["hooks"]["Stop"] for h in e["hooks"]]
    assert "beep" in cmds
    assert "bash ~/.claude/completion-chime.sh" in cmds


def test_completion_chime_not_duplicated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(initp, "completion_chime_supported", lambda: True)
    monkeypatch.setattr("builtins.input", lambda *a, **k: "y")
    initp.optional_setup_completion_chime()
    initp.optional_setup_completion_chime()
    data = json.loads(
        (tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8")
    )
    cmds = [h["command"] for e in data["hooks"]["Stop"] for h in e["hooks"]]
    assert cmds.count("bash ~/.claude/completion-chime.sh") == 1


def test_completion_chime_missing_asset_fails_hard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = tmp_path / "scripts" / "init_project.py"
    fake.parent.mkdir()
    monkeypatch.setattr(initp, "__file__", str(fake))
    with pytest.raises(FileNotFoundError):
        initp.optional_setup_completion_chime()
