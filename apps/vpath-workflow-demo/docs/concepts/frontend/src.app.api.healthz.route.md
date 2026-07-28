---
entity: src.app.api.healthz.route
kind: frontend
stories: []
tests: [tests/standalone-workflow-demo.proof.ts]
status: validated
validated: 2026-07-22
---

# Web health route

The web listener exposes the SDK-owned health response at the manifest's
readiness and liveness path. The app contains no custom probe semantics.
