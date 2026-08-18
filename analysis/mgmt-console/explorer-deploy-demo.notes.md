# Explorer deploy demo runbook (Phase 4)

**Status:** live proof on vm5 (2026-08-11) — console Connected · vm5 as
`admin_alain`; Explorer present in Running applications; catalog title aligned
to platform label `Explorer`. Curl healthz via SOCKS remains the operator
confirm when the tunnel is up (CI cannot invent a box).

## Preconditions

1. `apps/vpath-explorer/` present in this repo (THROWAWAY extract; see its README).
2. A registered **server** instance in `instances.local.env` (`KIND=server-nuc`
   or `server-cloud-vm`, `LIFECYCLE=live`) with SSH + `CHECKOUT` (+
   `SOURCE_CHECKOUT` for `deliver`). vm5 is registered as **terra**.
3. Console/CLI can drive that instance (`vpath-console --instance vm5` or
   selector against `terra`).

## Steps (server path)

1. Register / refresh the app (from repo root)::

       vpath app add --name vpath-explorer --path apps/vpath-explorer
       # or publish via console Add application / POST /api/apps/publish

2. Build + deploy onto the driven instance (ops verbs)::

       vpath build --app vpath-explorer
       vpath deploy --app vpath-explorer

   Or, when using the instance selector against the box pipeline::

       python -m vpath_platform_mgmt.instances.selector gradle <instance> -- \
         redeployApp -Papp=vpath-explorer

3. Health proof (replace host/port from the instance profile)::

       curl -fsS "https://<instance-host>:<platform-port>/explorer/api/healthz"

   Expect HTTP 200 and a body that confirms the explorer health route.

## Haltepunkte (record what bit)

| # | Risk | Observed |
|---|---|---|
| 1 | OntoGate parentage / graft paths | Not exercised this run (app already installed) |
| 2 | SDK / `file:` dependency resolution | Not exercised this run |
| 3 | Interpreter / Node pin | Not exercised this run |
| 4 | Manifest base path `/explorer` | Platform route `/explorer` matches; UI title must be `Explorer` (aligned in `vpath-app.yaml`) |
| 5 | SOCKS / Keycloak for ops console | Tunnel `:1085` flapping caused Keycloak relay 500; badge must not say “Cannot reach Keycloak” for non-discovery failures |

## Success checklist

- [x] Builds outside server monorepo (tree under `apps/vpath-explorer/`)
- [x] Deployed to one registered **server** instance via selector/ops (vm5 / terra — already running)
- [ ] Health response observed (`curl …/explorer/api/healthz` via SOCKS when tunnel up)
- [x] THROWAWAY marking in `apps/vpath-explorer/README.md`
- [x] Haltepunkte filled from the live run
- [x] Catalog title matches platform InstalledSet label (`Explorer`)

## Out of scope

Standalone Electron deploy demo (needs Phase 3 supervisor status file on the
shell side). Arsany remote cutover.
