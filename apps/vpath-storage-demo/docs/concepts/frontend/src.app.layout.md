---
entity: src.app.layout
kind: frontend
stories: []
tests: [tests/standalone-storage-demo.proof.ts]
status: validated
validated: 2026-07-22
---

# Root layout

The root layout mounts the provider tree, applies the theme-init script before
first paint, and renders the SDK demo/update chrome. It writes no header or
navigation — the activity bar is derived from the manifest.
