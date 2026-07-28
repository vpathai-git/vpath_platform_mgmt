---
entity: web.proxy
kind: frontend
stories: []
tests: []
status: validated
validated: 2026-07-12
---

# web.proxy — the SDK proxy route to the backend

`createProxyRoute` + `getRequiredEnv`: forwards `/api/fortune/*` to the
backend's Dapr-shape invoke URL, read from the environment PER REQUEST (never
baked into the build — CLAUDE.md §5), streaming bodies. Session comes from
[[web.auth]]'s NextAuth options. Missing env fails fast, no soft default
(CLAUDE.md §7).
