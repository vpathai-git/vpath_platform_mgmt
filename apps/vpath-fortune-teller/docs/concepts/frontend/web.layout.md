---
entity: web.layout
kind: frontend
stories: []
tests: []
status: validated
validated: 2026-07-12
---

# web.layout — the root layout shell

Next.js root layout: mounts [[web.providers]], the SDK theme-init script
(`THEME_INIT_SCRIPT` before first paint, `suppressHydrationWarning`), the demo
banner and update prompt. Owns no theme toggle and no user widget — the
platform shell does (CLAUDE.md §2/§4).
