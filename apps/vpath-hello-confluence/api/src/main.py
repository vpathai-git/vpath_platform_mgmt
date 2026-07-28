"""Confluence Browser api — VpathService entrypoint.

Business logic only (P1): the SDK's VpathService wires auth, /health, /ready and
tracing. We just mount our Confluence router. PORT is injected by the platform
(supervisor for standalone, K8s for cluster) — read it, never hardcode (CLAUDE.md §5).

Run:  uvicorn main:app --app-dir src --port "$PORT"
"""

from __future__ import annotations

import os

from vpath_backend_sdk import VpathService

from confluence.routes import router

app = VpathService(app_id="vpath-hello-confluence", title="Confluence Browser")
# Mount under /api: the SDK's createProxyRoute always forwards web requests to
# `{backend}/api/<path>`, so domain routes live under /api (/health stays at root,
# auto-provided by VpathService). The web calls e.g. /api/confluence/spaces →
# proxy → /api/spaces here.
app.include_router(router, prefix="/api")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=os.environ.get("VPATH_HTTP_HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8010")),
    )
