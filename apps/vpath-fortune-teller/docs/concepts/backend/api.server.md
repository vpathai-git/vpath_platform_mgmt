---
entity: api.server
kind: backend
stories: []
tests: []
status: validated
validated: 2026-07-12
---

# api.server — the uvicorn launcher shim

A thin runtime launcher: puts `api/src` on the path and serves the
[[api.main]] app with uvicorn, honoring the platform-injected `PORT` /
`VPATH_HTTP_HOST` environment (CLAUDE.md §5 — all config at runtime). No
domain logic lives here; it exists so both adapters (standalone supervisor,
cluster container) start the backend the same way.
