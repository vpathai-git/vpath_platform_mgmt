"""Confluence Cloud REST v2 client — read-only spaces + lazy page tree.

Auth is Basic `email:token` (Atlassian Cloud API token). The base URL is the
Confluence site root (e.g. https://<org>.atlassian.net); the v2 API lives under
`/wiki/api/v2`. Every non-2xx raises ConfluenceError — no partial results, no
silent empty (CLAUDE.md §7). The token is never logged.

The page structure is fetched LAZILY: `space_root_pages()` returns the top-level
pages; `page_children()` returns one page's direct children. A browser UI expands
on demand — we never pull an entire (potentially thousands-of-pages) space.
"""

from __future__ import annotations

import base64
from urllib.parse import urlsplit

import httpx

from .errors import ConfluenceError
from .models import PageNode, Space

_TIMEOUT = httpx.Timeout(15.0)
_PAGE_LIMIT = 100  # per-request page size
_MAX_PAGES = 200  # hard cap on pagination requests → raise, never loop forever


def _origin_and_root(base_url: str) -> tuple[str, str]:
    parts = urlsplit(base_url.rstrip("/"))
    if not parts.scheme or not parts.netloc:
        raise ConfluenceError(0, "confluence base_url must be an absolute https URL")
    origin = f"{parts.scheme}://{parts.netloc}"
    path = parts.path.rstrip("/")
    root = (
        f"{origin}{path}/api/v2" if path.endswith("/wiki") else f"{origin}/wiki/api/v2"
    )
    return origin, root


class ConfluenceClient:
    def __init__(
        self, base_url: str, basic: str, *, http: httpx.Client | None = None
    ) -> None:
        """`basic` is the raw Basic-auth pair "email:token" (Atlassian Cloud)."""
        if not (base_url and basic and ":" in basic):
            raise ConfluenceError(
                0, "confluence client requires base_url and an email:token pair"
            )
        self._origin, self._root = _origin_and_root(base_url)
        cred = base64.b64encode(basic.encode()).decode()
        self._headers = {"Authorization": f"Basic {cred}", "Accept": "application/json"}
        self._http = http or httpx.Client(timeout=_TIMEOUT)

    @classmethod
    def from_parts(
        cls, base_url: str, email: str, token: str, **kw
    ) -> "ConfluenceClient":
        """Build from separate email + token (e.g. local .env: EMAIL, PAT)."""
        if not (email and token):
            raise ConfluenceError(0, "email and token are both required")
        return cls(base_url, f"{email}:{token}", **kw)

    @classmethod
    def from_credential_header(
        cls, base_url: str, token_header: str, **kw
    ) -> "ConfluenceClient":
        """Build from the resource-gate header value (already an "email:token" pair)."""
        return cls(base_url, token_header, **kw)

    # -- low level ---------------------------------------------------------
    def _get_page(self, url: str, params: dict) -> tuple[list[dict], str | None]:
        # `params or None`: the `next` link already carries cursor+limit in its query;
        # passing an empty dict would make httpx drop that query string
        # (losing the cursor).
        resp = self._http.get(url, headers=self._headers, params=params or None)
        if resp.status_code != 200:
            raise ConfluenceError(resp.status_code, _detail(resp))
        data = resp.json()
        nxt = (data.get("_links") or {}).get("next")
        return data.get("results", []), (f"{self._origin}{nxt}" if nxt else None)

    def _get_all(self, path: str, params: dict | None = None) -> list[dict]:
        """GET a v2 collection, following cursor pagination (bounded by _MAX_PAGES)."""
        results: list[dict] = []
        url: str | None = f"{self._root}{path}"
        query = {"limit": _PAGE_LIMIT, **(params or {})}
        seen_ids: set[str] = set()
        for _ in range(_MAX_PAGES):
            rows, url = self._get_page(url, query)
            for r in rows:  # de-dup: Confluence cursors can overlap
                rid = str(r.get("id"))
                if rid not in seen_ids:
                    seen_ids.add(rid)
                    results.append(r)
            query = {}  # the `next` link carries cursor + limit
            if not url:
                return results
        raise ConfluenceError(0, f"pagination exceeded {_MAX_PAGES} pages for {path}")

    # -- public ------------------------------------------------------------
    def list_spaces(self) -> list[Space]:
        rows = self._get_all("/spaces")
        spaces = [
            Space(str(s["id"]), s.get("key", ""), s.get("name", ""), s.get("type", ""))
            for s in rows
        ]
        spaces.sort(key=lambda s: s.name.lower())
        return spaces

    def space_root_pages(self, space_id: str) -> list[PageNode]:
        """Top-level pages of a space (lazy: children fetched on demand)."""
        rows = self._get_all(f"/spaces/{space_id}/pages", {"depth": "root"})
        return _to_nodes(rows)

    def page_children(self, page_id: str) -> list[PageNode]:
        """Direct child pages of one page."""
        rows = self._get_all(f"/pages/{page_id}/children")
        return _to_nodes(rows)

    def close(self) -> None:
        self._http.close()


def _to_nodes(rows: list[dict]) -> list[PageNode]:
    nodes = [PageNode(str(r["id"]), r.get("title") or "(untitled)") for r in rows]
    nodes.sort(key=lambda n: n.title.lower())
    return nodes


def _detail(resp: httpx.Response) -> str:
    try:
        body = resp.json()
        errs = body.get("errors") if isinstance(body, dict) else None
        if errs:
            return str(errs[0].get("title") or errs[0].get("detail") or errs[0])
        return str(body.get("message") or body)[:200]
    except Exception:
        return resp.text[:200] or resp.reason_phrase
