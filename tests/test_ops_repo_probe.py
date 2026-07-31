"""Tests for reading a repository through gh instead of cloning it."""

from __future__ import annotations

import base64
from collections.abc import Sequence
from pathlib import Path

import pytest

from vpath_platform_mgmt.ops.repo_fetch import FetchError, RunResult
from vpath_platform_mgmt.ops.repo_probe import (
    Probed,
    clean_ref,
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


def test_the_app_may_live_in_a_subdirectory_of_the_repository() -> None:
    """A workspace root is not an app; examples/<app> is."""
    _, runner = responder(
        {
            "commits/main": RunResult(0, SHA + "\n", ""),
            "contents/examples/vpath-knowledge-builder/vpath-app.yaml": RunResult(
                0, encoded(MANIFEST), ""
            ),
        }
    )

    probed = probe(
        "github.com/org/repo",
        "main",
        runner,
        path="examples/vpath-knowledge-builder",
    )

    assert probed.path == "examples/vpath-knowledge-builder"
    assert probed.files == {"vpath-app.yaml": MANIFEST}


def test_a_probe_without_a_path_still_reads_the_repository_root() -> None:
    _, runner = responder(
        {
            "commits/main": RunResult(0, SHA + "\n", ""),
            "contents/vpath-app.yaml": RunResult(0, encoded(MANIFEST), ""),
        }
    )

    probed = probe("github.com/org/repo", "main", runner)

    assert probed.path == ""
    assert probed.files == {"vpath-app.yaml": MANIFEST}


def test_a_path_a_human_pasted_with_slashes_asks_a_clean_url() -> None:
    seen, runner = responder({"commits/main": RunResult(0, SHA + "\n", "")})

    probe("github.com/org/repo", "main", runner, path="/examples/app/")

    asked = [part for argv in seen for part in argv if "contents/" in part]
    assert asked
    assert all("contents/examples/app/" in part for part in asked)


def test_a_query_string_smuggled_in_the_path_is_refused_not_forwarded() -> None:
    """A stray '?' would become the URL's first '?', hijacking ``ref``."""
    seen, runner = responder({"commits/main": RunResult(0, SHA + "\n", "")})

    with pytest.raises(FetchError, match="not a usable path"):
        probe("github.com/org/repo", "main", runner, path="app?ref=malicious&x=")

    assert seen == []  # refused before any credentialed call is made


def test_a_path_that_walks_out_of_the_repository_is_refused() -> None:
    seen, runner = responder({"commits/main": RunResult(0, SHA + "\n", "")})

    with pytest.raises(FetchError, match="not a usable path"):
        probe("github.com/org/repo", "main", runner, path="examples/../secrets")

    assert seen == []


def test_a_path_with_a_backslash_is_refused() -> None:
    seen, runner = responder({"commits/main": RunResult(0, SHA + "\n", "")})

    with pytest.raises(FetchError, match="not a usable path"):
        probe("github.com/org/repo", "main", runner, path="examples\\app")

    assert seen == []


def test_an_owner_or_repository_with_an_odd_charset_is_refused() -> None:
    """Both are concatenated into the same credentialed gh api URL as path."""
    for url in (
        "github.com/org?x=1/repo",
        "github.com/org/repo?ref=other",
        "github.com/org/..",
    ):
        with pytest.raises(FetchError, match="not a usable"):
            parse_slug(url)


def test_a_ref_that_would_hijack_the_api_url_is_refused() -> None:
    """``ref`` is a path segment in repos/<slug>/commits/<ref>."""
    with pytest.raises(FetchError, match="not a usable ref"):
        clean_ref("main?x=1")
    with pytest.raises(FetchError, match="not a usable ref"):
        clean_ref("../../other")
    with pytest.raises(FetchError, match="no ref given"):
        clean_ref("   ")
    assert clean_ref(" release/1.0 ") == "release/1.0"


def test_the_manifest_is_read_at_the_resolved_commit_not_at_the_branch() -> None:
    """A branch that moves would otherwise ship a tree we never inspected."""
    seen, runner = responder(
        {
            "commits/main": RunResult(0, SHA + "\n", ""),
            "contents/vpath-app.yaml": RunResult(0, encoded(MANIFEST), ""),
        }
    )

    probe("github.com/org/repo", "main", runner)

    asked = [part for argv in seen for part in argv if "contents/" in part]
    assert asked
    assert all(part.endswith("?ref=" + SHA) for part in asked), asked


def test_a_member_escaping_into_a_sibling_directory_is_refused(tmp_path: Path) -> None:
    """``startswith`` accepted ``/tree-evil`` beside ``/tree``."""
    import tarfile

    from vpath_platform_mgmt.ops.repo_probe import _extract_stripped

    root = tmp_path / "tree"
    root.mkdir()
    (tmp_path / "tree-evil").mkdir()
    member = tarfile.TarInfo("prefix/../tree-evil/stolen.txt")
    member.size = 0

    with tarfile.open(tmp_path / "empty.tar", "w") as archive:
        with pytest.raises(FetchError, match="escape"):
            _extract_stripped(archive, member, root)
