# STORYBOOK.md — concept stories (brownfield adoption)

The hull stories are narrated in `usecases.json`; THIS book narrates the
CONCEPT stories. The app was adopted brownfield: the catalog is an INVENTORY
(every entity `unmapped`, every concept doc a `reverse_draft` hypothesis).

## K01 — the expression backlog (positive, to_be — born red)

The inventoried modules become expressed concepts: entities mapped, concept
docs validated (dated, sha-pinned), real proofs named. Twin (R-E):
`tests/test_k01_expression_backlog.py` — a strict-xfail test that FLIPS GREEN
only when this story lands. Until then it is a visible, pinned finding.

## Forbidden stories — the red drill (each mutation on a scratch copy)

- **KN1** — an entity name detached from the book ONTOLOGY.md: R-A reds (and
  the doc index line carries the name, so R-C reds with it).
- **KN2** — a source file lands outside the catalog: R-B reds.
- **KN3** — an entity loses its concept doc: R-C reds.
- **KN4** — a pin freezing a reverse_draft hypothesis: R-D reds (the lock
  must never freeze unvalidated truth).
- **KN5** — the backlog twin forgets its story id: R-E reds.
