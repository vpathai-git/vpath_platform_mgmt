# OntoGate adoption — vpath-agentic-resource-modeling (Spine-3)

This app is modeled in **OntoGate**: each feature is a *story* composed from the
app-hull **foundation** (Spine-2, the kit's `foundation/`) + this app's **Spine-3**
(`spine.yaml`). The gate rejects anything that doesn't compose.

Unlike `vpath-fortune-teller` (self-contained, NEED face honestly empty), this app
**fills the NEED face for real**: it DECLARES an `agent-provider` resource so the
platform provisions/injects it.

## Run it

```bash
python3 examples/vpath-agentic-resource-modeling/.ontogate/regenerate.py   # spine.yaml -> ontology.json
python3 examples/vpath-agentic-resource-modeling/.ontogate/check.py        # the gate
```

`check.py` is a three-layer composition (per `foundation/ADOPTION.md`):

1. the kit's vendored **gatelib** — M10 freshness on the generated `ontology.json`,
   `story_lint` grammar, `verdict` pinning;
2. the **foundation audit** (`foundation/audit`) run against THIS app repo
   (read-only) — the 34 hull contracts as file checks;
3. **app stories** (`usecases.json`) — a POSITIVE story per contract (plus four
   extra runtime positives, P28–P31, for the WP3 `get_agent_factory()` path) and
   NINE NEGATIVE stories (the red-drill: each applies a mutation from
   `tests/mutations.py` to a scratch COPY and asserts the named contract goes RED,
   then discards the copy). 40 stories total.

## The NEED face is REAL here (the point of this example)

The foundation audit is deliberately **lenient** on the NEED face — an absent need
reads as "unused" and passes, because "an under-declared real need is caught by the
per-app story, not silently here" (the foundation's own words). So `check.py` adds an
**app-strict NEED override**: because this app's Spine-3 declares
`need.resource_requirements.declared: true`, the root manifest **MUST** carry
`resourceRequirements`, or `C-need-resource-requirements` goes RED.

That makes the DECLARED need **binding** and gives the red-drill teeth:

- **N07 `delete-resource-requirements`** strips the agent-provider declaration from
  the manifest → `C-need-resource-requirements` goes RED (the app-strict check fires).
- **N08 `bespoke-secret-mount`** reads a K8s secret NAME in code →
  `C-no-bespoke-secret-mount` goes RED (the LLM key must stay platform-managed via
  envfrom; the app models config, not credentials).
- **N09 `runtime-bespoke-key-read`** (WP3) does the same on the Python RUNTIME
  surface — a backend module names a K8s secret to fetch the LLM key itself →
  `C-no-bespoke-secret-mount` goes RED. The runtime reaches cognition ONLY via
  `get_agent_factory()`; it never fetches a provider key.

## What it proves

- **34/34 contracts green** on the real app (`APP  PASS green`).
- **The gate can say NO**: nine negative stories fire their contracts on the
  mutated copy (a gate that never rejects is unproven).
- **The NEED face is filled FOR REAL**: `C-need-resource-requirements` passes
  because the agent-provider declaration is present, and fails the moment it is
  removed. Contrast `vpath-fortune-teller`, whose NEED face is honestly empty.

## Provenance

`ontology.json` is GENERATED from `spine.yaml` — never hand-edit it. Editing
`spine.yaml` without re-running `regenerate.py` makes the gate exit 2 (M10 stale).
The mutation fixtures live under `tests/` so the foundation audit skips them (they
carry deliberate trigger literals that would otherwise read as real violations).
