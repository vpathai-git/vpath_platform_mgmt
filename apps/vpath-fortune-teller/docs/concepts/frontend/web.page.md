---
entity: web.page
kind: frontend
stories: []
tests: []
status: validated
validated: 2026-07-12
---

# web.page — the product UI

The one page this app writes: ask a question, draw the card, render fortune +
sign. Writes ZERO header/nav chrome — the activity bar is SDK-rendered from
the manifest (CLAUDE.md §2). All colors are semantic tokens (`var(--vp-*)`),
never palette literals (CLAUDE.md §4). Talks to the backend exclusively
through [[web.providers]]' `useVpathMutation` against the proxy path.
