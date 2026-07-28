# VPATH Storage Demo

`vpath-storage-demo` is the kit's first **Stores** application example (the
third first-class citizen, CITIZENS.md §3). It is a web-only Next.js app that
declares app-owned storage folders in its manifest and browses them through the
published SDK storage hooks. It writes no volume, no file service, and no
credential handling — it declares and consumes.

## What it declares

`vpath-app.yaml` carries:

- `spec.appStorage.folders[]` — three folders, one per visibility mode, each
  with a description:
  - **Notes** — `shared: private` (per-user, owner-only);
  - **Handbook** — `shared: read` (team-readable, read-only);
  - **Uploads** — `shared: readwrite` (shared read/write drop zone).
- `spec.capabilities.storageExplorer: true` — turns on the platform browse
  surface the storage hooks consume.

`spec.sharedFolders` and `spec.capabilities.storageAdmin` are intentionally
**not** declared: a jointly-mounted durable PVC needs a second mounter this
web-only example does not carry, and the demo performs no admin/bulk operations.
Declaring either would fake a capability (P6 — fail fast, never fall back).

## What it consumes

`src/components/storage-demo.tsx` calls `useStorageRoots`, `useStorageListing`,
and `useCreateFolder` from `@vpath/sdk`. Those hooks resolve their API base at
runtime from the browser location (see below) and call the platform storage API
through the app's same-origin `/api/platform/*` proxy route. The UI shows an
honest state at every step:

- **loading** while the roots query is in flight;
- **fail-closed unavailable** if the platform storage API cannot be reached —
  no empty store is faked;
- **empty** when the user has no visible roots yet;
- **roots + listing** when the platform serves them.

## How the storage hooks resolve their API base

The hooks are app-agnostic. `useStorageRoots` / `useStorageListing` build their
URLs with `apiFetch()`, which prefixes `getAppBasePath()` — the first path
segment of `window.location.pathname` — to the fixed suffix
`/api/platform/v1/storage/*`. Mounted at `/storage-demo`, the browser therefore
calls `/storage-demo/api/platform/v1/storage/roots`, which the app's
`src/app/api/platform/[...path]/route.ts` proxy forwards to the platform API
(`VPATH_API_BASE_URL`, injected at runtime). No app configuration is needed.
Source of truth: `kit/sdk/src/storage/hooks.ts` + `kit/sdk/src/utils/api-client.ts`.

## Runtime boundary and maturity

Storage is standalone-capable (CITIZENS.md §3: `StateStore` is SQLite locally,
storage is served platform-API-side), so — unlike workflow execution — this app
is not cluster-only. But a real storage **roundtrip** (roots → listing → create)
can only be exercised against a running platform.

Maturity:

- **Render / empty-state path** — scenario-verifiable. Covered by
  `tests/scenarios/standalone-storage-demo.ts`; a verification target until run
  in the integrated Electron shell.
- **Storage API roundtrip** — **code-complete / unverified**. This environment
  has no running platform, so no claim is made that a live roots/listing/create
  call has succeeded.

## Local mechanical checks

From the kit root:

```sh
npm ci
npm run build --workspace vpath-storage-demo
python3 examples/vpath-storage-demo/.ontogate/check.py
make check
```

`VPATH_API_BASE_URL` is required whenever the storage proxy or the version proxy
is used; the cluster and standalone supervisors inject it. See `DEPLOYMENT.md`
for cluster and standalone integration.
