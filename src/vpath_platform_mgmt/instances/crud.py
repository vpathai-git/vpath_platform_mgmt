"""Create, update and remove instances -- the write half of the register.

Everything here edits the operator's gitignored register file in place, and
every write ends the same way: the file is re-read through :func:`registry.load`
before it is kept.  If the result would not parse, the original content is put
back and the caller is told why.  A register that has been left half-written is
worse than one that refused the edit.

Comments and layout the operator wrote are preserved: edits are line-oriented,
not a re-serialisation of a parsed model.  The only comment this module ever
deletes is the stanza header it wrote itself.
"""

from __future__ import annotations

from pathlib import Path

from . import templates
from .registry import NAME_RE, RegistryError, load, parse_lines
from .templates import Template, TemplateError

DECLARATION_KEY = "VPATH_INSTANCES"

_HEADER = """
# =============================================================================
# instances.local.env -- the platform instance register (gitignored payload)
# =============================================================================
# Created by vpath_platform_mgmt from its versioned type templates.
# Values here are yours and are never committed; the templates that shape them
# are versioned in src/vpath_platform_mgmt/instances/templates/.
# =============================================================================

"""


def _read(path: Path) -> list[str]:
    if not path.is_file():
        return _HEADER.lstrip("\n").splitlines()
    return path.read_text(encoding="utf-8").splitlines()


def _declared_names(lines: list[str]) -> list[str]:
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(f"{DECLARATION_KEY}="):
            return stripped.split("=", 1)[1].split()
    return []


def _set_declaration(lines: list[str], names: list[str]) -> list[str]:
    """Rewrite (or introduce) the one ``VPATH_INSTANCES`` line."""
    rendered = f"{DECLARATION_KEY}={' '.join(names)}"
    out = []
    replaced = False
    for line in lines:
        if line.strip().startswith(f"{DECLARATION_KEY}=") and not replaced:
            out.append(rendered)
            replaced = True
        else:
            out.append(line)
    if not replaced:
        out.extend(["", rendered])
    return out


def _commit(path: Path, lines: list[str], previous: str | None) -> None:
    """Write the file, then prove it still parses -- or put the old one back.

    ``previous`` is the exact original text, or ``None`` when the register did
    not exist; in that case a rejected write removes the file again rather than
    leaving an unusable stub behind.
    """
    path.write_text("\n".join(lines).rstrip("\n") + "\n", encoding="utf-8")
    try:
        load(path)
    except RegistryError as exc:
        if previous is None:
            path.unlink(missing_ok=True)
        else:
            path.write_text(previous, encoding="utf-8")
        raise RegistryError(f"edit rejected, register left unchanged -- {exc}") from exc


def _original(path: Path) -> str | None:
    return path.read_text(encoding="utf-8") if path.is_file() else None


def create(
    path: Path,
    name: str,
    template_name: str,
    values: dict[str, str],
) -> Template:
    """Add one instance, shaped by a versioned type template.

    The template decides which fields exist and which are mandatory; this
    function only refuses what the template or the register would refuse.
    """
    if not NAME_RE.match(name):
        raise RegistryError(
            f"instance name {name!r} must be lower-case alphanumeric "
            f"starting with a letter"
        )
    template = templates.load_template(template_name)
    templates.validate(template, values)

    lines = _read(path)
    declared = _declared_names(lines)
    if name in declared:
        raise RegistryError(f"{path}: instance {name!r} is already declared")

    lines = _set_declaration(lines, declared + [name])
    lines.extend(["", templates.render_stanza(template, name, values).rstrip("\n")])
    _commit(path, lines, _original(path))
    return template


def update(path: Path, name: str, changes: dict[str, str]) -> None:
    """Set fields on an existing instance.

    An empty value removes the field's line -- that is how an operator retracts
    a claim, and it is different from writing an empty string into the
    register, which would look like a declared blank.
    """
    if not changes:
        raise RegistryError(f"{path}: update of {name!r} changes nothing")
    if not path.is_file():
        raise RegistryError(f"no instance register at {path}")

    previous = _original(path)
    lines = path.read_text(encoding="utf-8").splitlines()
    if name not in _declared_names(lines):
        raise RegistryError(f"{path}: instance {name!r} is not declared")

    _reject_unknown_fields(name, lines, changes)
    prefix = f"{name.upper()}_"
    remaining = dict(changes)
    out: list[str] = []
    for line in lines:
        key = _assigned_key(line)
        if key is None or not key.startswith(prefix):
            out.append(line)
            continue
        field = key[len(prefix) :]
        if field not in remaining:
            out.append(line)
            continue
        value = remaining.pop(field).strip()
        if value:
            out.append(f"{key}={value}")
    for field, value in remaining.items():
        if value.strip():
            out.append(f"{prefix}{field}={value.strip()}")
    _commit(path, out, previous)


def _reject_unknown_fields(
    name: str, lines: list[str], changes: dict[str, str]
) -> None:
    """Refuse a field the instance's own template does not declare.

    Without this a typo becomes a silently ignored setting -- the register
    would look edited and behave as before.
    """
    values = parse_lines(lines, "register")
    kind = values.get(f"{name.upper()}_KIND", "")
    try:
        template = templates.template_for_kind(kind)
    except TemplateError:
        return
    known = {f.key for f in template.fields} | {"KIND"}
    unknown = sorted(set(changes) - known)
    if unknown:
        raise RegistryError(
            f"template {template.name!r} declares no field(s): {', '.join(unknown)}"
        )


def _assigned_key(line: str) -> str | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None
    key = stripped.split("=", 1)[0]
    return key if key.isidentifier() else None


def remove(path: Path, name: str) -> None:
    """Drop one instance: its declaration, its fields, and its own header."""
    if not path.is_file():
        raise RegistryError(f"no instance register at {path}")
    previous = _original(path)
    lines = path.read_text(encoding="utf-8").splitlines()
    declared = _declared_names(lines)
    if name not in declared:
        raise RegistryError(f"{path}: instance {name!r} is not declared")
    if len(declared) == 1:
        raise RegistryError(
            f"{path}: {name!r} is the only declared instance -- a register that "
            f"declares nothing is not a valid register; delete the file instead"
        )

    prefix = f"{name.upper()}_"
    header = f"# --- {name} ("
    kept = [
        line
        for line in lines
        if not (_assigned_key(line) or "").startswith(prefix)
        and not line.strip().startswith(header)
    ]
    _commit(path, _set_declaration(kept, [n for n in declared if n != name]), previous)
