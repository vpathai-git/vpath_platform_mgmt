---
entity: api.pkg
kind: backend
stories: []
tests: []
status: validated
validated: 2026-07-12
---

# api.pkg — the backend package facade

The `fortune` package root: re-exports the deck vocabulary (`Card`,
`draw_fortune`) from [[api.deck]] so consumers import the domain, not a file
layout. Carries no logic of its own — a facade, kept thin on purpose.
