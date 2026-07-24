"""
Tests for scripts/check_template_drift.py and scripts/sync_from_template.py.

Builds a miniature template repository with real git history (two versions)
and a fake derived project, then verifies every classification state and the
apply/merge behavior — no network involved.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import check_template_drift as drift  # noqa: E402
import init_project as initp  # noqa: E402
import sync_from_template as sync  # noqa: E402

# Hook safety: when pytest runs inside a git hook (the pre-commit gate), git
# exports GIT_INDEX_FILE/GIT_DIR pointing at the REAL repo — without
# scrubbing, the fixtures' `git add` would corrupt the host repo's index.
GIT_CLEAN_ENV = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}

MAKEFILE_V1 = "run:\n\techo v1\n"
MAKEFILE_V2 = "run:\n\techo v2\n"
CONTRIB_V1 = "alpha\nbeta\ngamma\n"
CONTRIB_V2 = "alpha\nbeta\ngamma-improved\n"
CONTRIB_CUSTOM = "alpha-custom\nbeta\ngamma\n"  # project edited line 1 of v1
ENV_EXAMPLE = "APP_NAME=demo\n"


def run_git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", *args],
        check=True,
        capture_output=True,
        text=True,
        env=GIT_CLEAN_ENV,
    )
    return result.stdout.strip()


@pytest.fixture
def template_repo(tmp_path: Path) -> Path:
    """Two-commit template: v1, then v2 with an update, an add, a delete."""
    repo = tmp_path / "template"
    (repo / "context").mkdir(parents=True)
    (repo / "Makefile").write_text(MAKEFILE_V1, encoding="utf-8")
    (repo / "CONTRIBUTING.md").write_text(CONTRIB_V1, encoding="utf-8")
    (repo / ".env.example").write_text(ENV_EXAMPLE, encoding="utf-8")
    (repo / "context" / "old.md").write_text("old doc\n", encoding="utf-8")
    run_git(repo, "init", "-q")
    run_git(repo, "add", "-A")
    run_git(repo, "commit", "-qm", "v1")
    (repo / "Makefile").write_text(MAKEFILE_V2, encoding="utf-8")
    (repo / "CONTRIBUTING.md").write_text(CONTRIB_V2, encoding="utf-8")
    (repo / "context" / "old.md").unlink()
    (repo / "context" / "new.md").write_text("new doc\n", encoding="utf-8")
    run_git(repo, "add", "-A")
    run_git(repo, "commit", "-qm", "v2")
    return repo


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """Derived project stamped from template v1, with one customization."""
    root = tmp_path / "project"
    (root / "context").mkdir(parents=True)
    (root / "Makefile").write_text(MAKEFILE_V1, encoding="utf-8")  # pristine, stale
    (root / "CONTRIBUTING.md").write_text(CONTRIB_CUSTOM, encoding="utf-8")
    (root / ".env.example").write_text(ENV_EXAMPLE, encoding="utf-8")  # up to date
    (root / "context" / "old.md").write_text("old doc\n", encoding="utf-8")
    (root / "context" / "own.md").write_text("project-own file\n", encoding="utf-8")
    return root


def test_blob_sha_matches_git() -> None:
    # `echo hello | git hash-object --stdin` — the canonical git example
    assert sync.blob_sha(b"hello\n") == "ce013625030ba8dba906f756967f9e9ca394464a"


def test_template_files_enumerates_tracked_only(template_repo: Path) -> None:
    files = {p.as_posix() for p in drift.template_files(template_repo)}
    assert files == {"Makefile", "CONTRIBUTING.md", ".env.example", "context/new.md"}


def test_classify_all_five_states(template_repo: Path, project: Path) -> None:
    plan = sync.classify(project, template_repo)
    assert plan["same"] == [".env.example"]
    assert plan["new"] == ["context/new.md"]
    assert plan["update"] == ["Makefile"]
    assert plan["custom"] == ["CONTRIBUTING.md"]
    assert plan["remove"] == ["context/old.md"]
    # project-own file in a tracked dir is nobody's business
    all_buckets = [rel for bucket in plan.values() for rel in bucket]
    assert "context/own.md" not in all_buckets


def test_apply_updates_pristine_and_preserves_custom(
    template_repo: Path, project: Path
) -> None:
    plan = sync.classify(project, template_repo)
    unresolved = sync.execute(project, template_repo, plan, stamp=None, merge=False)
    assert (project / "Makefile").read_text(encoding="utf-8") == MAKEFILE_V2
    assert (project / "context" / "new.md").is_file()
    assert not (project / "context" / "old.md").exists()
    assert (project / "context" / "own.md").is_file()
    customized = (project / "CONTRIBUTING.md").read_text(encoding="utf-8")
    assert customized == CONTRIB_CUSTOM  # untouched without --merge
    assert unresolved == ["CONTRIBUTING.md"]


def test_merge_combines_local_and_template_changes(
    template_repo: Path, project: Path
) -> None:
    v1_sha = run_git(template_repo, "rev-parse", "HEAD~1")
    plan = sync.classify(project, template_repo)
    unresolved = sync.execute(project, template_repo, plan, stamp=v1_sha, merge=True)
    merged = (project / "CONTRIBUTING.md").read_text(encoding="utf-8")
    assert merged == "alpha-custom\nbeta\ngamma-improved\n"  # both edits, no markers
    assert unresolved == []


def test_read_stamp_both_formats(tmp_path: Path) -> None:
    assert drift.read_stamp(tmp_path) == (None, None)
    stamp = tmp_path / drift.STAMP_FILE
    stamp.write_text("abc123\n", encoding="utf-8")  # pre-flavor format: sha only
    assert drift.read_stamp(tmp_path) == ("abc123", None)
    stamp.write_text("abc123 flavor/java\n", encoding="utf-8")
    assert drift.read_stamp(tmp_path) == ("abc123", "flavor/java")


def test_history_blobs_ignores_other_branches(template_repo: Path) -> None:
    # A side branch shipping different content must not count as pristine.
    run_git(template_repo, "checkout", "-qb", "side")
    (template_repo / "Makefile").write_text("side-only\n", encoding="utf-8")
    run_git(template_repo, "add", "-A")
    run_git(template_repo, "commit", "-qm", "side version")
    run_git(template_repo, "checkout", "-q", "-")
    blobs = sync.history_blobs(template_repo)
    assert sync.blob_sha(b"side-only\n") not in blobs.get("Makefile", set())
    assert sync.blob_sha(MAKEFILE_V1.encode()) in blobs["Makefile"]


# --- optional context-visibility status line (opt-in, writes GLOBAL ~/.claude) ---
# These guard the opt-in contract: the setup item touches the user's global
# config, so it MUST do nothing without explicit consent (decision 007, Path X).


def test_statusline_decline_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The opt-in guard: declining must leave ~/.claude completely untouched.
    # Fails loud if anyone reverts this to a silent global write.
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("builtins.input", lambda *a, **k: "n")
    initp.optional_setup_context_statusline()
    assert not (tmp_path / ".claude").exists()


def test_statusline_consent_merges_without_clobber(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    claude = tmp_path / ".claude"
    claude.mkdir()
    (claude / "settings.json").write_text('{"theme": "dark"}\n', encoding="utf-8")
    monkeypatch.setattr("builtins.input", lambda *a, **k: "y")

    initp.optional_setup_context_statusline()

    data = json.loads((claude / "settings.json").read_text(encoding="utf-8"))
    assert data["theme"] == "dark"  # pre-existing key preserved, not clobbered
    assert data["statusLine"]["command"] == "bash ~/.claude/statusline-context.sh"
    script = claude / "statusline-context.sh"
    asset = Path(initp.__file__).parent / "assets" / "statusline-context.sh"
    assert script.read_text(encoding="utf-8") == asset.read_text(encoding="utf-8")


def test_statusline_is_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("builtins.input", lambda *a, **k: "y")
    initp.optional_setup_context_statusline()
    settings = tmp_path / ".claude" / "settings.json"
    first = settings.read_text(encoding="utf-8")
    initp.optional_setup_context_statusline()  # detects up-to-date, no rewrite
    assert settings.read_text(encoding="utf-8") == first


# --- the agent-facing hook (context-report) installed by the same opt-in ---
# The status line shows the user the fill; the hook injects the SAME figure into
# the model's context. These guard the hook half of the opt-in contract.


def test_hook_consent_registers_without_clobbering_other_hooks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    claude = tmp_path / ".claude"
    claude.mkdir()
    (claude / "settings.json").write_text(
        '{"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "beep"}]}]}}\n',
        encoding="utf-8",
    )
    monkeypatch.setattr("builtins.input", lambda *a, **k: "y")

    initp.optional_setup_context_statusline()

    data = json.loads((claude / "settings.json").read_text(encoding="utf-8"))
    assert data["hooks"]["Stop"][0]["hooks"][0]["command"] == "beep"  # preserved
    ups = data["hooks"]["UserPromptSubmit"]
    cmds = [h["command"] for e in ups for h in e["hooks"]]
    assert "bash ~/.claude/context-report.sh" in cmds
    script = claude / "context-report.sh"
    asset = Path(initp.__file__).parent / "assets" / "context-report.sh"
    assert script.read_text(encoding="utf-8") == asset.read_text(encoding="utf-8")


def test_hook_not_duplicated_on_rerun(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("builtins.input", lambda *a, **k: "y")
    initp.optional_setup_context_statusline()
    initp.optional_setup_context_statusline()
    settings = tmp_path / ".claude" / "settings.json"
    data = json.loads(settings.read_text(encoding="utf-8"))
    ups = data["hooks"]["UserPromptSubmit"]
    cmds = [h["command"] for e in ups for h in e["hooks"]]
    assert cmds.count("bash ~/.claude/context-report.sh") == 1


def test_context_visibility_missing_hook_asset_fails_hard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Guard (no silent degradation): a missing bundled asset must fail loud,
    # never a half-install. Status line present, hook asset absent.
    fake = tmp_path / "scripts"
    (fake / "assets").mkdir(parents=True)
    (fake / "assets" / "statusline-context.sh").write_text("x", encoding="utf-8")
    monkeypatch.setattr(initp, "__file__", str(fake / "init_project.py"))
    monkeypatch.setenv("HOME", str(tmp_path))
    with pytest.raises(FileNotFoundError):
        initp.optional_setup_context_statusline()
