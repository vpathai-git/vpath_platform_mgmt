"""Tests for fetching an app repository. No test here touches the network."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest

from vpath_platform_mgmt.ops.repo_fetch import (
    FetchError,
    RunResult,
    clone_argv,
    fetch,
    normalise_url,
)

COMMIT = "08f7f9e8c753a2ad2f71ecea43dabbc5ac58b0eb"


def recorder(*results: RunResult) -> tuple[list[list[str]], object]:
    """A runner that replays canned results and records every argv."""
    calls: list[list[str]] = []
    queue = list(results)

    def runner(argv: Sequence[str], timeout: int) -> RunResult:
        calls.append(list(argv))
        return queue.pop(0)

    return calls, runner


def test_a_pasted_url_is_made_usable() -> None:
    """github.com/org/repo is what comes out of a browser bar."""
    assert normalise_url("github.com/org/repo.git") == "https://github.com/org/repo.git"
    assert normalise_url(" https://x/y.git ") == "https://x/y.git"
    assert normalise_url("git@github.com:org/repo.git") == "git@github.com:org/repo.git"
    with pytest.raises(FetchError, match="no repository URL"):
        normalise_url("   ")


def test_clone_is_shallow_and_single_branch(tmp_path: Path) -> None:
    argv = clone_argv("https://x/y.git", "main", tmp_path / "t")
    assert argv[:2] == ["git", "clone"]
    assert "--depth" in argv and "1" in argv
    assert "--single-branch" in argv
    assert argv[argv.index("--branch") + 1] == "main"


def test_fetch_returns_the_resolved_commit(tmp_path: Path) -> None:
    calls, runner = recorder(RunResult(0, "", ""), RunResult(0, COMMIT + "\n", ""))
    result = fetch(
        "github.com/org/repo.git", "main", runner=runner, into=tmp_path / "clone"
    )
    assert result.commit == COMMIT
    assert result.repo == "https://github.com/org/repo.git"
    assert calls[1][:3] == ["git", "-C", str(tmp_path / "clone")]


def test_a_failed_clone_reports_gits_own_last_line(tmp_path: Path) -> None:
    """The operator needs git's reason, not our exit code."""
    _, runner = recorder(
        RunResult(128, "", "remote: Repository not found.\nfatal: could not read")
    )
    with pytest.raises(FetchError, match="fatal: could not read"):
        fetch("github.com/org/nope.git", "main", runner=runner, into=tmp_path / "c")


def test_a_missing_ref_names_the_ref(tmp_path: Path) -> None:
    _, runner = recorder(RunResult(128, "", "fatal: Remote branch nope not found"))
    with pytest.raises(FetchError, match="ref 'nope'"):
        fetch("github.com/org/repo.git", "nope", runner=runner, into=tmp_path / "c")


def test_an_unresolvable_head_is_refused(tmp_path: Path) -> None:
    _, runner = recorder(RunResult(0, "", ""), RunResult(0, "  \n", ""))
    with pytest.raises(FetchError, match="could not resolve HEAD"):
        fetch("github.com/org/repo.git", "main", runner=runner, into=tmp_path / "c")
