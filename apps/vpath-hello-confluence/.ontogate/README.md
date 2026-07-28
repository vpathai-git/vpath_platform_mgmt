# OntoGate adoption — vpath-hello-confluence (Spine-3, RETROACTIVE)

This app is modeled in **OntoGate**: each feature is a *story* composed from the
app-hull **foundation** (Spine-2, the kit's `foundation/`) + this app's **Spine-3**
(`spine.yaml`). The gate rejects anything that doesn't compose.

This is the kit's **first example** — built *before* the methodology stood, so the
adoption is **retroactive**. The 34-contract foundation audit ran green on the
**unmodified** app: this `.ontogate/` adds the gate; it fixes nothing.

What makes this Spine-3 distinct from the other two examples:

- **The richest NEED face**: it binds an EXTERNAL system and declares **two**
  resource kinds — a `credential` (system: confluence, `delivery: header`,
  `identityBearing: true`) and a `connector`. Contrast `vpath-fortune-teller`
  (NEED honestly empty) and `vpath-agentic-resource-modeling` (one kind).
- **A two-manifest pair**: the web `vpath-app.yaml` plus the sibling
  `api/vpath-app.yaml`. The app-strict NEED check is **pair-wide** — the api reads
  the gate-injected `X-Vpath-Credential-Confluence-*` headers, so its own manifest
  must authorize that use.
- **Two honest `as_is` pins** (findings to drain — both PLATFORM findings, see below).

## Run it

```bash
python3 examples/vpath-hello-confluence/.ontogate/regenerate.py   # spine.yaml -> ontology.json
python3 examples/vpath-hello-confluence/.ontogate/check.py        # the gate
```

`check.py` is a three-layer composition (per `foundation/ADOPTION.md`):

1. the kit's vendored **gatelib** — M10 freshness on the generated `ontology.json`,
   `story_lint` grammar, `verdict` pinning;
2. the **foundation audit** (`foundation/audit`) run against THIS app repo
   (read-only) — the 34 hull contracts as file checks;
3. **app stories** (`usecases.json`) — one POSITIVE story per contract, two `as_is`
   pins, and nine NEGATIVE stories (the red-drill: each applies a mutation from
   `tests/mutations.py` to a scratch COPY and asserts the named contract goes RED,
   then discards the copy).

## The pair-wide app-strict NEED check

The foundation audit is deliberately **lenient** on the NEED face — an absent need
reads as "unused" and passes. Because this app's Spine-3 declares
`need.resource_requirements.declared: true`, `check.py` enforces the
`resourceRequirements` declaration in **both** pair manifests, or
`C-need-resource-requirements` goes RED:

- **N07 `delete-resource-requirements`** strips the block from the root (web)
  manifest → RED.
- **N09 `delete-api-resource-requirements`** strips it from the sibling
  `api/vpath-app.yaml` → RED.
- **N08 `bespoke-secret-mount`** reads the K8s secret NAME (`confluence-creds`) in
  code → `C-no-bespoke-secret-mount` goes RED (the credential is gate-injected per
  request; the platform secret is never the app's to touch).

## The `as_is` pins (findings to drain)

Both pins are **platform findings**, not app defects; each drains through a
platform change, and neither blocks the hull adoption:

- **F1 — sibling-invoke URL** (`A01`): `env.VPATH_HELLO_CONFLUENCE_API_URL`
  hand-authors a Dapr-shape invoke URL to the api sibling because **no manifest
  field expresses a sibling invoke**. This is the exact jira-demo nuance the hull
  records under `C-no-handbuilt-dapr-url` ("the platform owes a sibling-invoke
  declaration"). The contract passes — it governs only the generated platform-api
  URL. Drains when the platform ships the declaration.
- **F2 — the platform PR carried in-tree** (`A02`):
  `platform-pr/external-services/confluence/` is a **platform-side value
  definition** (the proposed `confluence` external-service type) that the app
  carries because `vpath_server` ships neither the type nor any **Spine-1
  ontology** to compose the `system: confluence` value against. Per the hull
  membership criterion this value-space is **S3** (platform-owned: "the hull
  declares the SLOT, not the values"), so the missing platform ontology is
  **not a blocker** for this adoption — it is the recorded reason F2 exists.
  Drains when the platform PR lands (and, at Spine-1 altitude, when the platform
  exports an ontology for its external-service value-space).

**Drain re-evaluation 2026-07-11** (post gatelib 0.5.2→0.10.25, demand
`gatelib-method-refresh`): both drain conditions are still UNMET at platform
pin `f3fad225` — the manifest schema (`config/schemas/vpath-app-schema.json`)
still has no sibling-invoke field (F1), and `config/external-services/` still
ships no `confluence` type (F2; only `azure-openai`, `jira`, `openai`). Both
pins stay, honestly expressed. Next re-evaluation: on the next SDK pin bump.

**Drain re-evaluation 2026-07-19** (SDK pin bump f3fad225 → 984dc56e, +371
commits): both drain conditions are STILL UNMET at platform pin `984dc56e` —
no sibling-invoke field anywhere in the manifest vocabulary (code hits are
only the platform's own FINDINGS books), and `config/external-services/`
still ships only `azure-openai`, `jira`, `openai` (F2's `confluence` type
absent; Confluence appears only as a playbook example). Both pins stay,
honestly expressed. Next re-evaluation: on the next SDK pin bump.

## What it proves

- **34/34 contracts green** on the real, unmodified app (`APP  PASS green`) —
  the app was boundary-clean before the gate existed; the gate now keeps it so.
- **The gate can say NO**: nine negative stories fire their contracts on the
  mutated copy (a gate that never rejects is unproven).
- **A declared need is binding pair-wide**: `C-need-resource-requirements` fails
  the moment the declaration disappears from EITHER manifest of the pair.

## Provenance

`ontology.json` is GENERATED from `spine.yaml` — never hand-edit it. Editing
`spine.yaml` without re-running `regenerate.py` makes the gate exit 2 (M10 stale).
The mutation fixtures live under `tests/` so the foundation audit skips them (they
carry deliberate trigger literals that would otherwise read as real violations).
