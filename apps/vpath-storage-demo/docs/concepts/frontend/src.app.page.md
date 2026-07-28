---
entity: src.app.page
kind: frontend
stories: [K01]
tests: [tests/standalone-storage-demo.proof.ts]
status: validated
validated: 2026-07-22
---

# Storage page

The dynamic page mounts the client storage explorer. It holds no domain logic
of its own; the render / empty-state proof (K01) drives it through the SDK
storage surface.
