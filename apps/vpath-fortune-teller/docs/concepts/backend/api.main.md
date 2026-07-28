---
entity: api.main
kind: backend
stories: []
tests: []
status: validated
validated: 2026-07-12
---

# api.main — the VpathService entrypoint

Business logic only (P1): constructs the SDK's `VpathService` (which wires
auth, `/health`, `/ready`, tracing) and mounts the domain router from
[[api.routes]] under `/api` — the SDK's proxy forwards web requests to
`{backend}/api/<path>`. `PORT` is injected by the platform at runtime, read
from the environment, never hardcoded (CLAUDE.md §5).
