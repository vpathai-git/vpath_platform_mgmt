"""Append-only probe history next to the instance register.

Each line is one JSON object: ``ts``, ``name``, ``kind``, ``coarse``, ``fields``.
The file is operator-local (gitignored); it never invents a healthy verdict.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

HISTORY_ENV_VAR = "VPATH_INSTANCES_HISTORY"
HISTORY_SUFFIX = ".history.jsonl"


class _ReadingLike(Protocol):
    name: str
    kind: str
    verdict: str
    facts: list[Any]
    gaps: list[Any]


def history_path(register: Path) -> Path:
    """Where history is stored for a register file."""
    override = os.environ.get(HISTORY_ENV_VAR)
    if override:
        return Path(override).expanduser()
    return Path(f"{register}{HISTORY_SUFFIX}")


def append_reading(path: Path, reading: _ReadingLike) -> None:
    """Append one probe reading as a JSONL line."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = {fact.label: fact.value for fact in reading.facts}
    for gap in reading.gaps:
        fields[f"!{gap.label}"] = gap.value
    event = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "name": reading.name,
        "kind": reading.kind,
        "coarse": reading.verdict,
        "fields": fields,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=True) + "\n")


def read_tail(
    path: Path,
    *,
    name: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Return the last ``limit`` events, optionally filtered by instance name."""
    if limit < 1:
        return []
    if not path.is_file():
        return []
    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        if name is not None and event.get("name") != name:
            continue
        events.append(event)
    return events[-limit:]
