# STORYBOOK.md — concept stories (the domain plane)

The hull stories (P01..P27, N01..N06 — one per foundation contract) are
narrated in `usecases.json` itself; THIS book narrates the CONCEPT stories the
five rules govern. Machine form: `usecases.json` → `concept_stories`.

## K01 — the domain round-trip is proven end-to-end (positive, as_is)

A user asks the oracle: `POST /api/draw` with an optional question returns the
deterministic card the deck maps that question to. Twin proof (R-E):
`api/tests/test_api.py` drives the REAL router (auth overridden) and asserts
the exact deterministic payload — including the ask-nothing first-time state.
The test back-references the story id; the story cannot land without it.

## Forbidden stories — the red drill (each mutation on a scratch copy)

- **KN1** — an entity name is detached from the book ONTOLOGY.md: lockstep
  reds (R-A), and the cascade is pinned honestly — the doc index line and the
  dated extension record carry the name too, so R-C and R-D red with it.
- **KN2** — a source file lands outside the catalog (`rogue-source`): the
  catalog↔src bijection reds (R-B). Code cannot be born past the model.
- **KN3** — an entity loses its concept doc (`delete-concept-doc`): the
  concept-doc bijection reds (R-C).
- **KN4** — a validated concept doc is edited without re-pin + dated record
  (`break-permission-lock`): the sha-pin permission lock reds (R-D).
- **KN5** — a story's proof test forgets its story id (`detach-story-proof`):
  the story-test twin reds (R-E).
