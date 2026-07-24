#!/usr/bin/env python3
"""Publish a DIRECTORY of Markdown files as a Confluence page tree (v2 API,
standard library): one child page per *.md under --parent, idempotent.

Extras:
  - internal .md cross-links become real Confluence page links (by title)
  - long pages get a table of contents (ToC)
  - --into NAME.md=PAGEID : migrate that file into an EXISTING page (title kept)

Example:
  python publish_set.py --dir ./docs --parent 27951105 \\
      --into 01_INTRO.md=28049409
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import confluence_api as api  # noqa: E402
import confluence_md as md  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Markdown directory -> Confluence page tree"
    )
    ap.add_argument("--dir", required=True, help="directory of *.md files")
    ap.add_argument("--parent", required=True, help="parent page id")
    ap.add_argument("--host", help="Confluence host (else from .env)")
    ap.add_argument(
        "--into",
        action="append",
        default=[],
        help="NAME.md=PAGEID : migrate file into an existing page (repeatable)",
    )
    a = ap.parse_args()

    src = Path(a.dir)
    files = sorted(src.glob("*.md"))
    if not files:
        print(f"ERROR: no .md files in {src}", file=sys.stderr)
        return 2
    into = dict(x.split("=", 1) for x in a.into)  # {filename: pageid}

    conf = api.confluence_from_env(host_override=a.host)
    space_id, ptitle = conf.space_of(a.parent)
    print(f"Parent: '{ptitle}' (spaceId {space_id})\n")

    # Title per file (for the page title AND the link map). With --into: the
    # target page's title.
    titles: dict[str, str] = {}
    bodies: dict[str, str] = {}
    for f in files:
        h1, storage = md.md_file_to_page(f.read_text(encoding="utf-8"), f.stem)
        bodies[f.name] = storage
        if f.name in into:
            s, ex = conf.get_page(into[f.name])
            titles[f.name] = ex["title"] if s == 200 and isinstance(ex, dict) else h1
        else:
            titles[f.name] = h1
    link_map = {name: titles[name] for name in titles}

    for f in files:
        title = titles[f.name]
        storage = md.with_toc(md.rewrite_internal_links(bodies[f.name], link_map))
        if f.name in into:
            res = conf.update_page(
                into[f.name], storage, message=f"Content from {f.name}"
            )
            print(f"  [migrated   ] {f.name:40} -> {conf.page_url(res)}")
        else:
            action, res = conf.upsert(space_id, title, storage, parent_id=a.parent)
            print(f"  [{action:11}] {f.name:40} -> {conf.page_url(res)}")
    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
