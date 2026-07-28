# STORYBOOK.md — storage demo concept stories

The hull stories in `usecases.json` carry the manifest and platform-boundary
doctrine (including the storage declaration itself). THIS book narrates the
example-specific UI proof.

## K01 — honest storage explorer surface (positive, as_is)

From the real sidebar path, the integrated-shell scenario finds Storage Demo,
opens it, reads the Stores-citizen intro and the manifest-declared folders (one
per visibility mode: private, read, readwrite), then verifies the live roots
surface reaches exactly one honest terminal state — real roots, an honest empty
store, or a visibly fail-closed "unavailable" — and that no folder contents are
fabricated. Twin (R-E): `tests/standalone-storage-demo.proof.ts`, which the
canonical `tests/scenarios/standalone-storage-demo.ts` scenario re-exports.

## Forbidden stories — the red drill (each mutation on a scratch copy)

- **KN1** — an entity name detached from the book ONTOLOGY.md: R-A reds; the
  doc index and dated pin record also make R-C and R-D red.
- **KN2** — a source file lands outside the catalog: R-B reds.
- **KN3** — an entity loses its concept doc: R-C reds.
- **KN4** — a validated concept changes without a matching re-pin: R-D reds.
- **KN5** — the standalone proof twin forgets its story id: R-E reds.
