"""Versioned instance kind templates (M1).

Each YAML file under this package declares required fields and whether live
ops are allowed (``ops: live``) or refused (``ops: unproven``).
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Any

import yaml

OPS_LIVE = "live"
OPS_UNPROVEN = "unproven"
ALL_OPS = frozenset({OPS_LIVE, OPS_UNPROVEN})


class TemplateError(Exception):
    """A kind template is missing or malformed."""


@dataclass(frozen=True)
class KindTemplate:
    """One environment kind as declared in YAML."""

    kind: str
    ops: str
    required: tuple[str, ...]
    path_fields: frozenset[str]
    optional: tuple[str, ...] = ()

    @property
    def allows_live_ops(self) -> bool:
        return self.ops == OPS_LIVE


def _package_dir() -> Path:
    return Path(__file__).resolve().parent


def kinds() -> tuple[str, ...]:
    """Every kind that has a template file, sorted."""
    names = sorted(path.stem for path in _package_dir().glob("*.yaml"))
    return tuple(names)


def _parse(data: Any, source: str) -> KindTemplate:
    if not isinstance(data, dict):
        raise TemplateError(f"{source}: template root must be a mapping")
    kind = data.get("kind")
    if not isinstance(kind, str) or not kind:
        raise TemplateError(f"{source}: kind must be a non-empty string")
    ops = data.get("ops", OPS_LIVE)
    if ops not in ALL_OPS:
        raise TemplateError(
            f"{source}: ops is {ops!r}; expected one of {', '.join(sorted(ALL_OPS))}"
        )
    required = data.get("required") or []
    optional = data.get("optional") or []
    path_fields = data.get("path_fields") or []
    if not isinstance(required, list) or not all(isinstance(x, str) for x in required):
        raise TemplateError(f"{source}: required must be a list of strings")
    if not isinstance(optional, list) or not all(isinstance(x, str) for x in optional):
        raise TemplateError(f"{source}: optional must be a list of strings")
    if not isinstance(path_fields, list) or not all(
        isinstance(x, str) for x in path_fields
    ):
        raise TemplateError(f"{source}: path_fields must be a list of strings")
    return KindTemplate(
        kind=kind,
        ops=ops,
        required=tuple(required),
        optional=tuple(optional),
        path_fields=frozenset(path_fields),
    )


@lru_cache(maxsize=None)
def load_template(kind: str) -> KindTemplate:
    """Load one kind template. Raises rather than inventing fields."""
    path = _package_dir() / f"{kind}.yaml"
    if path.is_file():
        text = path.read_text(encoding="utf-8")
        source = str(path)
    else:
        try:
            ref = resources.files(__package__).joinpath(f"{kind}.yaml")
            if not ref.is_file():
                raise TemplateError(
                    f"unknown kind {kind!r}; expected one of {', '.join(kinds())}"
                )
            text = ref.read_text(encoding="utf-8")
            source = f"{__package__}/{kind}.yaml"
        except TemplateError:
            raise
        except (FileNotFoundError, TypeError, AttributeError, OSError) as exc:
            raise TemplateError(
                f"unknown kind {kind!r}; expected one of {', '.join(kinds())}"
            ) from exc
    data = yaml.safe_load(text)
    tpl = _parse(data, source)
    if tpl.kind != kind:
        raise TemplateError(f"{source}: kind {tpl.kind!r} does not match file {kind!r}")
    return tpl


def path_fields() -> frozenset[str]:
    """Union of path-valued fields across every template."""
    fields: set[str] = set()
    for kind in kinds():
        fields |= set(load_template(kind).path_fields)
    return frozenset(fields)
