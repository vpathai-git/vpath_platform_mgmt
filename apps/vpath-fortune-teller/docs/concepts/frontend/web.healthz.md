---
entity: web.healthz
kind: frontend
stories: []
tests: []
status: validated
validated: 2026-07-12
---

# web.healthz — the SDK health route

`createHealthRoute()` verbatim — the manifest's readiness/liveness probes hit
this path; the SDK owns the semantics (never a hand-written probe handler,
hull contract C-health-via-sdk).
