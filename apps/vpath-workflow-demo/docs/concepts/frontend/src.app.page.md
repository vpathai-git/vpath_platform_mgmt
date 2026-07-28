---
entity: src.app.page
kind: frontend
stories: [K01]
tests: [tests/standalone-workflow-demo.proof.ts]
status: validated
validated: 2026-07-22
---

# Runtime boundary adapter

The dynamic server page requires an explicit platform or standalone runtime and
passes one capability fact to the client. Standalone never mounts run controls;
platform mode delegates execution to the workflow SDK.
