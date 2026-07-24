"""
Tests for scripts/check_skill_assumptions.py.

Builds synthetic fable-team SKILL.md files under tmp_path and verifies the
full exit-code contract (0 fresh / 1 stale / 2 broken), plus one test
against the real repo file so the shipped assumptions block stays parseable.
"""

import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import check_skill_assumptions as csa  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]


def write_skill(root: Path, body: str) -> None:
    skill = root / csa.SKILL_REL_PATH
    skill.parent.mkdir(parents=True)
    skill.write_text(body, encoding="utf-8")


def block(validated: date, horizon_days: int = 180) -> str:
    return (
        f"{csa.SENTINEL_BEGIN}\n"
        "```yaml\n"
        "tier_judgment: fable\n"
        f"validated: {validated.isoformat()}\n"
        f"review_horizon_days: {horizon_days}\n"
        "```\n"
        f"{csa.SENTINEL_END}\n"
    )


def test_fresh_block_exits_0(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_skill(tmp_path, block(date.today()))
    assert csa.check(tmp_path) == 0
    assert "fresh" in capsys.readouterr().out


def test_stale_block_exits_1_with_banner(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_skill(tmp_path, block(date.today() - timedelta(days=200), 180))
    assert csa.check(tmp_path) == 1
    assert "FOOD-CHAIN REVALIDATION DUE" in capsys.readouterr().out


def test_missing_required_key_exits_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    body = (
        f"{csa.SENTINEL_BEGIN}\n"
        "```yaml\n"
        "review_horizon_days: 180\n"
        "```\n"
        f"{csa.SENTINEL_END}\n"
    )
    write_skill(tmp_path, body)
    assert csa.check(tmp_path) == 2
    assert "validated" in capsys.readouterr().err


def test_missing_sentinels_exits_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_skill(tmp_path, "# a skill without an assumptions block\n")
    assert csa.check(tmp_path) == 2
    assert "sentinel" in capsys.readouterr().err


def test_unparseable_date_exits_2(tmp_path: Path) -> None:
    body = (
        f"{csa.SENTINEL_BEGIN}\n"
        "validated: soonish\n"
        "review_horizon_days: 180\n"
        f"{csa.SENTINEL_END}\n"
    )
    write_skill(tmp_path, body)
    assert csa.check(tmp_path) == 2


def test_skill_absent_exits_0_stated(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert csa.check(tmp_path) == 0
    assert "not present" in capsys.readouterr().out


def write_claude_md(
    root: Path,
    validated: date,
    horizon_days: int = 180,
    tree: str = "",
    ontogate: str = "not-adopted",
) -> None:
    structure = f"## Project Structure\n```\n{tree}\n```\n\n" if tree else ""
    agents_body = "# Shared Governance\n\n" f"{structure}"
    (root / csa.AGENTS_MD_REL_PATH).write_text(agents_body, encoding="utf-8")
    claude_body = (
        "# Claude Adapter\n\n"
        "@AGENTS.md\n\n"
        f"{csa.CLAUDE_MD_BEGIN}\n"
        f"validated: {validated.isoformat()}\n"
        f"review_horizon_days: {horizon_days}\n"
        f"ontogate: {ontogate}\n"
        f"{csa.CLAUDE_MD_END}\n"
    )
    (root / csa.CLAUDE_MD_REL_PATH).write_text(claude_body, encoding="utf-8")


def test_claude_md_fresh_exits_0(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_claude_md(tmp_path, date.today())
    assert csa.check(tmp_path) == 0
    assert "CLAUDE.md validated" in capsys.readouterr().out


def test_claude_md_stale_exits_1_with_banner(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_claude_md(tmp_path, date.today() - timedelta(days=200), 180)
    assert csa.check(tmp_path) == 1
    assert "CLAUDE.MD REVALIDATION DUE" in capsys.readouterr().out


def test_claude_md_without_stamp_exits_2(tmp_path: Path) -> None:
    (tmp_path / csa.AGENTS_MD_REL_PATH).write_text("# Shared\n", encoding="utf-8")
    (tmp_path / csa.CLAUDE_MD_REL_PATH).write_text(
        "# Claude Adapter\n\n@AGENTS.md\n", encoding="utf-8"
    )
    assert csa.check(tmp_path) == 2


def test_claude_md_without_agents_md_exits_2(tmp_path: Path) -> None:
    write_claude_md(tmp_path, date.today())
    (tmp_path / csa.AGENTS_MD_REL_PATH).unlink()
    assert csa.check(tmp_path) == 2


def test_claude_md_without_agents_import_exits_2(tmp_path: Path) -> None:
    write_claude_md(tmp_path, date.today())
    claude = tmp_path / csa.CLAUDE_MD_REL_PATH
    claude.write_text(claude.read_text(encoding="utf-8").replace("@AGENTS.md", ""))
    assert csa.check(tmp_path) == 2


def test_claude_md_duplicating_shared_governance_exits_2(tmp_path: Path) -> None:
    write_claude_md(tmp_path, date.today())
    claude = tmp_path / csa.CLAUDE_MD_REL_PATH
    claude.write_text(claude.read_text(encoding="utf-8") + "\n## Hard Rules\n")
    assert csa.check(tmp_path) == 2


def test_worst_code_wins_across_targets(tmp_path: Path) -> None:
    write_skill(tmp_path, block(date.today()))  # fresh skill -> 0
    write_claude_md(tmp_path, date.today() - timedelta(days=400))  # stale -> 1
    assert csa.check(tmp_path) == 1


TREE = "project/\n├── src/\n│   └── pkg/\n└── pyproject.toml"


def test_structure_tree_matching_reality_exits_0(tmp_path: Path) -> None:
    (tmp_path / "src" / "pkg").mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    write_claude_md(tmp_path, date.today(), tree=TREE)
    assert csa.check(tmp_path) == 0


def test_structure_tree_naming_missing_path_exits_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "src").mkdir()  # pkg/ missing -> nested entry is stale
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    write_claude_md(tmp_path, date.today(), tree=TREE)
    assert csa.check(tmp_path) == 2
    assert "src/pkg" in capsys.readouterr().err


def test_ontogate_adopted_with_real_gate_exits_0(tmp_path: Path) -> None:
    gate = tmp_path / ".ontogate" / "check.py"
    gate.parent.mkdir(parents=True)
    gate.write_text("print('gate')\n", encoding="utf-8")
    write_claude_md(tmp_path, date.today(), ontogate=".ontogate/check.py")
    assert csa.check(tmp_path) == 0


def test_ontogate_claimed_but_gate_missing_exits_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_claude_md(tmp_path, date.today(), ontogate=".ontogate/check.py")
    assert csa.check(tmp_path) == 2
    assert "claims adoption" in capsys.readouterr().err


def test_context_decay_absent_is_skipped(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # The context-decay block is optional: a CLAUDE.md without it must not fail.
    write_claude_md(tmp_path, date.today())
    assert csa.check(tmp_path) == 0
    assert "context-decay rule not present" in capsys.readouterr().out


def test_context_decay_stale_exits_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    today = date.today().isoformat()
    stale = (date.today() - timedelta(days=200)).isoformat()
    (tmp_path / csa.AGENTS_MD_REL_PATH).write_text("# Shared\n", encoding="utf-8")
    body = (
        "# Project Context\n\n"
        "@AGENTS.md\n\n"
        f"{csa.CLAUDE_MD_BEGIN}\n"
        f"validated: {today}\n"
        "review_horizon_days: 180\n"
        "ontogate: not-adopted\n"
        f"{csa.CLAUDE_MD_END}\n\n"
        f"{csa.CONTEXT_DECAY_BEGIN}\n"
        f"validated: {stale}\n"
        "review_horizon_days: 120\n"
        f"{csa.CONTEXT_DECAY_END}\n"
    )
    (tmp_path / csa.CLAUDE_MD_REL_PATH).write_text(body, encoding="utf-8")
    assert csa.check(tmp_path) == 1
    assert "CONTEXT-DECAY REVALIDATION DUE" in capsys.readouterr().out


def test_real_repo_block_is_fresh() -> None:
    assert csa.check(REPO_ROOT) == 0
