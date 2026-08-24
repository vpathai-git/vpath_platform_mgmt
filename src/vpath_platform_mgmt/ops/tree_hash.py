"""Compute the Git tree identity recorded by app source provenance.

The server-side twin lives in
``test_infra/extra/test_app_home_is_single.py`` in ``vpath_server``.  A
cross-repository import is impossible, so both use the same temporary-index
chain and pin it independently with a known Git tree in their tests.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

GIT_TIMEOUT_SECONDS = 30


class TreeHashError(Exception):
    """A source tree could not be represented as a Git tree."""


def git_tree_sha(tree: Path) -> str:
    """Return the Git tree object hash for an ordinary source directory."""
    source = Path(tree).resolve()
    if not source.is_dir():
        raise TreeHashError(f"source tree not found: {source}")

    with tempfile.TemporaryDirectory(prefix="vpath-tree-sha-") as temporary:
        git_dir = Path(temporary) / "objects.git"
        index = Path(temporary) / "index"
        _git(["init", "--bare", "--quiet", str(git_dir)], os.environ.copy())
        environment = os.environ.copy()
        environment.update(
            {
                "GIT_DIR": str(git_dir),
                "GIT_WORK_TREE": str(source),
                "GIT_INDEX_FILE": str(index),
            }
        )
        _git(["add", "."], environment)
        return _git(["write-tree"], environment).strip()


def _git(arguments: list[str], environment: dict[str, str]) -> str:
    completed = subprocess.run(  # noqa: S603 - fixed executable, no shell
        ["git", *arguments],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=environment,
        timeout=GIT_TIMEOUT_SECONDS,
    )
    if completed.returncode == 0:
        return completed.stdout
    detail = completed.stderr.strip().splitlines()
    reason = detail[-1] if detail else f"exit {completed.returncode}"
    raise TreeHashError(f"git {' '.join(arguments)} failed: {reason}")
