---
entity: web.providers
kind: frontend
stories: []
tests: []
status: validated
validated: 2026-07-12
---

# web.providers — the SDK app wiring

The canonical `createVpathApp({ appId, basePath })` call (GL1): identity and
activity derive from the manifest — no inline `activity:` override. Exports
the query/mutation hooks ([[web.page]] consumes them) so every data access
rides the SDK's session-aware fetch, never a hand-rolled one.
