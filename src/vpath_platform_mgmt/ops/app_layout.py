"""Where the server puts an app's tree and the SDKs its manifest declares.

Split out of ``app_preflight`` along the seam between "where the server puts
things" (this module) and "what is wrong with this repository" (the gate
itself), to keep each module under the project's line limit.
"""

from __future__ import annotations

import posixpath
from dataclasses import dataclass
from pathlib import Path

import yaml

APPS_ROOT = "apps_infra/apps"
MANIFEST = "vpath-app.yaml"


@dataclass(frozen=True)
class Build:
    """What the manifest says about building this app."""

    hash_dirs: tuple[str, ...]
    sdks: dict[str, str]


def _build_block(tree: Path) -> dict[str, object]:
    manifest = tree / MANIFEST
    if not manifest.is_file():
        return {}
    parsed = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
    spec = parsed.get("spec") if isinstance(parsed, dict) else None
    build = spec.get("build") if isinstance(spec, dict) else None
    return build if isinstance(build, dict) else {}


def read_build(tree: Path) -> Build:
    """The hashed directories and declared SDKs, however sparse the manifest."""
    block = _build_block(tree)
    hashed = block.get("hash")
    dirs = hashed.get("dirs") if isinstance(hashed, dict) else None
    declared = block.get("sdks")
    sdks: dict[str, str] = {}
    for entry in declared if isinstance(declared, list) else []:
        if isinstance(entry, dict) and entry.get("name"):
            sdks[str(entry["name"])] = str(entry.get("source", "")).strip("/")
    hashes = (
        tuple(str(entry).strip("/") for entry in dirs) if isinstance(dirs, list) else ()
    )
    return Build(hashes, sdks)


def home_of(app: str) -> str:
    """Where the server puts this app's own tree."""
    return f"{APPS_ROOT}/{app}"


def resolve(app: str, target: str) -> str:
    """Where a path written inside the app lands in the server tree."""
    if target.startswith("/"):
        return target.rstrip("/")
    return posixpath.normpath(f"{home_of(app)}/{target}")


def inside(app: str, resolved: str) -> bool:
    """Whether a resolved path is still the app's own directory."""
    home = home_of(app)
    return resolved == home or resolved.startswith(f"{home}/")


def as_file_path(app: str, source: str) -> str:
    """The dependency path an app would have to write to reach ``source``."""
    return f"file:{posixpath.relpath(source, home_of(app))}"
