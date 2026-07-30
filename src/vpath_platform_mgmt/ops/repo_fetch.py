"""Fetch an app repository at a ref, and report the commit that arrived.

One job: get a working tree out of git and name the commit it stands on. It
knows nothing about applications, manifests or the catalog, so the registry
above it can be tested without git and this can be tested without a network.

Shallow by design (``--depth 1``): the registry only ever needs the tree at
one ref, and nothing here wants history. There is deliberately no clone cache
-- a cached tree would let us report a commit that is not the one that would
ship, which is the failure this module exists to make impossible.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

CLONE_TIMEOUT_SECONDS = 180

# git writes progress to stderr and we never parse it; only the commit is read
# from stdout, so a Runner needs to return both plus the code.
Runner = Callable[[Sequence[str], int], "RunResult"]


class FetchError(Exception):
    """The repository or ref could not be fetched."""


@dataclass(frozen=True)
class RunResult:
    """What a git invocation produced."""

    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


@dataclass(frozen=True)
class Fetched:
    """A tree on disk and the commit it stands on."""

    path: Path
    commit: str
    repo: str
    ref: str


def run(argv: Sequence[str], timeout: int) -> RunResult:
    """Invoke git with a fixed argv; no shell, so no quoting to get wrong."""
    completed = subprocess.run(  # noqa: S603 - fixed argv, never a shell
        list(argv),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    return RunResult(completed.returncode, completed.stdout, completed.stderr)


def normalise_url(url: str) -> str:
    """Accept what a human pastes; hand git something it understands.

    ``github.com/org/repo.git`` is what comes out of a browser bar, and git
    treats a schemeless string as a local path -- so it would fail with a
    confusing "does not exist" rather than a network error.
    """
    trimmed = url.strip()
    if not trimmed:
        raise FetchError("no repository URL given")
    if "://" in trimmed or trimmed.startswith("git@"):
        return trimmed
    return "https://" + trimmed.lstrip("/")


def clone_argv(url: str, ref: str, target: Path) -> list[str]:
    """The one command this module runs."""
    return [
        "git",
        "clone",
        "--depth",
        "1",
        "--branch",
        ref,
        "--single-branch",
        url,
        str(target),
    ]


def fetch(
    url: str,
    ref: str = "main",
    runner: Runner = run,
    into: Path | None = None,
) -> Fetched:
    """Clone ``url`` at ``ref`` and resolve the commit; raise on any failure."""
    if into is not None:
        target = Path(into)
    else:
        target = Path(tempfile.mkdtemp(prefix="vpath-app-"))
    normalised = normalise_url(url)
    cloned = runner(clone_argv(normalised, ref, target), CLONE_TIMEOUT_SECONDS)
    if not cloned.ok:
        shutil.rmtree(target, ignore_errors=True)
        raise FetchError(_why(normalised, ref, cloned))

    resolved = runner(["git", "-C", str(target), "rev-parse", "HEAD"], 30)
    if not resolved.ok or not resolved.stdout.strip():
        shutil.rmtree(target, ignore_errors=True)
        raise FetchError(f"{normalised}: cloned {ref} but could not resolve HEAD")
    return Fetched(
        path=target, commit=resolved.stdout.strip(), repo=normalised, ref=ref
    )


def _why(url: str, ref: str, result: RunResult) -> str:
    """git's own last line beats a generic exit code."""
    lines = [line for line in result.stderr.strip().splitlines() if line.strip()]
    detail = lines[-1] if lines else f"exit {result.returncode}"
    return f"cannot fetch {url} at ref '{ref}': {detail}"
