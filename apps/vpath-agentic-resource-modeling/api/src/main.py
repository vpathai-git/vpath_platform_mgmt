"""Agentic Resource Modeling api — VpathService entrypoint.

Business logic only (P1): the SDK's VpathService wires auth, /health, /ready
and tracing. We just mount our cognition-modeling router. PORT is injected by
the platform (supervisor for standalone, K8s for cluster) — read it, never
hardcode (CLAUDE.md §5).

Run:  uvicorn main:app --app-dir src --port "$PORT"
"""

from __future__ import annotations

import os

from vpath_backend_sdk import VpathService

from cognition.routes import router
from cognition.runtime import runtime_router

app = VpathService(
    app_id="vpath-agentic-resource-modeling",
    title="Agentic Resource Modeling",
)
# Mount under /api: the SDK's createProxyRoute forwards web requests to
# `{backend}/api/<path>`, so domain routes live under /api (/health stays at
# root, auto-provided by VpathService). The web calls /api/modeling/validate →
# proxy → /api/validate here.
#   * router          — the DECLARATION layer (compose/validate/project + the
#                       read-only bound-resource status).
#   * runtime_router  — the RUNTIME layer (/api/runtime/offerings + /invoke):
#                       the canonical get_agent_factory() path.
app.include_router(router, prefix="/api")
app.include_router(runtime_router, prefix="/api")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=os.environ.get("VPATH_HTTP_HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8021")),
    )
