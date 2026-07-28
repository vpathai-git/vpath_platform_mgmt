"""App catalog: the applications this management plane knows about.

Read from ``vpath-app.yaml`` manifests — the same file the server pipeline
discovers apps by — so the console can never show a different set than the
engine would build. Manifests are found one level down (``<dir>/<app>/``),
which is how both this repo's ``apps/`` folder and the server's
``apps_infra/apps/`` are laid out.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

MANIFEST = "vpath-app.yaml"


@dataclass(frozen=True)
class AppEntry:
    """One application, as the console lists it."""

    name: str
    title: str
    description: str
    base_path: str
    icon: str = ""
    app_type: str = ""
    port: int | None = None
    source: str = ""

    def to_dict(self, platform_url: str = "") -> dict[str, object]:
        """JSON view; ``url`` is empty unless a platform URL is configured."""
        url = ""
        if platform_url and self.base_path:
            url = platform_url.rstrip("/") + "/" + self.base_path.lstrip("/")
        return {
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "base_path": self.base_path,
            "icon": self.icon,
            "type": self.app_type,
            "port": self.port,
            "source": self.source,
            "url": url,
        }


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def entry_from_manifest(path: Path) -> AppEntry | None:
    """Parse one manifest into an entry, or None if it is not a VpathApp."""
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return None
    data = _as_dict(raw)
    spec = _as_dict(data.get("spec"))
    meta = _as_dict(data.get("metadata"))
    if not spec and not meta:
        return None
    ui = _as_dict(spec.get("ui"))
    name = str(meta.get("name") or path.parent.name)
    port = spec.get("port")
    return AppEntry(
        name=name,
        title=str(ui.get("title") or name),
        description=str(ui.get("description") or ""),
        base_path=str(spec.get("basePath") or ""),
        icon=str(ui.get("icon") or ""),
        app_type=str(spec.get("type") or ""),
        port=int(port) if isinstance(port, int) else None,
        source=path.parent.name,
    )


class AppCatalog:
    """Discovers applications under one or more app directories."""

    def __init__(self, *app_dirs: Path) -> None:
        self._dirs = [directory for directory in app_dirs if directory]

    @property
    def directories(self) -> list[Path]:
        """The directories scanned for manifests."""
        return list(self._dirs)

    def entries(self) -> list[AppEntry]:
        """All discoverable apps, de-duplicated by name, sorted by title."""
        found: dict[str, AppEntry] = {}
        for directory in self._dirs:
            if not directory.is_dir():
                continue
            for manifest in sorted(directory.glob(f"*/{MANIFEST}")):
                entry = entry_from_manifest(manifest)
                if entry is not None and entry.name not in found:
                    found[entry.name] = entry
        return sorted(found.values(), key=lambda item: item.title.lower())
