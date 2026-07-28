---
entity: src.pages.api.auth.[...nextauth]
kind: frontend
stories: []
tests: [tests/standalone-storage-demo.proof.ts]
status: validated
validated: 2026-07-22
---

# Delegated auth handler

The SDK NextAuth handler runs the OIDC redirect flow in iframe-compatible mode.
The app builds no password form and validates no token; the platform Keycloak
owns identity, and the platform proxy consumes these auth options.
