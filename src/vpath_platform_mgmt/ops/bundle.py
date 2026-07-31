"""Bundle an app directory and read its git provenance for upload.

The developer works in their app repo; this packs the app folder and the
facts about where it came from, so the server can record exactly what it
materialized (decision 16).
"""

from __future__ import annotations

import io
import subprocess
import tarfile
from pathlib import Path

MANIFEST = "vpath-app.yaml"
SKIP_DIRS = {".git", "node_modules", ".next", "__pycache__", ".venv", "venv"}


class BundleError(Exception):
    """The directory is not a usable app source bundle."""


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def provenance_of(app_dir: Path) -> dict[str, str]:
    """Repo URL, ref, commit and dirty flag for the app's checkout."""
    dirty = _git(app_dir, "status", "--porcelain", "--", ".")
    return {
        "repo": _git(app_dir, "config", "--get", "remote.origin.url"),
        "ref": _git(app_dir, "rev-parse", "--abbrev-ref", "HEAD"),
        "commit": _git(app_dir, "rev-parse", "HEAD"),
        "dirty": "true" if dirty else "false",
    }


def bundle(app_dir: Path) -> bytes:
    """tar.gz of the app directory, excluding build and VCS noise."""
    if not app_dir.is_dir():
        raise BundleError(f"not a directory: {app_dir}")
    if not (app_dir / MANIFEST).is_file():
        raise BundleError(
            f"{app_dir} has no {MANIFEST} — that file is what makes it an app"
        )
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for path in sorted(app_dir.rglob("*")):
            relative = path.relative_to(app_dir)
            if SKIP_DIRS & set(relative.parts):
                continue
            if path.is_symlink() or not (path.is_file() or path.is_dir()):
                continue
            archive.add(path, arcname=relative.as_posix(), recursive=False)
    return buffer.getvalue()
