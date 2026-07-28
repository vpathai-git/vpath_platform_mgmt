---
entity: src.app.api.proxy.[...path].route
kind: frontend
stories: [K01]
tests: [tests/standalone-workflow-demo.proof.ts]
status: validated
validated: 2026-07-22
---

# Platform API proxy

Workflow hooks use this authenticated same-origin route. The SDK streams the
request to the runtime-injected platform API target and fails if that target is
missing; the app owns no workflow backend.
