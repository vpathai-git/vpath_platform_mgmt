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
    # Absolute location on this host. Never serialized: the console has no
    # business knowing server paths, and the browse API resolves by app name.
    directory: Path | None = None

    @property
    def shell_id(self) -> str:
        """The id the platform shell selects an app by.

        The generated app catalog derives it from the app name minus the
        ``vpath-`` prefix and ``-web`` suffix; the platform's ingress config
        documents the same derivation and asks that it be kept in lockstep.
        """
        shell_id = self.name.removeprefix("vpath-")
        return shell_id.removesuffix("-web")

    def to_dict(self, platform_url: str = "") -> dict[str, object]:
        """JSON view; ``url`` is empty unless a platform URL is configured.

        The link points at the platform SHELL (``/?app=<id>``), not at the
        app's bare basePath. A deep link to the basePath renders the app
        full-screen with no sidebar or shell chrome — the platform hosts apps
        in an iframe and selects them by catalog id.
        """
        url = ""
        if platform_url and self.base_path:
            url = f"{platform_url.rstrip('/')}/?app={self.shell_id}"
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
        directory=path.parent.resolve(),
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

    def entry(self, name: str) -> AppEntry | None:
        """One app by manifest name."""
        return next((item for item in self.entries() if item.name == name), None)
