"""Supervisor status file under a standalone HOME (Phase 3 contract)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

STATUS_REL = Path("runtime") / "vpath-standalone.status.json"
REQUIRED_ANY_OF = (("port", "ports"),)
REQUIRED = ("pid", "started_at")
VERSION_KEYS = ("version", "build_id")


class StatusFileError(Exception):
    """Status file missing or malformed."""


def status_path(home: str | Path) -> Path:
    return Path(home) / STATUS_REL


def parse_status(path: Path) -> dict[str, Any]:
    """Parse and validate the supervisor status file. Fail hard on bad shape."""
    if not path.is_file():
        raise StatusFileError(f"missing status file: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise StatusFileError(f"{path}: not valid JSON") from exc
    if not isinstance(data, dict):
        raise StatusFileError(f"{path}: root must be a JSON object")
    for key in REQUIRED:
        if key not in data or data[key] in ("", None):
            raise StatusFileError(f"{path}: missing required key {key!r}")
    if "port" not in data and "ports" not in data:
        raise StatusFileError(f"{path}: need port or ports")
    if not any(data.get(k) not in ("", None) for k in VERSION_KEYS):
        raise StatusFileError(f"{path}: need version or build_id")
    return data
