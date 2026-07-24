"""Confluence Cloud v2 REST client + credential loading. Standard library only.

Companion to confluence_md.py (the Markdown converter). Provides:
  - load_env(): credentials from .env (cwd or skill folder) or environment vars
  - Confluence: a small v2 REST client (get / find / upsert / update page)
  - confluence_from_env(): build a client from the resolved credentials

No host is hardcoded: Confluence_Base_URL must be supplied via config (.env,
environment, or --host); a missing host raises rather than guessing a tenant.
"""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# Recognised .env / environment keys.
_KEYS = ("API_Token_Confluence", "Atlassian_Email", "Confluence_Base_URL")


def _find_dotenv() -> Path | None:
    candidates = []
    if os.environ.get("VPATH_DOTENV"):
        candidates.append(Path(os.environ["VPATH_DOTENV"]))
    candidates.append(Path.cwd() / ".env")  # working directory
    candidates.append(Path(__file__).resolve().parent / ".env")  # skill folder
    for c in candidates:
        if c.is_file():
            return c
    return None


def load_env() -> dict[str, str]:
    """Read credentials. Order: .env (cwd/skill) as a base, environment
    variables take precedence. Tolerates 'KEY = VALUE'."""
    data: dict[str, str] = {}
    path = _find_dotenv()
    if path:
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            data[k.strip()] = v.strip().strip('"').strip("'")
    for k in _KEYS:  # environment overrides
        if os.environ.get(k):
            data[k] = os.environ[k]
    return data


class Confluence:
    def __init__(self, email: str, token: str, host: str):
        if not email or not token:
            raise ValueError(
                "Atlassian_Email and API_Token_Confluence are required "
                "(.env or environment)."
            )
        if not host:
            raise ValueError(
                "Confluence_Base_URL is required (.env, environment, or --host)."
            )
        self.host = host.rstrip("/")
        self._auth = base64.b64encode(f"{email}:{token}".encode()).decode()

    def _req(self, method: str, path: str, body=None):
        data = json.dumps(body).encode() if body is not None else None
        r = urllib.request.Request(
            self.host + path,
            data=data,
            method=method,
            headers={
                "Authorization": f"Basic {self._auth}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(r) as resp:
                b = resp.read().decode()
                return resp.status, (json.loads(b) if b.strip() else None)
        except urllib.error.HTTPError as e:
            b = e.read().decode()
            try:
                b = json.loads(b)
            except json.JSONDecodeError:
                pass
            return e.code, b

    def get_page(self, page_id, body_format: str | None = None):
        p = f"/wiki/api/v2/pages/{page_id}"
        if body_format:
            p += f"?body-format={body_format}"
        return self._req("GET", p)

    def space_of(self, parent_id) -> tuple[str, str]:
        s, p = self.get_page(parent_id)
        if s != 200 or not isinstance(p, dict):
            raise RuntimeError(
                f"Parent page {parent_id} not readable: {s} {str(p)[:200]}"
            )
        return str(p["spaceId"]), p["title"]

    def find_page(self, space_id, title: str):
        q = urllib.parse.quote(title)
        s, found = self._req(
            "GET", f"/wiki/api/v2/pages?space-id={space_id}&title={q}&limit=50"
        )
        if s == 200 and isinstance(found, dict):
            for pg in found.get("results", []):
                if pg.get("title") == title:
                    return pg
        return None

    def upsert(self, space_id, title: str, storage: str, parent_id=None):
        """Create or (by title) update a page. -> (action, page)."""
        body = {
            "spaceId": str(space_id),
            "status": "current",
            "title": title,
            "body": {"representation": "storage", "value": storage},
        }
        if parent_id:
            body["parentId"] = str(parent_id)
        existing = self.find_page(space_id, title)
        if existing:
            s, cur = self.get_page(existing["id"])
            body["id"] = existing["id"]
            body["version"] = {
                "number": cur["version"]["number"] + 1,
                "message": "Update via skill",
            }
            s, res = self._req("PUT", f"/wiki/api/v2/pages/{existing['id']}", body)
            action = "updated"
        else:
            s, res = self._req("POST", "/wiki/api/v2/pages", body)
            action = "created"
        if s in (200, 201) and isinstance(res, dict):
            return action, res
        raise RuntimeError(f"Confluence error {s}: {str(res)[:400]}")

    def update_page(
        self,
        page_id,
        storage: str,
        title: str | None = None,
        message: str = "Update via skill",
    ):
        """Replace the body of a SPECIFIC existing page (title kept unless given)."""
        s, cur = self.get_page(page_id)
        if s != 200 or not isinstance(cur, dict):
            raise RuntimeError(f"Page {page_id} not readable: {s}")
        body = {
            "id": str(page_id),
            "status": "current",
            "title": title or cur["title"],
            "body": {"representation": "storage", "value": storage},
            "version": {
                "number": cur["version"]["number"] + 1,
                "message": message,
            },
        }
        s, res = self._req("PUT", f"/wiki/api/v2/pages/{page_id}", body)
        if s == 200 and isinstance(res, dict):
            return res
        raise RuntimeError(f"Confluence error {s}: {str(res)[:400]}")

    def page_url(self, page: dict) -> str:
        return f"{self.host}/wiki/spaces/{page.get('spaceId')}/pages/{page['id']}"


def confluence_from_env(
    env: dict | None = None, host_override: str | None = None
) -> Confluence:
    env = env or load_env()
    host = host_override or env.get("Confluence_Base_URL") or ""
    return Confluence(
        env.get("Atlassian_Email", ""),
        env.get("API_Token_Confluence", ""),
        host,
    )
