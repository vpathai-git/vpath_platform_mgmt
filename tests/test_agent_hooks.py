"""Tests for shared agent hook scripts."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import agent_hooks.post_edit_check as hook  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_post_edit_hook_missing_python_tools_fails_hard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    edited = tmp_path / "example.py"
    edited.write_text("print('x')\n", encoding="utf-8")
    monkeypatch.setenv("PATH", str(tmp_path / "no-tools"))
    checks = hook.checks_for(edited, tmp_path)
    assert len(checks) == 1
    assert checks[0].returncode == 2
    assert "edit NOT checked" in checks[0].stderr


def test_codex_hooks_do_not_install_post_tool_use() -> None:
    hook_config = REPO_ROOT / ".codex" / "hooks.json"
    data = json.loads(hook_config.read_text(encoding="utf-8"))
    assert "PostToolUse" not in data["hooks"]


def test_codex_skills_reuse_claude_skills() -> None:
    skills = REPO_ROOT / ".codex" / "skills"
    if skills.is_symlink():
        assert skills.readlink() == Path("../.claude/skills")
        assert (skills / "careful-commit" / "SKILL.md").is_file()
    else:
        # Windows checkouts without symlink support materialize the link as
        # a text file holding the target path — the reuse contract still
        # holds and the target must exist.
        assert skills.read_text(encoding="utf-8").strip() == "../.claude/skills"
        assert (
            REPO_ROOT / ".claude" / "skills" / "careful-commit" / "SKILL.md"
        ).is_file()


def test_codex_stop_hook_uses_completion_chime() -> None:
    hook_config = REPO_ROOT / ".codex" / "hooks.json"
    data = json.loads(hook_config.read_text(encoding="utf-8"))
    hooks = data["hooks"]["Stop"][0]["hooks"]
    commands = [entry["command"] for entry in hooks]
    assert any("scripts/assets/completion-chime.sh" in cmd for cmd in commands)
