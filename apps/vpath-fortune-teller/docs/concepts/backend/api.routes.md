---
entity: api.routes
kind: backend
stories: [K01]
tests: [api/tests/test_api.py]
status: validated
validated: 2026-07-12
---

# api.routes — the domain API surface

The only API this app writes (CLAUDE.md §1): `POST /draw` takes an optional
question (over-long or wrong-typed input fails LOUD with a 422, never a silent
default) and returns the deterministic card drawn by [[api.deck]]. Every route
depends on the SDK's `require_auth` — identity is the platform's job, never
hand-verified here. Proven end-to-end by story K01's twin test
(`api/tests/test_api.py`).
