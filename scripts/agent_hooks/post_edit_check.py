#!/usr/bin/env python3
"""Shared post-edit quality hook for Claude Code and Codex."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def run(cmd: list[str]) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(cmd, capture_output=True, text=True)


def tool(name: str, root: Path) -> str | None:
    bindir = "Scripts" if sys.platform == "win32" else "bin"
    exe = name + (".exe" if sys.platform == "win32" else "")
    candidate = root / "venv" / bindir / exe
    if candidate.is_file():
        return str(candidate)
    return shutil.which(name)


def walk_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        found: list[str] = []
        for nested in value.values():
            found.extend(walk_strings(nested))
        return found
    if isinstance(value, list):
        found = []
        for nested in value:
            found.extend(walk_strings(nested))
        return found
    return []


def edited_path(payload: dict[str, Any], root: Path) -> Path | None:
    preferred = payload.get("tool_input", {}).get("file_path")
    candidates = [preferred] if isinstance(preferred, str) else []
    candidates.extend(walk_strings(payload))
    for candidate in candidates:
        path = Path(candidate)
        if not path.is_absolute():
            path = root / path
        if path.is_file():
            return path
    return None


def checks_for(path: Path, root: Path) -> list["subprocess.CompletedProcess[str]"]:
    if path.suffix == ".py":
        black = tool("black", root)
        flake8 = tool("flake8", root)
        if not (black and flake8):
            return [
                subprocess.CompletedProcess(
                    ["post_edit_check"],
                    2,
                    "",
                    "post_edit_check: black/flake8 not installed - edit NOT "
                    "checked. Run: make install-dev\n",
                )
            ]
        rel = str(path)
        return [
            run([black, "--check", "--quiet", rel]),
            run([flake8, rel, "--max-line-length=88", "--extend-ignore=E203"]),
        ]
    if path.suffix == ".java" and (root / "gradlew").is_file():
        wrapper = "gradlew.bat" if sys.platform == "win32" else "./gradlew"
        return [run([str(root / wrapper), "spotlessCheck", "-q"])]
    return []


def main() -> int:
    root = Path.cwd()
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    path = edited_path(payload, root)
    if path is None:
        return 0
    failed = [check for check in checks_for(path, root) if check.returncode != 0]
    if not failed:
        return 0
    for check in failed:
        sys.stderr.write(check.stdout + check.stderr)
    sys.stderr.write(f"\npost_edit_check: {path} fails the quality gate - fix now.\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
