# ONTOLOGY.md — vpath-storage-demo concept catalog

The human-form home of the app's CONCEPT PLANE (five rules R-A..R-E, kit
flavor of the baseline starter seed). The machine form lives in `spine.yaml`
(`entities:` / `concept_pins:`, source of truth) → `ontology.json` (generated
— never hand-edit). The hull plane (27 foundation contracts) is documented in
`README.md`; both planes are gated by the SAME `check.py`.

**The Spine IS the index** (R-C): every entity links its concept doc at a
fixed place — topic → kind → entity, no separate index file that could drift.

## Catalog

| entity | kind | path | concept doc |
|---|---|---|---|
| src.app.api.healthz.route | frontend | src/app/api/healthz/route.ts | [docs/concepts/frontend/src.app.api.healthz.route.md](../docs/concepts/frontend/src.app.api.healthz.route.md) |
| src.app.api.platform.[...path].route | frontend | src/app/api/platform/[...path]/route.ts | [docs/concepts/frontend/src.app.api.platform.[...path].route.md](../docs/concepts/frontend/src.app.api.platform.[...path].route.md) |
| src.app.api.version.route | frontend | src/app/api/version/route.ts | [docs/concepts/frontend/src.app.api.version.route.md](../docs/concepts/frontend/src.app.api.version.route.md) |
| src.app.layout | frontend | src/app/layout.tsx | [docs/concepts/frontend/src.app.layout.md](../docs/concepts/frontend/src.app.layout.md) |
| src.app.page | frontend | src/app/page.tsx | [docs/concepts/frontend/src.app.page.md](../docs/concepts/frontend/src.app.page.md) |
| src.components.providers | frontend | src/components/providers.tsx | [docs/concepts/frontend/src.components.providers.md](../docs/concepts/frontend/src.components.providers.md) |
| src.components.storage-demo | frontend | src/components/storage-demo.tsx | [docs/concepts/frontend/src.components.storage-demo.md](../docs/concepts/frontend/src.components.storage-demo.md) |
| src.pages.api.auth.[...nextauth] | frontend | src/pages/api/auth/[...nextauth].ts | [docs/concepts/frontend/src.pages.api.auth.[...nextauth].md](../docs/concepts/frontend/src.pages.api.auth.[...nextauth].md) |

Dependency edges (R-B checks declared == observed imports): the platform
storage proxy depends on delegated auth; the layout depends on providers; the
page depends on the storage explorer surface.

## Extension records (R-D — the permission ledger)

Editing a validated concept doc requires a re-pin in `spine.yaml` plus a dated
record line here naming the entity. Records:

- 2026-07-22 — validated and pinned src.app.api.healthz.route.
- 2026-07-22 — validated and pinned src.app.api.platform.[...path].route.
- 2026-07-22 — validated and pinned src.app.api.version.route.
- 2026-07-22 — validated and pinned src.app.layout.
- 2026-07-22 — validated and pinned src.app.page.
- 2026-07-22 — validated and pinned src.components.providers.
- 2026-07-22 — validated and pinned src.components.storage-demo.
- 2026-07-22 — validated and pinned src.pages.api.auth.[...nextauth].
