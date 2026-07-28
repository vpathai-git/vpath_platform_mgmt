#!/usr/bin/env python3
"""Phase-1 live data check (CLAUDE.md §6 Rule 3a).

Loads ENDPOINT/EMAIL/PAT from the nearest `.env` and prints REAL spaces + one
space's page tree from the live Confluence. Exits non-zero if the expected real
space ("DG Durst Group") is absent — no soft pass.

Run from the api dir:
  uv run --python 3.11 --with httpx verify_confluence.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))
from confluence import ConfluenceClient, ConfluenceError  # noqa: E402

EXPECT = "DG Durst Group"  # known real space on durst-group.atlassian.net


def load_env() -> dict[str, str]:
    for d in [Path.cwd(), *Path(__file__).resolve().parents]:
        env = d / ".env"
        if env.is_file():
            out: dict[str, str] = {}
            for line in env.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip().strip('"').strip("'")
            return out
    raise SystemExit("no .env found (need ENDPOINT, EMAIL, PAT)")


def main() -> int:
    env = load_env()
    missing = [k for k in ("ENDPOINT", "EMAIL", "PAT") if not env.get(k)]
    if missing:
        raise SystemExit(f"missing in .env: {', '.join(missing)}")

    client = ConfluenceClient.from_parts(env["ENDPOINT"], env["EMAIL"], env["PAT"])
    try:
        spaces = client.list_spaces()
    except ConfluenceError as e:
        raise SystemExit(f"FAIL: list_spaces -> {e}")

    print(f"\n=== {len(spaces)} spaces ===")
    for s in spaces:
        print(f"  {s.key:12} {s.name}  ({s.type})")

    names = {s.name for s in spaces}
    if EXPECT not in names:
        print(f"\nFAIL: expected real space {EXPECT!r} not found", file=sys.stderr)
        return 1

    target = next(s for s in spaces if s.name == EXPECT)
    print(f"\n=== root pages of {target.key} — {target.name} ===")
    roots = client.space_root_pages(target.id)
    for n in roots[:15]:
        print(f"  - {n.title}")
    if not roots:
        print("FAIL: expected at least one root page", file=sys.stderr)
        return 1

    first = roots[0]
    kids = client.page_children(first.id)
    print(f"\n=== children of {first.title!r} ({len(kids)}) ===")
    for k in kids[:10]:
        print(f"    - {k.title}")

    print(
        f"\nOK: real data verified — {len(spaces)} spaces, "
        f"{EXPECT!r} has {len(roots)} root pages, first page has {len(kids)} children"
    )
    client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
