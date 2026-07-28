---
entity: src.components.storage-demo
kind: frontend
stories: [K01]
tests: [tests/standalone-storage-demo.proof.ts]
status: validated
validated: 2026-07-22
---

# Storage explorer surface

The client component teaches the Stores citizen: it renders the manifest's
declared folders (one per visibility mode) and a live roots explorer driven by
`useStorageRoots` / `useStorageListing` / `useCreateFolder`. Every live state is
honest — loading, fail-closed unavailable, empty, and populated — and no folder
contents are ever fabricated.
