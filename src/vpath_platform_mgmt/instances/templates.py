"""Versioned type templates -- the one place a new instance is shaped from.

The decision this implements (M1, 2026-07-27)
---------------------------------------------
*Declarative + kind hooks.*  One versioned template per instance type declares
the fields, which of them are mandatory, and their defaults.  Type-specific
*behaviour* is not duplicated here -- it stays in the kind hooks that already
exist (:mod:`.transport`, :mod:`.probe`).  Creating an instance is therefore:
copy the template, fill the payload, validate.

Why JSON and not YAML
---------------------
The decision said "template YAML".  YAML costs a third-party parser, and
``AGENTS.md`` puts stdlib ahead of a new dependency; the format was incidental
to the decision, the *versioned declarative file per type* was the substance.
So the templates are JSON, read with :mod:`json`, and the human-facing comments
they carry are rendered into the register stanza rather than into the file
itself -- which is where an operator actually reads them.

The templates are versioned here (they are mechanism).  The values an operator
fills in are payload and land in the gitignored register.  That split is the
axis definition, not an implementation detail.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .instance import ALL_KINDS

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
PLACEHOLDER = "<fill in>"


class TemplateError(Exception):
    """A template is absent, malformed, or was filled in incompletely."""


@dataclass(frozen=True)
class TemplateField:
    """One field an instance of this type may -- or must -- declare."""

    key: str
    comment: str
    required: bool = False
    default: str = ""
    example: str = ""

    @property
    def suggestion(self) -> str:
        """What the rendered stanza offers when the operator gave no value."""
        return self.default or self.example or PLACEHOLDER


@dataclass(frozen=True)
class Template:
    """A versioned creation template for one instance type."""

    name: str
    version: str
    kind: str
    title: str
    summary: str
    fields: tuple[TemplateField, ...]
    proven: bool = True
    unproven_reason: str = ""
    source: str = ""

    def field(self, key: str) -> TemplateField:
        for candidate in self.fields:
            if candidate.key == key:
                return candidate
        raise TemplateError(f"template {self.name!r} declares no field {key!r}")

    @property
    def required_keys(self) -> tuple[str, ...]:
        return tuple(f.key for f in self.fields if f.required)


def available() -> tuple[str, ...]:
    """Every type template shipped with this package, alphabetically."""
    return tuple(sorted(p.stem for p in TEMPLATE_DIR.glob("*.json")))


def _field_from(raw: object, template_name: str, source: str) -> TemplateField:
    if not isinstance(raw, dict):
        raise TemplateError(
            f"{source}: template {template_name!r} has a non-object field"
        )
    key = raw.get("key", "")
    if not isinstance(key, str) or not key:
        raise TemplateError(f"{source}: a field of {template_name!r} has no key")
    return TemplateField(
        key=key,
        comment=str(raw.get("comment", "")),
        required=bool(raw.get("required", False)),
        default=str(raw.get("default", "")),
        example=str(raw.get("example", "")),
    )


def load_template(name: str) -> Template:
    """Read one type template.  Raises rather than inventing a shape."""
    path = TEMPLATE_DIR / f"{name}.json"
    if not path.is_file():
        raise TemplateError(
            f"no type template {name!r} -- this package ships "
            f"{', '.join(available()) or '<none>'}"
        )
    source = str(path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TemplateError(f"{source}: not readable as JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise TemplateError(f"{source}: a template must be a JSON object")

    kind = str(raw.get("kind", ""))
    if kind not in ALL_KINDS:
        raise TemplateError(
            f"{source}: kind {kind!r} is not one of {', '.join(sorted(ALL_KINDS))}"
        )
    fields = tuple(
        _field_from(item, name, source) for item in raw.get("fields", []) or []
    )
    if not fields:
        raise TemplateError(f"{source}: template {name!r} declares no fields")

    proven = bool(raw.get("proven", True))
    reason = str(raw.get("unproven_reason", ""))
    if not proven and not reason:
        raise TemplateError(
            f"{source}: template {name!r} is marked unproven without a reason -- "
            f"an unproven template must say what is not established"
        )
    return Template(
        name=name,
        version=str(raw.get("template_version", "")),
        kind=kind,
        title=str(raw.get("title", name)),
        summary=str(raw.get("summary", "")),
        fields=fields,
        proven=proven,
        unproven_reason=reason,
        source=source,
    )


def load_all() -> tuple[Template, ...]:
    """Every shipped template, in the order :func:`available` lists them."""
    return tuple(load_template(name) for name in available())


def template_for_kind(kind: str) -> Template:
    """The template that creates instances of this kind.

    Several templates may map to one kind only if that is a real distinction;
    today the mapping is one-to-one, and an ambiguous one raises rather than
    picking the first match.
    """
    matches = [t for t in load_all() if t.kind == kind]
    if not matches:
        raise TemplateError(f"no type template creates kind {kind!r}")
    if len(matches) > 1:
        raise TemplateError(
            f"kind {kind!r} is claimed by several templates: "
            + ", ".join(t.name for t in matches)
        )
    return matches[0]


def missing_required(template: Template, values: dict[str, str]) -> tuple[str, ...]:
    """Which mandatory fields the operator has not filled in.

    A value left at the placeholder counts as missing: a stanza written with
    ``<fill in>`` still in it would parse, and would then point the tooling at
    a box that does not exist.
    """
    return tuple(
        key
        for key in template.required_keys
        if not values.get(key, "").strip() or values.get(key, "").strip() == PLACEHOLDER
    )


def validate(template: Template, values: dict[str, str]) -> None:
    """Raise unless every mandatory field of this template carries a value."""
    unknown = sorted(set(values) - {f.key for f in template.fields})
    if unknown:
        raise TemplateError(
            f"template {template.name!r} declares no field(s): {', '.join(unknown)}"
        )
    missing = missing_required(template, values)
    if missing:
        raise TemplateError(
            f"template {template.name!r} still needs {', '.join(missing)}"
        )


def render_stanza(template: Template, name: str, values: dict[str, str]) -> str:
    """The register block for one new instance, comments and all.

    Unfilled optional fields are emitted commented out rather than blank, so
    the operator sees what the type *could* answer without the register
    carrying an empty claim.
    """
    prefix = name.upper()
    lines = [
        f"# --- {name} ({template.title}) "
        f"-- from template {template.name} v{template.version} ".ljust(78, "-"),
    ]
    if template.summary:
        lines.append(f"# {template.summary}")
    if not template.proven:
        lines.append(f"# UNPROVEN: {template.unproven_reason}")
    lines.append(f"{prefix}_KIND={template.kind}")
    for item in template.fields:
        given = values.get(item.key, "").strip()
        if item.comment:
            lines.append(f"#   {item.comment}")
        if given:
            lines.append(f"{prefix}_{item.key}={given}")
        elif item.required:
            lines.append(f"{prefix}_{item.key}={item.suggestion}")
        else:
            lines.append(f"# {prefix}_{item.key}={item.suggestion}")
    return "\n".join(lines) + "\n"
