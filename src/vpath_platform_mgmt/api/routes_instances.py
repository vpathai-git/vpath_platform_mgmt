"""Fleet register routes: list and detail over server + standalone instances."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request

from vpath_platform_mgmt.api.auth import Identity
from vpath_platform_mgmt.instances import history, probe, transport
from vpath_platform_mgmt.instances.registry import (
    Instance,
    RegistryError,
    default_register_path,
    load,
)

IdentityFn = Callable[[Request], Identity]

MASK_FIELD_KEYS = frozenset({"SSH_KEY", "SSH_KEY_SOURCE"})
MASK = "<masked>"


def _mask_fields(fields: dict[str, str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in fields.items():
        if key in MASK_FIELD_KEYS or key.endswith("_KEY"):
            out[key] = MASK if value else value
        else:
            out[key] = value
    return out


def _probe_one(instance: Instance, register: Path, timeout: int) -> probe.Reading:
    reading = probe.read_instance(instance, timeout, transport.run)
    history.append_reading(history.history_path(register), reading)
    return reading


def _list_rows(path: Path, timeout: int) -> list[dict[str, str]]:
    try:
        registry = load(path)
    except RegistryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    rows: list[dict[str, str]] = []
    for instance in registry.instances:
        reading = _probe_one(instance, path, timeout)
        rows.append(
            {
                "name": instance.name,
                "kind": instance.kind,
                "lifecycle": instance.lifecycle,
                "coarse": reading.verdict,
            }
        )
    return rows


def _detail_payload(path: Path, name: str, timeout: int) -> dict[str, object]:
    try:
        registry = load(path)
        instance = registry.get(name)
    except RegistryError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    reading = _probe_one(instance, path, timeout)
    events = history.read_tail(history.history_path(path), name=name, limit=20)
    ontogate = instance.fields.get("ONTOGATE_URL", "").strip()
    return {
        "name": instance.name,
        "kind": instance.kind,
        "lifecycle": instance.lifecycle,
        "ontogate_url": ontogate or None,
        "fields": _mask_fields(dict(instance.fields)),
        "probe": {
            "verdict": reading.verdict,
            "facts": [
                {"label": f.label, "value": f.value, "source": f.source}
                for f in reading.facts
            ],
            "gaps": [
                {"label": g.label, "value": g.value, "source": g.source}
                for g in reading.gaps
            ],
        },
        "history": events,
    }


def register(
    app: FastAPI,
    identity: IdentityFn,
    instances_register: Path | None = None,
    *,
    probe_timeout: int = 12,
) -> None:
    """Attach read-only fleet routes. Missing register yields an empty list."""

    def _register_path() -> Path:
        if instances_register is not None:
            return instances_register
        return default_register_path()

    @app.get("/api/instances")
    def list_instances(request: Request) -> list[dict[str, str]]:
        identity(request)
        path = _register_path()
        if not path.is_file():
            return []
        return _list_rows(path, probe_timeout)

    @app.get("/api/instances/{name}")
    def show_instance(request: Request, name: str) -> dict[str, object]:
        identity(request)
        path = _register_path()
        if not path.is_file():
            raise HTTPException(status_code=404, detail=f"no register at {path}")
        return _detail_payload(path, name, probe_timeout)
