# ONTOLOGY.md — vpath-fortune-teller concept catalog (the app domain Spine)

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
| api.server | backend | api/server.py | [docs/concepts/backend/api.server.md](../docs/concepts/backend/api.server.md) |
| api.main | backend | api/src/main.py | [docs/concepts/backend/api.main.md](../docs/concepts/backend/api.main.md) |
| api.pkg | backend | api/src/fortune/__init__.py | [docs/concepts/backend/api.pkg.md](../docs/concepts/backend/api.pkg.md) |
| api.deck | backend | api/src/fortune/deck.py | [docs/concepts/backend/api.deck.md](../docs/concepts/backend/api.deck.md) |
| api.routes | backend | api/src/fortune/routes.py | [docs/concepts/backend/api.routes.md](../docs/concepts/backend/api.routes.md) |
| web.layout | frontend | src/app/layout.tsx | [docs/concepts/frontend/web.layout.md](../docs/concepts/frontend/web.layout.md) |
| web.page | frontend | src/app/page.tsx | [docs/concepts/frontend/web.page.md](../docs/concepts/frontend/web.page.md) |
| web.providers | frontend | src/components/providers.tsx | [docs/concepts/frontend/web.providers.md](../docs/concepts/frontend/web.providers.md) |
| web.proxy | frontend | src/app/api/fortune/[...path]/route.ts | [docs/concepts/frontend/web.proxy.md](../docs/concepts/frontend/web.proxy.md) |
| web.healthz | frontend | src/app/api/healthz/route.ts | [docs/concepts/frontend/web.healthz.md](../docs/concepts/frontend/web.healthz.md) |
| web.version | frontend | src/app/api/version/route.ts | [docs/concepts/frontend/web.version.md](../docs/concepts/frontend/web.version.md) |
| web.auth | frontend | src/pages/api/auth/[...nextauth].ts | [docs/concepts/frontend/web.auth.md](../docs/concepts/frontend/web.auth.md) |

Dependency edges (R-B checks declared == observed imports):
`api.server → api.main → api.routes → api.deck`, `api.pkg → api.deck`,
`web.layout → web.providers`, `web.page → web.providers`,
`web.proxy → web.auth`.

## Extension records (R-D — the permission ledger)

Editing a validated concept doc requires a re-pin in `spine.yaml` PLUS a dated
record line here naming the entity — the recorded, conscious act IS the
permission. Records:

- 2026-07-12 api.server: validated at birth (concept plane adoption, plan Änderung 5)
- 2026-07-12 api.main: validated at birth (concept plane adoption, plan Änderung 5)
- 2026-07-12 api.pkg: validated at birth (concept plane adoption, plan Änderung 5)
- 2026-07-12 api.deck: validated at birth (concept plane adoption, plan Änderung 5)
- 2026-07-12 api.routes: validated at birth (concept plane adoption, plan Änderung 5)
- 2026-07-12 web.layout: validated at birth (concept plane adoption, plan Änderung 5)
- 2026-07-12 web.page: validated at birth (concept plane adoption, plan Änderung 5)
- 2026-07-12 web.providers: validated at birth (concept plane adoption, plan Änderung 5)
- 2026-07-12 web.proxy: validated at birth (concept plane adoption, plan Änderung 5)
- 2026-07-12 web.healthz: validated at birth (concept plane adoption, plan Änderung 5)
- 2026-07-12 web.version: validated at birth (concept plane adoption, plan Änderung 5)
- 2026-07-12 web.auth: validated at birth (concept plane adoption, plan Änderung 5)
