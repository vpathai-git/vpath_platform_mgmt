"""The one entry point the console is driven through -- shell or terminal.

Every command prints JSON with ``--json`` and readable text without it, so the
Electron shell and a human operator use the *same* code path.  A second,
shell-only path would be a second truth about the register.

Commands
--------
    view [--probe]              every instance in the generic dual view
    templates                   the versioned type templates and their fields
    create <name> --template T --set K=V ...
    update <name> --set K=V ...
    remove <name>

Exit codes
----------
    0   the command ran and succeeded
    1   the command ran and the action was refused (bad values, name taken)
    2   the truth could not be established: no register, unknown instance
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from ..instances import crud, probe, transport
from ..instances.registry import RegistryError, default_register_path, load
from ..instances.templates import Template, TemplateError, load_all
from ..instances.transport import Runner
from . import view

EXIT_OK = 0
EXIT_REFUSED = 1
EXIT_UNDETERMINED = 2


def template_payload(template: Template) -> dict[str, Any]:
    """One template in the shape a creation form is built from."""
    return {
        "name": template.name,
        "version": template.version,
        "kind": template.kind,
        "title": template.title,
        "summary": template.summary,
        "proven": template.proven,
        "unproven_reason": template.unproven_reason,
        "fields": [
            {
                "key": f.key,
                "comment": f.comment,
                "required": f.required,
                "suggestion": f.suggestion,
            }
            for f in template.fields
        ],
    }


def parse_settings(pairs: Sequence[str]) -> dict[str, str]:
    """Turn ``--set KEY=VALUE`` arguments into a mapping.

    An argument without ``=`` is an error rather than an ignored token: a
    silently dropped setting is an edit the operator believes they made.
    """
    values: dict[str, str] = {}
    for pair in pairs:
        if "=" not in pair:
            raise TemplateError(f"--set expects KEY=VALUE, got {pair!r}")
        key, _, value = pair.partition("=")
        key = key.strip().upper()
        if not key:
            raise TemplateError(f"--set expects KEY=VALUE, got {pair!r}")
        values[key] = value.strip()
    return values


def render_view(payload: dict[str, Any]) -> str:
    lines = [f"register: {payload['register']}"]
    lines.append(f"probed:   {payload['probed_at'] or 'not probed in this run'}")
    lines.append("")
    for item in payload["instances"]:
        lines.append(
            f"{item['name']}  [{item['kind']}]  {item['generic']['status']}"
            f"  (template {item['template'] or '?'})"
        )
        for panel in item["panels"]:
            if not panel["rows"] and not panel["note"]:
                continue
            lines.append(f"  {panel['title']}")
            for row in panel["rows"]:
                lines.append(f"    {row['label']:<20} {row['value']}")
            if panel["note"]:
                lines.append(f"    ({panel['note']})")
        lines.append("  Location questions")
        for answer in item["locations"]:
            shown = answer["value"] if answer["declared"] else answer["detail"]
            lines.append(f"    {answer['field']:<20} {shown}")
        gate = item["ontogate"]
        lines.append(
            f"  OntoGate  {gate['url'] if gate['available'] else gate['detail']}"
        )
        lines.append(f"  Uptime    {item['generic']['uptime']}")
        lines.append(f"  Apps      {item['generic']['apps']}")
        lines.append("")
    return "\n".join(lines)


def render_templates(payloads: list[dict[str, Any]]) -> str:
    lines = []
    for item in payloads:
        mark = "" if item["proven"] else "  [UNPROVEN]"
        lines.append(f"{item['name']}  v{item['version']}  -> {item['kind']}{mark}")
        lines.append(f"  {item['title']}: {item['summary']}")
        if not item["proven"]:
            lines.append(f"  UNPROVEN: {item['unproven_reason']}")
        for field in item["fields"]:
            flag = "required" if field["required"] else "optional"
            lines.append(f"    {field['key']:<18} {flag:<9} {field['comment']}")
        lines.append("")
    return "\n".join(lines)


def _emit(payload: Any, text: str, as_json: bool) -> None:
    print(json.dumps(payload, indent=2) if as_json else text)


def cmd_view(parsed: argparse.Namespace, runner: Runner) -> int:
    registry = load(parsed.register)
    readings = (
        [probe.read_instance(i, parsed.timeout, runner) for i in registry.instances]
        if parsed.probe
        else []
    )
    payload = view.build(registry, readings)
    _emit(payload, render_view(payload), parsed.json)
    return EXIT_OK


def cmd_templates(parsed: argparse.Namespace) -> int:
    payloads = [template_payload(t) for t in load_all()]
    _emit(payloads, render_templates(payloads), parsed.json)
    return EXIT_OK


def cmd_create(parsed: argparse.Namespace) -> int:
    path = parsed.register or default_register_path()
    values = parse_settings(parsed.set)
    template = crud.create(path, parsed.name, parsed.template, values)
    payload = {
        "created": parsed.name,
        "template": template.name,
        "version": template.version,
        "kind": template.kind,
        "register": str(path),
        "proven": template.proven,
    }
    warning = "" if template.proven else f"\nUNPROVEN: {template.unproven_reason}"
    _emit(
        payload,
        f"created {parsed.name} from template {template.name} "
        f"v{template.version} in {path}{warning}",
        parsed.json,
    )
    return EXIT_OK


def cmd_update(parsed: argparse.Namespace) -> int:
    path = parsed.register or default_register_path()
    changes = parse_settings(parsed.set)
    crud.update(path, parsed.name, changes)
    _emit(
        {"updated": parsed.name, "fields": sorted(changes), "register": str(path)},
        f"updated {parsed.name}: {', '.join(sorted(changes))}",
        parsed.json,
    )
    return EXIT_OK


def cmd_remove(parsed: argparse.Namespace) -> int:
    path = parsed.register or default_register_path()
    crud.remove(path, parsed.name)
    _emit(
        {"removed": parsed.name, "register": str(path)},
        f"removed {parsed.name} from {path}",
        parsed.json,
    )
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vpath-console",
        description="The management console: view instances, create them from "
        "versioned type templates.",
    )
    parser.add_argument("--register", type=Path, default=None)
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--timeout", type=int, default=90, help="seconds per instance")
    sub = parser.add_subparsers(dest="command", required=True)

    seen = sub.add_parser("view", help="every instance in the generic dual view")
    seen.add_argument(
        "--probe",
        action="store_true",
        help="measure now instead of showing the register only",
    )

    sub.add_parser("templates", help="the versioned type templates")

    create = sub.add_parser("create", help="create an instance from a template")
    create.add_argument("name")
    create.add_argument("--template", required=True)
    create.add_argument("--set", action="append", default=[], metavar="KEY=VALUE")

    update = sub.add_parser("update", help="set fields on an existing instance")
    update.add_argument("name")
    update.add_argument("--set", action="append", default=[], metavar="KEY=VALUE")

    remove = sub.add_parser("remove", help="drop an instance from the register")
    remove.add_argument("name")
    return parser


def main(argv: Sequence[str] | None = None, runner: Runner = transport.run) -> int:
    parsed = build_parser().parse_args(argv)
    try:
        if parsed.command == "view":
            return cmd_view(parsed, runner)
        if parsed.command == "templates":
            return cmd_templates(parsed)
        if parsed.command == "create":
            return cmd_create(parsed)
        if parsed.command == "update":
            return cmd_update(parsed)
        return cmd_remove(parsed)
    except TemplateError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_REFUSED
    except RegistryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_UNDETERMINED


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
