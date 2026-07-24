#!/usr/bin/env python3
"""Check this project for drift against the vpath_empty_project template.

Run from a project that was created from the template:

    python scripts/check_template_drift.py [--diff] [--repo URL] [--ref REF]

Fetches the current template and compares the template-managed files,
reporting three states:

  up to date  - identical here and in the template
  missing     - exists in the template but not in this project
  differs     - exists in both but content changed (template improved, or
                this project customized it - inspect with --diff)

Files this project added are ignored; by-design divergent files (src/,
tests/, README.md, pyproject.toml, ...) are never compared.

Exit codes: 0 = up to date, 1 = drift found, 2 = execution error.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

TEMPLATE_REPO_DEFAULT = "https://github.com/vpathai-git/vpath_empty_project.git"

# Hook safety: inside a git hook, git exports GIT_INDEX_FILE/GIT_DIR pointing
# at the HOST repo — our subprocess git calls must never inherit them, or
# operations on the template clone would corrupt the host repository's index.
GIT_CLEAN_ENV = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}

STAMP_FILE = ".template-version"

# Paths (relative to project root) meant to stay in sync with the template.
TRACKED: list[str] = [
    ".claude/",
    "context/",
    "githooks/",
    "scripts/",
    "config/",
    ".github/workflows/",
    "Makefile",
    "CONTRIBUTING.md",
    "CLAUDE.md",
    ".gitignore",
    ".env.example",
    "LICENSE.TXT",
]

# By design divergent, never compared: src/, tests/, README.md,
# pyproject.toml, requirements.txt, CHANGELOG.md.
# LICENSE.TXT is tracked since 2026-06-11 (decision: vpath-internal projects
# share identical license boilerplate; the vpath_agents migration surfaced a
# stale 2024 copyright). Projects with a genuinely different license: remove
# the entry from this list — it then shows as customized exactly once.

IGNORED_NAMES = {".DS_Store", "__pycache__", ".pytest_cache", ".mypy_cache"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_stamp(root: Path) -> tuple[str | None, str | None]:
    """Parse .template-version: '<sha> [<ref>]'. Returns (sha, ref) or Nones.

    The ref names the template flavor branch this project was stamped from
    (e.g. 'main', 'flavor/java'); older stamps carry only the sha.
    """
    stamp = root / STAMP_FILE
    if not stamp.is_file():
        return None, None
    tokens = stamp.read_text(encoding="utf-8").split()
    return (tokens[0] if tokens else None), (tokens[1] if len(tokens) > 1 else None)


def _on_rm_error(func: Callable[..., Any], path: str, _exc: Any) -> None:
    """Windows: git objects are read-only; make writable and retry."""
    Path(path).chmod(stat.S_IWRITE)
    func(path)


def clone_template(repo: str, ref: str) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="template_drift_"))
    cmd = ["git", "clone", "--quiet", "--depth", "1", "--branch", ref, repo, str(tmp)]
    result = subprocess.run(cmd, capture_output=True, text=True, env=GIT_CLEAN_ENV)
    if result.returncode != 0:
        shutil.rmtree(tmp, onerror=_on_rm_error)
        sys.exit(
            f"ERROR: could not clone template {repo} (ref {ref}):\n{result.stderr}"
        )
    return tmp


def template_files(template_root: Path) -> list[Path]:
    """All tracked files in the template, as paths relative to its root."""
    found: list[Path] = []
    for entry in TRACKED:
        target = template_root / entry
        if entry.endswith("/"):
            if not target.is_dir():
                continue
            for f in sorted(target.rglob("*")):
                if f.is_file() and not (set(f.parts) & IGNORED_NAMES):
                    found.append(f.relative_to(template_root))
        elif target.is_file():
            found.append(Path(entry))
    return found


def show_diff(project_file: Path, template_file: Path, rel: Path) -> None:
    local = project_file.read_text(encoding="utf-8", errors="replace").splitlines()
    remote = template_file.read_text(encoding="utf-8", errors="replace").splitlines()
    diff = difflib.unified_diff(
        local, remote, fromfile=f"project/{rel}", tofile=f"template/{rel}", lineterm=""
    )
    print("\n".join(diff))


Buckets = tuple[list[Path], list[Path], list[Path]]


def classify(project_root: Path, template_root: Path, show_diffs: bool) -> Buckets:
    """Sort tracked template files into (same, missing, differs)."""
    same: list[Path] = []
    missing: list[Path] = []
    differs: list[Path] = []
    for rel in template_files(template_root):
        local, remote = project_root / rel, template_root / rel
        if not local.is_file():
            missing.append(rel)
        elif sha256(local) == sha256(remote):
            same.append(rel)
        else:
            differs.append(rel)
            if show_diffs:
                show_diff(local, remote, rel)
    return same, missing, differs


def report(buckets: Buckets, verbose: bool) -> int:
    same, missing, differs = buckets
    total = len(same) + len(missing) + len(differs)
    print(f"Checked {total} tracked template files.\n")
    if verbose:
        for rel in same:
            print(f"  = up to date  {rel}")
    if missing:
        print("Missing here (new in template — consider adopting):")
        for rel in missing:
            print(f"  + {rel}")
    if differs:
        print("Differs (template improved, or customized here — see --diff):")
        for rel in differs:
            print(f"  ! {rel}")
    if not missing and not differs:
        print("Up to date regarding all tracked template files.")
        return 0
    print(f"\nDrift: {len(missing)} missing, {len(differs)} differing.")
    return 1


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    _, stamp_ref = read_stamp(project_root)
    parser = argparse.ArgumentParser(
        description="Check this project for drift against the project template."
    )
    parser.add_argument(
        "--repo", default=TEMPLATE_REPO_DEFAULT, help="template repo URL"
    )
    parser.add_argument(
        "--ref",
        default=stamp_ref or "main",
        help="template branch or tag (default: the stamped flavor ref, else main)",
    )
    parser.add_argument(
        "--diff", action="store_true", help="print diffs for differing files"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="also list up-to-date files"
    )
    args = parser.parse_args()

    template_root = clone_template(args.repo, args.ref)
    try:
        print(f"Template: {args.repo} (ref {args.ref})")
        return report(classify(project_root, template_root, args.diff), args.verbose)
    finally:
        shutil.rmtree(template_root, onerror=_on_rm_error)


if __name__ == "__main__":
    sys.exit(main())
