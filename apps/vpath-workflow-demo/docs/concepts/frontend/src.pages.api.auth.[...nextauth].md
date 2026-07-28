---
entity: src.pages.api.auth.[...nextauth]
kind: frontend
stories: []
tests: [tests/standalone-workflow-demo.proof.ts]
status: validated
validated: 2026-07-22
---

# Delegated authentication handler

The SDK creates the iframe-compatible NextAuth handler and options consumed by
the proxy. The app contains no OIDC implementation or credential handling.
