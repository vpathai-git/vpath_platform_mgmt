"""Register an app repository into ``apps/<name>/`` so it can be sent.

See docs/superpowers/specs/2026-07-30-app-registry-design.md. Two files are
written per app and nothing else:

    vpath-app.yaml     the app's manifest
    vpath-source.yaml  where it came from, and where the manifest came from

An app repository that ships its own ``vpath-app.yaml`` is taken as authored:
the file is copied byte for byte and the generation flags are refused as
meaningless. A repository without one gets a manifest generated here, which is
faster to onboard but puts a second copy of the app's identity in this repo.
``manifest_origin`` is what keeps that copy honest -- ``refresh`` adopts an
upstream manifest the moment one appears, so the generated file is always
visibly provisional and upstream always wins.

Nothing here is a fallback: a repository that cannot be described is refused
with the specific reason, never registered half-way.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

from vpath_platform_mgmt.ops.apps import AppCatalog
from vpath_platform_mgmt.ops.tree_hash import TreeHashError, git_tree_sha

MANIFEST_NAME = "vpath-app.yaml"
PROVENANCE_NAME = "vpath-source.yaml"
UPSTREAM = "upstream"
GENERATED = "generated"
SAFE_NAME = re.compile(r"^[a-z][a-z0-9-]{2,49}$")
DEFAULT_ICON = "box"


class RegistryError(Exception):
    """The app could not be registered, and nothing was written."""


@dataclass(frozen=True)
class Generated:
    """The facts a manifest cannot be invented without."""

    name: str
    port: int
    base_path: str
    title: str
    description: str = ""
    icon: str = DEFAULT_ICON
    runtime: str = ""


@dataclass(frozen=True)
class Registration:
    """What was written, and where its manifest came from."""

    name: str
    directory: Path
    manifest_origin: str
    commit: str


def detect_runtime(tree: Path) -> str:
    """node or python, from what the repository actually contains.

    Ambiguity is not resolved by preference: two runtimes or none means the
    caller must say, because guessing wrong produces an app that builds into
    nothing and fails much later.
    """
    node = (tree / "package.json").is_file()
    python = (tree / "pyproject.toml").is_file()
    if node and not python:
        return "node"
    if python and not node:
        return "python"
    found = "both package.json and pyproject.toml" if node else "neither"
    raise RegistryError(
        f"cannot tell the runtime from the repository ({found} present) — "
        "pass --runtime node|python"
    )


def build_manifest(spec: Generated) -> dict[str, object]:
    """A manifest derived from four given facts and nothing invented."""
    base = spec.base_path.rstrip("/") or f"/{spec.name}"
    health = f"{base}/api/healthz"
    return {
        "apiVersion": "vpath/v1",
        "kind": "VpathApp",
        "metadata": {
            "name": spec.name,
            "namespace": spec.name,
            "labels": {"app.kubernetes.io/part-of": "vpath"},
        },
        "spec": {
            "type": "web",
            "image": spec.name,
            "basePath": base,
            "port": spec.port,
            "auth": {"oidcClient": spec.name},
            "health": {
                "readiness": health,
                "liveness": health,
                "scheme": "HTTPS",
            },
            "ui": {
                "title": spec.title,
                "description": spec.description,
                "icon": spec.icon or DEFAULT_ICON,
                "sidebar": True,
            },
            "build": {
                "runtime": spec.runtime,
                "hash": {"dirs": [f"apps_infra/apps/{spec.name}"]},
            },
        },
    }


class AppRegistry:
    """Owns ``apps/`` — the only writer of app entries in this repository."""

    def __init__(self, root: Path) -> None:
        self._root = Path(root)

    def entries(self) -> list[dict[str, object]]:
        """Registered apps with their provenance, newest field set included."""
        found: list[dict[str, object]] = []
        for folder in sorted(self._root.glob(f"*/{PROVENANCE_NAME}")):
            data = yaml.safe_load(folder.read_text(encoding="utf-8")) or {}
            found.append({"name": folder.parent.name, **data})
        return found

    def _ports_in_use(self, excluding: str) -> dict[int, str]:
        """Every port the catalog can already see, and which app holds it."""
        held: dict[int, str] = {}
        for entry in AppCatalog(self._root).entries():
            if entry.name != excluding and entry.port is not None:
                held[entry.port] = entry.name
        return held

    def register(
        self,
        repo: str,
        ref: str,
        commit: str,
        tree: Path,
        generate: Generated | None = None,
        replace: bool = False,
        path: str = "",
    ) -> Registration:
        """Write one app entry from an already-fetched tree."""
        upstream_manifest = Path(tree) / MANIFEST_NAME
        if upstream_manifest.is_file():
            if generate is not None:
                raise RegistryError(
                    f"{repo} ships its own {MANIFEST_NAME}; it is taken as "
                    "authored, so --name/--port/--base-path/--title do not apply"
                )
            text = upstream_manifest.read_text(encoding="utf-8")
            name = self._name_from(text, repo)
            origin = UPSTREAM
        else:
            if generate is None:
                raise RegistryError(
                    f"{repo} ships no {MANIFEST_NAME}, so one must be generated "
                    "— pass --name, --port, --base-path and --title"
                )
            name = generate.name
            text = yaml.safe_dump(build_manifest(generate), sort_keys=False)
            origin = GENERATED

        self._check_name(name)
        target = self._root / name
        if target.exists() and not replace:
            raise RegistryError(
                f"'{name}' is already registered — pass --replace to overwrite it"
            )
        self._check_port(text, name)
        self._write(
            target,
            text,
            repo=repo,
            ref=ref,
            commit=commit,
            origin=origin,
            path=path,
        )
        self._verify_readable(name, target)
        return Registration(name, target, origin, commit)

    def refresh(self, name: str, tree: Path, commit: str) -> Registration:
        """Re-record a fetched tree; adopt upstream's manifest if it appeared.

        Upstream always wins. A manifest generated here is provisional by
        definition, so the moment the app repository ships its own, ours is
        replaced and the origin recorded as upstream.
        """
        target = self._root / name
        provenance = target / PROVENANCE_NAME
        if not provenance.is_file():
            raise RegistryError(f"'{name}' is not registered here")
        previous = yaml.safe_load(provenance.read_text(encoding="utf-8")) or {}

        upstream_manifest = Path(tree) / MANIFEST_NAME
        origin = str(previous.get("manifest_origin", GENERATED))
        text = (target / MANIFEST_NAME).read_text(encoding="utf-8")
        if upstream_manifest.is_file():
            text = upstream_manifest.read_text(encoding="utf-8")
            origin = UPSTREAM

        self._write(
            target,
            text,
            repo=str(previous.get("repo", "")),
            ref=str(previous.get("ref", "main")),
            commit=commit,
            origin=origin,
            path=str(previous.get("path", "")),
        )
        self._verify_readable(name, target)
        return Registration(name, target, origin, commit)

    def stamp_tree(self, name: str, tree: Path) -> str:
        """Bind a registered source record to its complete fetched tree."""
        provenance = self._root / name / PROVENANCE_NAME
        if not provenance.is_file():
            raise RegistryError(f"'{name}' is not registered here")
        recorded = yaml.safe_load(provenance.read_text(encoding="utf-8")) or {}
        if not isinstance(recorded, dict):
            raise RegistryError(f"'{name}' has unreadable {PROVENANCE_NAME}")
        try:
            tree_sha = git_tree_sha(tree)
        except TreeHashError as exc:
            raise RegistryError(
                f"cannot hash the source tree for '{name}': {exc}"
            ) from exc
        recorded["tree_sha"] = tree_sha
        provenance.write_text(
            yaml.safe_dump(recorded, sort_keys=False), encoding="utf-8"
        )
        return tree_sha

    def _name_from(self, manifest_text: str, repo: str) -> str:
        parsed = yaml.safe_load(manifest_text) or {}
        metadata = parsed.get("metadata") if isinstance(parsed, dict) else None
        name = metadata.get("name") if isinstance(metadata, dict) else None
        if not isinstance(name, str) or not name:
            raise RegistryError(
                f"{repo}: its {MANIFEST_NAME} declares no metadata.name"
            )
        return name

    def _check_name(self, name: str) -> None:
        if not SAFE_NAME.match(name):
            raise RegistryError(
                f"'{name}' is not a usable app name — lowercase letters, "
                "digits and dashes, starting with a letter"
            )

    def _check_port(self, manifest_text: str, name: str) -> None:
        parsed = yaml.safe_load(manifest_text) or {}
        spec = parsed.get("spec") if isinstance(parsed, dict) else None
        port = spec.get("port") if isinstance(spec, dict) else None
        if not isinstance(port, int):
            return
        holder = self._ports_in_use(excluding=name).get(port)
        if holder is not None:
            raise RegistryError(
                f"port {port} is already used by '{holder}' — ports are never "
                "assigned automatically, pick a free one"
            )

    def _write(
        self,
        target: Path,
        manifest_text: str,
        repo: str,
        ref: str,
        commit: str,
        origin: str,
        path: str = "",
    ) -> None:
        target.mkdir(parents=True, exist_ok=True)
        (target / MANIFEST_NAME).write_text(manifest_text, encoding="utf-8")
        provenance = {
            "repo": repo,
            "ref": ref,
            "commit": commit,
            "path": path,
            "manifest_origin": origin,
            "added_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        (target / PROVENANCE_NAME).write_text(
            yaml.safe_dump(provenance, sort_keys=False), encoding="utf-8"
        )

    def _verify_readable(self, name: str, target: Path) -> None:
        """The console must never be handed a manifest it cannot parse."""
        if any(entry.name == name for entry in AppCatalog(self._root).entries()):
            return
        raise RegistryError(
            f"the manifest written for '{name}' is not readable by the catalog"
        )
