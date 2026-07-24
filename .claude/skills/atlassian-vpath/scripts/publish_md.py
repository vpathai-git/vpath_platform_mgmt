#!/usr/bin/env python3
"""Publish ONE Markdown file as a Confluence page (v2 API, standard library).

Credentials from .env (working directory) or environment variables:
  API_Token_Confluence, Atlassian_Email, Confluence_Base_URL

Examples:
  python publish_md.py --file DOC.md --parent 27951105
  python publish_md.py --file DOC.md --into 28049409   # replace one page's body
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import confluence_api as api  # noqa: E402
import confluence_md as md  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Markdown -> Confluence page")
    ap.add_argument("--file", required=True, help="path to the .md file")
    ap.add_argument("--parent", help="parent page id (new child page)")
    ap.add_argument("--into", help="existing page id: replace its body (title kept)")
    ap.add_argument("--space-id", help="space id (else derived from --parent)")
    ap.add_argument("--host", help="Confluence host (else from .env)")
    ap.add_argument("--title", help="override title (else the first H1)")
    a = ap.parse_args()

    src = Path(a.file)
    if not src.is_file():
        print(f"ERROR: file not found: {src}", file=sys.stderr)
        return 2
    title, storage = md.md_file_to_page(src.read_text(encoding="utf-8"), src.stem)
    if a.title:
        title = a.title

    conf = api.confluence_from_env(host_override=a.host)
    print(
        f"Host:  {conf.host}\nFile:  {src.name}\n"
        f"Title: {title}  ({len(storage)} chars)"
    )

    if a.into:
        res = conf.update_page(
            a.into, storage, title=a.title, message=f"Content from {src.name}"
        )
        print(f"Page updated (body replaced): {conf.page_url(res)}")
        return 0

    space_id = a.space_id
    if a.parent and not space_id:
        space_id, ptitle = conf.space_of(a.parent)
        print(f"Parent: '{ptitle}' (spaceId {space_id})")
    if not space_id:
        print("ERROR: --parent or --space-id required.", file=sys.stderr)
        return 2

    action, res = conf.upsert(space_id, title, storage, parent_id=a.parent)
    print(f"Page {action}: {conf.page_url(res)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
