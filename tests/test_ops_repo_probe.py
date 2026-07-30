"""Tests for reading a repository through gh instead of cloning it."""

from __future__ import annotations

import base64
from collections.abc import Sequence
from pathlib import Path

import pytest

from vpath_platform_mgmt.ops.repo_fetch import FetchError, RunResult
from vpath_platform_mgmt.ops.repo_probe import (
    Probed,
    materialise,
    parse_slug,
    probe,
    read_file,
    resolve_commit,
)

SHA = "08f7f9e8c753a2ad2f71ecea43dabbc5ac58b0eb"
MANIFEST = "apiVersion: vpath/v1\nmetadata:\n  name: vpath-thing\n"


def encoded(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def responder(mapping: dict[str, RunResult]):
    """A gh whose answer depends on the path being asked for."""
    seen: list[list[str]] = []

    def runner(argv: Sequence[str], timeout: int) -> RunResult:
        seen.append(list(argv))
        for fragment, result in mapping.items():
            if any(fragment in part for part in argv):
                return result
        return RunResult(1, "", "gh: Not Found (HTTP 404)")

    return seen, runner


def test_slug_is_read_from_anything_a_human_pastes() -> None:
    for url in (
        "github.com/org/repo.git",
        "https://github.com/org/repo",
        "git@github.com:org/repo.git",
        "https://www.github.com/org/repo/",
    ):
        assert parse_slug(url) == "org/repo"


def test_a_non_github_host_is_refused_not_guessed() -> None:
    with pytest.raises(FetchError, match="only GitHub"):
        parse_slug("https://gitea.internal/org/repo.git")


def test_the_commit_is_resolved_so_provenance_records_a_sha() -> None:
    _, runner = responder({"commits/main": RunResult(0, SHA + "\n", "")})
    assert resolve_commit("org/repo", "main", runner) == SHA


def test_an_inaccessible_repo_explains_the_internal_case() -> None:
    """A 404 on an INTERNAL repo means auth, not absence."""
    _, runner = responder(
        {"commits/main": RunResult(1, "", "gh: Not Found (HTTP 404)")}
    )
    with pytest.raises(FetchError, match="gh auth status"):
        resolve_commit("org/private", "main", runner)


def test_a_missing_file_is_absence_not_failure() -> None:
    _, runner = responder({"contents/package.json": RunResult(0, encoded("{}"), "")})
    assert read_file("org/repo", "main", "package.json", runner) == "{}"
    assert read_file("org/repo", "main", "pyproject.toml", runner) is None


def test_probe_collects_only_the_files_registration_needs() -> None:
    seen, runner = responder(
        {
            "commits/main": RunResult(0, SHA, ""),
            "contents/vpath-app.yaml": RunResult(0, encoded(MANIFEST), ""),
            "contents/package.json": RunResult(0, encoded("{}"), ""),
        }
    )
    result = probe("github.com/org/repo.git", "main", runner)

    assert result.commit == SHA
    assert result.repo_url == "https://github.com/org/repo.git"
    assert set(result.files) == {"vpath-app.yaml", "package.json"}
    assert all(part != "clone" for call in seen for part in call)  # never clones


def test_materialise_hands_the_registry_an_ordinary_directory(tmp_path: Path) -> None:
    """The registry must not be able to tell a probe from a clone."""
    target = materialise(
        Probed("org/repo", "main", SHA, {"vpath-app.yaml": MANIFEST}),
        tmp_path / "probed",
    )
    assert (target / "vpath-app.yaml").read_text(encoding="utf-8") == MANIFEST
