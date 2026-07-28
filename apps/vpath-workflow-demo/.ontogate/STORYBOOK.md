# STORYBOOK.md — workflow demo concept stories

The hull stories in `usecases.json` carry the manifest and platform-boundary
doctrine. This book narrates the example-specific UI proof.

## K01 — honest standalone workflow surface (positive, as_is)

From the real sidebar path, the integrated-shell scenario finds Workflow Demo,
opens it, reads the app-owned template name and the three-step configuration,
then verifies the explicit `No standalone workflow engine` state and the
absence of a run button. Twin (R-E):
`tests/standalone-workflow-demo.proof.ts`, which re-exports the canonical
`tests/scenarios/standalone-workflow-demo.ts` scenario.

## Forbidden stories — the red drill (each mutation on a scratch copy)

- **KN1** — an entity name detached from the book ONTOLOGY.md: R-A reds; the
  doc index and dated pin record also make R-C and R-D red.
- **KN2** — a source file lands outside the catalog: R-B reds.
- **KN3** — an entity loses its concept doc: R-C reds.
- **KN4** — a validated concept changes without a matching re-pin: R-D reds.
- **KN5** — the standalone proof twin forgets its story id: R-E reds.
