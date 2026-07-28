"""Axis 1 -- one generic view over every platform type, plus its own panels.

What this module is
-------------------
The console must show server, standalone and remote instances *through one
shape*: status, apps, state, operations.  Where a type has something no other
type has, that goes into a type-specific panel instead of being smuggled into
the generic shape.  This module builds that structure and nothing else -- it
renders no pixels, so the Electron shell and any test see the same data.

The honesty rules it enforces
-----------------------------
1. A fact that was never measured is reported as *not probed*, never as a
   value and never as "down".  Every view carries ``probed_at``: ``None``
   means nobody looked.
2. A register field that is blank is *not declared* -- distinct from a field
   declared as empty, which the register does not allow.
3. The OntoGate link is only a link when a viewer address is declared.  The
   viewer (``ontogate-view`` in ``vpath_ontogate``) binds an auto-picked
   loopback port, so no address can be derived; an undeclared one is shown as
   missing, never as a dead link.
4. Apps (axis 3) are not managed yet.  The apps section says so, and names the
   issue that changes it, rather than rendering an empty list that reads like
   "no apps".
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Sequence

from ..instances import probe
from ..instances.instance import LOCATION_FIELDS, Instance
from ..instances.probe import Reading
from ..instances.registry import Registry
from ..instances.templates import TemplateError, template_for_kind

NOT_PROBED = "NOT PROBED"
NOT_DECLARED = "not declared"

LOCATION_QUESTIONS = {
    "LOCATION": "Where does this instance live (host + filesystem)?",
    "BUILD_PROCESS": "Where does its build process live?",
    "SOURCE_REPOS": "Which source repositories does the build pull apps from?",
    "IMAGE_REGISTRY": "Where do its container images live?",
}

# What the console can actually drive today, per kind -- read off the code that
# would do it (selector + transport), not off an intention.
OPERATIONS = {
    "server-nuc": ("probe", "exec", "gradle", "deliver"),
    "server-cloud-vm": ("probe", "exec", "gradle", "deliver"),
    "standalone": ("probe",),
    "remote": (),
}

# Uptime was asked for explicitly and is decided (main figure: platform
# services healthy-since; detail: all four clocks).  Nothing measures it yet,
# so the console says that.  Relabelling "last install" as uptime would be a
# plausible number and a wrong one.
UPTIME_PENDING = (
    "not measured -- decided as 'platform services healthy since', with all "
    "four clocks (box, k3s, platform, apps) in the detail; the probe reads "
    "last install and deployment readiness but no clock yet; see "
    "analysis/instance-status/status-probe.issue.md"
)

APPS_PENDING = (
    "not managed yet -- axis 3 starts with one existing app (Explorer) made "
    "deployable in isolation; see analysis/mgmt-console/"
    "explorer-quick-extraction.issue.md"
)


def _row(label: str, value: str, source: str) -> dict[str, str]:
    return {"label": label, "value": value, "source": source}


def _declared(instance: Instance, key: str) -> dict[str, Any]:
    value = instance.fields.get(key, "").strip()
    return {
        "field": key,
        "value": value,
        "declared": bool(value),
        "detail": "" if value else f"{NOT_DECLARED} in {instance.source}",
    }


def locations(instance: Instance) -> list[dict[str, Any]]:
    """The four location questions, answered or honestly blank."""
    answers = []
    for key in LOCATION_FIELDS:
        answer = _declared(instance, key)
        answer["question"] = LOCATION_QUESTIONS[key]
        answers.append(answer)
    return answers


def ontogate(instance: Instance) -> dict[str, Any]:
    """The per-instance OntoGate link, or an honest absence (decision M3)."""
    url = instance.ontogate_view.strip()
    if url:
        return {"url": url, "available": True, "detail": ""}
    return {
        "url": "",
        "available": False,
        "detail": (
            "no OntoGate view declared for this instance. The viewer exists "
            "(vpath_ontogate: ontogate-view) but binds an auto-picked port, so "
            "its address cannot be derived -- declare ONTOGATE_VIEW once it runs"
        ),
    }


def _coordinates(instance: Instance) -> dict[str, Any]:
    """The register coordinates only this type has."""
    if instance.is_server:
        rows = [
            _row("ssh", instance.ssh_target, instance.source),
            _row("ssh key", instance.ssh_key or "<ssh default>", instance.source),
            _row("env profile", instance.env_profile, instance.source),
            _row("checkout", instance.checkout, instance.source),
        ]
        title = "Server box"
    elif instance.is_standalone:
        rows = [
            _row("app root", instance.app_root, instance.source),
            _row("home", instance.home, instance.source),
        ]
        title = "Standalone shell"
    else:
        rows = [
            _row("cluster", instance.cluster_host, instance.source),
            _row("jump host", instance.jump_host or NOT_DECLARED, instance.source),
            _row(
                "console permitted",
                instance.fields.get("CONSOLE_PERMITTED", "") or NOT_DECLARED,
                instance.source,
            ),
        ]
        title = "Remote customer cluster (unproven)"
    # Every panel carries the same three keys, so a renderer can loop over them
    # without knowing which panel it is holding.
    return {"title": title, "rows": rows, "note": ""}


def _measured(reading: Reading | None) -> dict[str, Any]:
    if reading is None:
        return {
            "title": "Measured",
            "rows": [],
            "note": "nobody has looked at this instance in this session",
        }
    return {
        "title": "Measured",
        "rows": [_row(f.label, f.value, f.source) for f in reading.facts],
        "note": "" if reading.facts else "the probe established nothing",
    }


def _gaps(reading: Reading | None) -> dict[str, Any]:
    rows = [_row(g.label, g.value, g.source) for g in reading.gaps] if reading else []
    return {"title": "Not establishable", "rows": rows, "note": ""}


def _template_name(instance: Instance) -> str:
    try:
        return template_for_kind(instance.kind).name
    except TemplateError:
        return ""


def instance_view(instance: Instance, reading: Reading | None) -> dict[str, Any]:
    """One instance in the shape every type shares, plus its own panels."""
    verdict = reading.verdict if reading is not None else NOT_PROBED
    return {
        "name": instance.name,
        "kind": instance.kind,
        "template": _template_name(instance),
        "lifecycle": instance.lifecycle,
        "notes": instance.notes,
        "source": instance.source,
        "generic": {
            "status": verdict,
            "healthy": verdict == probe.HEALTHY,
            "apps": APPS_PENDING,
            "uptime": UPTIME_PENDING,
            "state": instance.lifecycle,
            "operations": list(OPERATIONS.get(instance.kind, ())),
        },
        "panels": [_coordinates(instance), _measured(reading), _gaps(reading)],
        "locations": locations(instance),
        "ontogate": ontogate(instance),
    }


def build(
    registry: Registry,
    readings: Sequence[Reading] = (),
    *,
    probed_at: str | None = None,
) -> dict[str, Any]:
    """The whole console payload: every declared instance, one shape.

    ``probed_at`` is stamped only when readings were actually taken, so a
    cached view can never present itself as a current one.
    """
    by_name = {r.name: r for r in readings}
    if readings and probed_at is None:
        probed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "register": str(registry.path),
        "probed_at": probed_at if readings else None,
        "instances": [
            instance_view(i, by_name.get(i.name)) for i in registry.instances
        ],
    }
