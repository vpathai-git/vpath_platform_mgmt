---
entity: api.deck
kind: backend
stories: []
tests: []
status: validated
validated: 2026-07-12
---

# api.deck — the oracle's deterministic deck

The domain core: a fixed, curated list of twelve `Card`s and the stable-hash
draw (`draw_fortune`). Determinism is the load-bearing concept — the same
question always maps to the same card (sha256, never the salted builtin
`hash()`), which is what lets UI tests cite an exact rendered string
(CLAUDE.md §7). The deck order is part of the contract: reordering changes the
question→card mapping and is a behavior change, not a refactor. A draw is
always a real card — the deck is non-empty by construction, so there is no
empty/placeholder fortune path.
