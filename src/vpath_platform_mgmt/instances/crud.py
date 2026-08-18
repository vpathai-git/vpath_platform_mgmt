"""Write the instance register: create, update, remove.

Reads and writes the same ``KEY=VALUE`` format ``registry.load`` accepts.
Never invents hosts or keys; missing required fields raise.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Mapping

from .registry import (
    ALL_LIFECYCLES,
    LIFECYCLE_LIVE,
    NAME_RE,
    RegistryError,
    load,
    parse_lines,
)
from .templates import TemplateError, load_template


def _read_values(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    return parse_lines(path.read_text(encoding="utf-8").splitlines(), str(path))


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=".instances.", suffix=".tmp"
    )
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        tmp.replace(path)
    except Exception:
        if tmp.is_file():
            tmp.unlink()
        raise


def _render(values: Mapping[str, str], names: list[str]) -> str:
    lines = [
        "# written by vpath_platform_mgmt.instances.crud",
        f"VPATH_INSTANCES={' '.join(names)}",
        "",
    ]
    for name in names:
        prefix = f"{name.upper()}_"
        keys = sorted(k for k in values if k.startswith(prefix))
        for key in keys:
            lines.append(f"{key}={values[key]}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _validate_fields(
    name: str,
    kind: str,
    lifecycle: str,
    fields: Mapping[str, str],
    source: str,
) -> None:
    try:
        tpl = load_template(kind)
    except TemplateError as exc:
        raise RegistryError(str(exc)) from exc
    if lifecycle not in ALL_LIFECYCLES:
        raise RegistryError(
            f"{source}: lifecycle {lifecycle!r}; expected one of "
            f"{', '.join(sorted(ALL_LIFECYCLES))}"
        )
    if lifecycle == LIFECYCLE_LIVE:
        missing = [key for key in tpl.required if not fields.get(key)]
        if missing:
            prefix = f"{name.upper()}_"
            raise RegistryError(
                f"{source}: instance {name!r} ({kind}) is missing "
                + ", ".join(f"{prefix}{key}" for key in missing)
            )


def create(
    path: Path,
    name: str,
    kind: str,
    fields: Mapping[str, str],
    *,
    lifecycle: str = LIFECYCLE_LIVE,
) -> None:
    """Append a new instance to the register file."""
    if not NAME_RE.match(name):
        raise RegistryError(
            f"instance name {name!r} must be lower-case alphanumeric "
            f"starting with a letter"
        )
    values = _read_values(path)
    names = values.get("VPATH_INSTANCES", "").split()
    if name in names:
        raise RegistryError(f"instance {name!r} already declared in {path}")
    merged = dict(fields)
    merged["KIND"] = kind
    merged["LIFECYCLE"] = lifecycle
    _validate_fields(name, kind, lifecycle, merged, str(path))
    prefix = f"{name.upper()}_"
    for key, value in merged.items():
        values[f"{prefix}{key}"] = value
    names.append(name)
    values["VPATH_INSTANCES"] = " ".join(names)
    _atomic_write(path, _render(values, names))
    load(path).get(name)


def update(path: Path, name: str, fields: Mapping[str, str]) -> None:
    """Merge field updates into an existing instance."""
    registry = load(path)
    instance = registry.get(name)
    values = _read_values(path)
    names = list(registry.names())
    prefix = f"{name.upper()}_"
    merged = dict(instance.fields)
    merged.update(fields)
    kind = merged.get("KIND", instance.kind)
    lifecycle = merged.get("LIFECYCLE", instance.lifecycle)
    _validate_fields(name, kind, lifecycle, merged, str(path))
    for key in list(values):
        if key.startswith(prefix):
            del values[key]
    for key, value in merged.items():
        values[f"{prefix}{key}"] = value
    values["VPATH_INSTANCES"] = " ".join(names)
    _atomic_write(path, _render(values, names))
    load(path).get(name)


def remove(path: Path, name: str) -> None:
    """Drop one instance and its prefixed fields."""
    registry = load(path)
    registry.get(name)
    values = _read_values(path)
    names = [n for n in registry.names() if n != name]
    if not names:
        raise RegistryError(
            f"{path}: refusing to remove the last instance -- "
            f"VPATH_INSTANCES would be empty"
        )
    prefix = f"{name.upper()}_"
    for key in list(values):
        if key.startswith(prefix):
            del values[key]
    values["VPATH_INSTANCES"] = " ".join(names)
    _atomic_write(path, _render(values, names))
    load(path)
