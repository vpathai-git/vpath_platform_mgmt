"""The Deploy-of-Record InstalledSet: what ArgoCD is allowed to run.

The server's GitOps cutover made a git repository the deploy authority:
``platform/k8s-manifests`` in the in-cluster Gitea holds ``installed-set.json``
next to the rendered payloads, and the ``vpath-apps`` ApplicationSet generates
one child Application per app *named in that set*. Publishing an app is
therefore a commit, not a command.

This module is the set's grammar and nothing else — no I/O, no HTTP. It
mirrors ``validate_set`` in the server's ``lib/pipeline/deploy-record-template.sh``
so the management plane cannot write a record the engine would reject.
"""

from __future__ import annotations

import json
import re
from typing import Any

SCHEMA_VERSION = 1
KINDS: dict[str, str] = {"app": "apps", "workflow": "workflows"}
NAME = re.compile(r"^[a-z0-9.-]+$")
INSTALLED_SET_PATH = "installed-set.json"


class InstalledSetError(Exception):
    """The set is malformed, or a mutation of it was refused."""


def array_for(kind: str) -> str:
    """The set's array name for a template kind."""
    try:
        return KINDS[kind]
    except KeyError as exc:
        raise InstalledSetError(
            f"invalid template kind '{kind}' (expected app or workflow)"
        ) from exc


def validate_name(name: str) -> str:
    """A DNS-style lowercase template name, or fail hard."""
    if not NAME.fullmatch(name):
        raise InstalledSetError(
            f"invalid template name '{name}' (expected DNS-style lowercase)"
        )
    return name


def _validate_array(data: dict[str, Any], key: str) -> list[str]:
    names = data.get(key)
    if not isinstance(names, list):
        raise InstalledSetError(f"malformed InstalledSet: '{key}' is not an array")
    for name in names:
        if not isinstance(name, str):
            raise InstalledSetError(
                f"malformed InstalledSet: '{key}' holds a non-string"
            )
        validate_name(name)
    if len(set(names)) != len(names):
        raise InstalledSetError(f"malformed InstalledSet: '{key}' has duplicates")
    return names


def parse(text: str) -> dict[str, Any]:
    """Parse and fully validate an ``installed-set.json`` document."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise InstalledSetError(f"InstalledSet is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise InstalledSetError("malformed InstalledSet: top level is not an object")
    if data.get("schema_version") != SCHEMA_VERSION:
        raise InstalledSetError(
            f"unsupported InstalledSet schema_version {data.get('schema_version')!r} "
            f"(expected {SCHEMA_VERSION})"
        )
    for key in KINDS.values():
        _validate_array(data, key)
    return data


def dump(data: dict[str, Any]) -> str:
    """Serialize a set the way the engine's ``jq`` writes it."""
    return json.dumps(data, indent=2, sort_keys=True) + "\n"


def contains(data: dict[str, Any], kind: str, name: str) -> bool:
    """Whether the set already names this template."""
    return validate_name(name) in data[array_for(kind)]


def add(data: dict[str, Any], kind: str, name: str) -> dict[str, Any]:
    """A copy of the set with ``name`` installed (sorted, unique)."""
    key = array_for(kind)
    names = sorted(set(data[key]) | {validate_name(name)})
    return {**data, key: names}


def remove(data: dict[str, Any], kind: str, name: str) -> dict[str, Any]:
    """A copy of the set with ``name`` uninstalled."""
    key = array_for(kind)
    validate_name(name)
    return {**data, key: [item for item in data[key] if item != name]}


def payload_path(kind: str, name: str) -> str:
    """Where the rendered manifests for a template live in the record."""
    return f"{array_for(kind)}/{validate_name(name)}"


def appset_input_path(name: str) -> str:
    """Where an app's ApplicationSet input JSON lives in the record."""
    return f"appset-inputs/{validate_name(name)}.json"


def archived_input_path(name: str) -> str:
    """Where uninstall parks an app's input so install can bring it back.

    The ApplicationSet generates a child Application per file in
    ``appset-inputs/``, so removing the file is what actually uninstalls an
    app. Deleting it outright made the operation one-way: re-installing then
    required a fresh render on the build host. Parking it one directory down
    — outside the generator's view — keeps uninstall effective while leaving
    the exact rendered input, digest included, available to install again.
    """
    return f"uninstalled/{validate_name(name)}.json"
