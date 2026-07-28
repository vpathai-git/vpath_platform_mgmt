---
entity: web.auth
kind: frontend
stories: []
tests: []
status: validated
validated: 2026-07-12
---

# web.auth — the NextAuth handler from the SDK

`createNextAuthHandler()` — login is an OIDC redirect handled by the platform
(Keycloak); this file only exports the handler and its `authOptions` (consumed
by [[web.proxy]] for the session). No password forms, no hand JWT validation,
ever (CLAUDE.md §3).
