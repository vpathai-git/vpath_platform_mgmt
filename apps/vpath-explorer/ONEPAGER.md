# The vpath-explorer app — cross-app file manager

vpath-explorer is the platform's cross-app **file manager**: an authenticated user opens Explorer from the sidebar and browses, views, and manages their storage roots (`{app}/{folder}`) across every app — writable workspace folders (Documents/Downloads), read-only output roots (e.g. KP output roots), and the private `.state` root — always through the SDK storage hooks into the app's `/api/platform` proxy, never a direct filesystem.

## How this mount is governed

The authored Spine is `.ontogate/spine.yaml`; it models the app's own domain
delta as `explorer_spine`, a project-layer per-app fleet child. It **grafts**
`app_model_spine` (M11, deep topology — the fleet parent at `apps_infra/.ontogate/`)
and **extends** `app_base_spine` (M12, the shared app vocabulary at
`apps_infra/app_base/.ontogate/`). The platform hull (auth, the activity/header
bar, egress/NetworkPolicy, version-lineage, health) arrives by inheritance plus
the frozen 066 hull contract (`.ontogate/imported/hull_contract.json`, checked by
M11c freshness at the parent roll-up) and is never re-described here. The KP
output roots and the KP lifecycle are `kp_lifecycle_spine`'s; the storage
endpoints and per-user authz are platform-api's — both consumed across a seam,
cross-referenced, never re-pinned (see `.ontogate/FINDINGS.md`).

The three axioms are EX1 (cross-app storage only through the platform-api proxy,
user-scoped, server-enforced), EX2 (read-only output roots are respected, not
app-enforced — writes go only to writable roots), and EX3 (every FileView binds
to a live storage result — no fabricated or stale tree). EX1 is mechanized (the
app proxy is the only storage path); EX2 and EX3 hold by structure but their
negatives are UNGUARDED — pinned as-is (`EA1`, `EA2`) and drained by the to-be
scans `EX10`/`EX11`. The requirement seam is n/a on record — the app is specified
by its manifests (`vpath-app.yaml`, `app-card.yaml`) and code, not an external
requirement document (`.ontogate/FINDINGS.md :: requirement-seam-2026-07-17`).

The catalog carries a readable flow map (`op_read`/`op_write` reads the roots and
serves/produces the views and entries; the three FileViews consume the roots and
entries they render). Use `.ontogate/STORYBOOK.md` to read the realized, to-be,
forbidden, and as-is flows. `.ontogate/ONTOLOGY.md` is the human catalog, while
`.ontogate/ontology.json` and `.ontogate/usecases.json` are the machine forms.
Run `.ontogate/check.py` through the interpreter named by `.ontogate/PYTHON`.
Regenerate only through `.ontogate/regenerate.py` with the repository's central
authoring environment.

## Key doors

- `.ontogate/spine.yaml` — authored model and observable flow map
- `.ontogate/STORYBOOK.md` — use-case catalog and expected violations
- `.ontogate/FINDINGS.md` — pinned findings, decisions, and walk records
- `.ontogate/imported/hull_contract.json` — frozen 066 hull contract (M11)
- `.ontogate/check.py` — mount gate
- `src/hooks/useFileSystem.ts` — the SDK storage hooks the app re-exports
- `src/app/api/platform/[...path]/route.ts` — the `/api/platform` proxy (EX1)
