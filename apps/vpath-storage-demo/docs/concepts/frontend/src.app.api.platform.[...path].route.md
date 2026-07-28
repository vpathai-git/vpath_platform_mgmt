---
entity: src.app.api.platform.[...path].route
kind: frontend
stories: []
tests: [tests/standalone-storage-demo.proof.ts]
status: validated
validated: 2026-07-22
---

# Platform storage proxy

The same-origin catch-all route forwards the storage hooks' authenticated
`/api/platform/v1/storage/*` calls to the VPATH platform API. The target is read
per request from `VPATH_API_BASE_URL` (SDK `createProxyRoute` + delegated auth);
the app bakes in no URL and validates no token itself.
