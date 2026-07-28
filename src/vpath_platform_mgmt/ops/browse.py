"""Read-only file browsing inside an application's folder.

Backs the Application Explorer: the operator can inspect what an app
actually contains before deploying it. Strictly read-only and strictly
inside the app directory — the same paranoia as ops/source.py, which does
the writing.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from vpath_platform_mgmt.ops.apps import AppCatalog

SKIP_DIRS = {".git", "node_modules", ".next", "__pycache__", ".venv", "venv"}
MAX_BYTES = 256 * 1024
MAX_ENTRIES = 2000
BINARY_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".webp",
    ".pdf",
    ".zip",
    ".gz",
    ".tgz",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".jar",
    ".class",
}


class BrowseError(Exception):
    """Browsing refused; the message says why."""


@dataclass(frozen=True)
class Node:
    """One entry in an app's file tree."""

    path: str
    is_dir: bool
    size: int = 0

    def to_dict(self) -> dict[str, object]:
        """JSON view."""
        return {"path": self.path, "dir": self.is_dir, "size": self.size}


class AppBrowser:
    """Lists and reads files under an app's directory."""

    def __init__(self, catalog: AppCatalog) -> None:
        self._catalog = catalog

    def _root(self, app: str) -> Path:
        entry = self._catalog.entry(app)
        if entry is None or entry.directory is None:
            raise BrowseError(f"unknown application '{app}'")
        return entry.directory

    def _resolve(self, app: str, relative: str) -> Path:
        """Resolve a path inside the app, refusing anything that escapes."""
        root = self._root(app)
        candidate = (root / relative).resolve()
        if candidate != root and root not in candidate.parents:
            raise BrowseError(f"path '{relative}' escapes the application folder")
        return candidate

    def tree(self, app: str) -> list[Node]:
        """Every file and folder in the app, excluding build and VCS noise."""
        root = self._root(app)
        nodes: list[Node] = []
        for path in sorted(root.rglob("*")):
            relative = path.relative_to(root)
            if SKIP_DIRS & set(relative.parts):
                continue
            if path.is_symlink():
                continue
            if path.is_dir():
                nodes.append(Node(relative.as_posix(), True))
            elif path.is_file():
                nodes.append(Node(relative.as_posix(), False, path.stat().st_size))
            if len(nodes) >= MAX_ENTRIES:
                break
        return nodes

    def read(self, app: str, relative: str) -> dict[str, object]:
        """Text content of one file, size-capped; binaries are refused."""
        target = self._resolve(app, relative)
        if not target.is_file():
            raise BrowseError(f"not a file: {relative}")
        if target.suffix.lower() in BINARY_SUFFIXES:
            raise BrowseError(f"{target.name} is a binary file — not shown")
        size = target.stat().st_size
        data = target.read_bytes()[:MAX_BYTES]
        if b"\x00" in data:
            raise BrowseError(f"{target.name} looks binary — not shown")
        return {
            "path": relative,
            "size": size,
            "truncated": size > MAX_BYTES,
            "content": data.decode("utf-8", errors="replace"),
        }
