# OntoGate adoption — vpath-fortune-teller (Spine-3)

This app is modeled in **OntoGate**: each feature is a *story* composed from the
app-hull **foundation** (Spine-2, the kit's `foundation/`) + this app's **Spine-3**
(`spine.yaml`). The gate rejects anything that doesn't compose.

## Run it

```bash
python3 examples/vpath-fortune-teller/.ontogate/regenerate.py   # spine.yaml -> ontology.json
python3 examples/vpath-fortune-teller/.ontogate/check.py        # the gate
```

`check.py` is a four-layer composition (per `foundation/ADOPTION.md` + the
concept-gate-maturity plan, 2026-07-12 Änderung 5):

1. the kit's vendored **gatelib** — M10 freshness on the generated `ontology.json`,
   `story_lint` grammar, `verdict` pinning;
2. the **foundation audit** (`foundation/audit`) run against THIS app repo
   (read-only) — the 34 hull contracts as file checks;
3. **app stories** (`usecases.json`) — one POSITIVE story per contract (asserts the
   audit passes on the real app) + six NEGATIVE stories (the red-drill: each applies
   a mutation from `tests/mutations.py` to a scratch COPY and asserts the named
   contract goes RED, then discards the copy);
4. the **concept plane** (`concept_rules.py`) — the five starter rules over the
   app-domain catalog (`spine.yaml` `[app-catalog]` → `ONTOLOGY.md` /
   `STORYBOOK.md` / `FINDINGS.md` / `docs/concepts/`), with its own negative
   concept stories (KN1..KN5) red-drilling each rule on scratch copies.

## The method cycle the concept plane enforces

1. **Entry** — a feature enters as `/ontogate <request>`, never directly as code.
2. **Gate first** — run `check.py`; red is repaired before anything else.
3. **Analyze against the stock** — express the feature as a model fragment:
   which catalog entities does it touch or compose? For every touched entity
   the deep-dive sits at a fixed place: `docs/concepts/<kind>/<entity>.md`
   (R-C makes gaps red).
4. **Existing concept touched?** — only as a conscious extension: user
   permission, dated record in `ONTOLOGY.md`, sha re-pin (R-D reds without it).
5. **Tests before implementation** — the story lands with its twin test born
   red (strict xfail + `to_be` pin, a visible finding); forbidden stories get
   red-drill mutations instead (R-E).
6. **Implement inside the frames** — code without a catalog entry is
   impossible (R-B).
7. **Land** — flip the pins green, pull the doc lockstep (R-A/R-C); a green
   gate means model, docs, tests and code tell the same story.

## What it proves

- **34/34 contracts green** on the real app (`APP  PASS green`).
- **The gate can say NO**: the six negative stories fire their contracts on the
  mutated copy (a gate that never rejects is unproven).
- **The NEED face is honestly empty**: this app binds no external system, so
  `C-need-resource-requirements` passes because there is *nothing to declare*
  (`fill.backend/frontend/manifest` all realized; `need.resource_requirements:
  false`). Contrast `vpath-hello-confluence`, which declares a credential need.

## Provenance

`ontology.json` is GENERATED from `spine.yaml` — never hand-edit it. Editing
`spine.yaml` without re-running `regenerate.py` makes the gate exit 2 (M10 stale).
The mutation fixtures live under `tests/` so the foundation audit skips them (they
carry deliberate trigger literals that would otherwise read as real violations).
