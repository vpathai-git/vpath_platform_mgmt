# Confluence publishing (detail)

Confluence runs on **`Confluence_Base_URL`** (its own host, not the Jira host). v2 REST API.
Everything is **bundled in the skill** (`scripts/`), pure Python standard library — no pip, no repo deps.

## Bundled scripts (in the skill folder)
| Purpose | Command |
|---|---|
| One MD file → new child page | `python scripts/publish_md.py --file X.md --parent <page-id>` |
| One MD file → replace existing page | `python scripts/publish_md.py --file X.md --into <page-id>` |
| Directory → page tree (cross-links + ToC) | `python scripts/publish_set.py --dir ./docs --parent <page-id>` |
| Migrate one set file into an existing page | `python scripts/publish_set.py --dir ./docs --parent <id> --into 01_X.md=<page-id>` |

Logic/helpers: `scripts/confluence_md.py` (`md_file_to_page`, `convert_markdown`,
`rewrite_internal_links`, `with_toc`) and `scripts/confluence_api.py` (`load_env`, class `Confluence`,
`confluence_from_env`). Idempotent by title (Confluence enforces unique titles per space). The first H1 becomes the page title.

## Rendering traps (cause display errors)
1. **Heading inside a blockquote** (`> ### …`): Confluence does **not** render `<h…>` inside `<blockquote>`
   (empty box). → the converter turns it into a bold paragraph (`heading_as_strong`).
2. **Code/ASCII diagrams**: as a Confluence **code macro** (`<![CDATA[…]]>`), else
   whitespace/monospace is lost. Fenced ```-blocks are handled this way.
3. **Internal `.md` cross-links**: rewrite to **page links by title**
   (`<ac:link><ri:page ri:content-title="…"/>…</ac:link>`), not a dead `<a href="x.md">`.
4. **Special characters/umlauts/emojis** are preserved (UTF-8); Confluence encodes on save
   `—`→`&mdash;`, `ß`→`&szlig;` — when verifying compare with `html.unescape`.
5. **ToC**: long pages get a table of contents prepended automatically (`with_toc`).

## Verification after publishing
- List the parent page's children (`GET /wiki/api/v2/pages/<id>/children`).
- Body length > 0, version incremented.
- Check `ri:content-title` link targets against real page titles (with `html.unescape`).

## Programmatic (instead of CLI)
```python
import sys; sys.path.insert(0, "<skill>/scripts")
import confluence_api as api, confluence_md as md
conf = api.confluence_from_env()
title, storage = md.md_file_to_page(open("DOC.md", encoding="utf-8").read(), "DOC")
space_id, _ = conf.space_of("27951105")
action, page = conf.upsert(space_id, title, storage, parent_id="27951105")
print(action, conf.page_url(page))
```
