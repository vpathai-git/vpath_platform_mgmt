# Deployment

The app is web-only. It has no app-owned API backend. Its same-origin
`/api/platform/*` route forwards the authenticated storage calls the SDK hooks
make to the VPATH platform API, and `/api/version` proxies the strict platform
deploy identity. All config is injected at runtime via env (never baked into the
build): `VPATH_API_BASE_URL` — the platform API target, a Dapr-shape invoke URL
known only at runtime.

## Cluster

1. Build and deploy the web app through the normal platform app pipeline.
2. The manifest is auto-discovered (P5) — **zero platform edits**. The generator
   reads `spec.appStorage.folders[]` and provisions the declared folders, and
   `spec.capabilities.storageExplorer` enables the browse surface.
3. Open the app from the platform sidebar. The storage hooks call the platform
   storage API through the same-origin proxy; missing config or an unreachable
   API surfaces as a visible fail-closed state, never a faked empty store.

Do not add generated K8s resources to this directory. Do not add a bespoke
volume mount or a hand-built file service — storage is a platform citizen the
app only declares (CITIZENS.md §3).

## Standalone

Storage is standalone-capable (served platform-API-side; `StateStore` is SQLite
locally). Registration is still needed for the app to boot in the integrated
shell.

Until standalone boot discovery is complete, add one isolated entry to
`NEXT_APPS` in the platform checkout's `standalone/src/main/index.ts`:

```ts
"vpath-storage-demo": {
  appName: "vpath-storage-demo",
  basePath: "/storage-demo",
  sourceDirRel: path.join("apps_infra", "apps", "vpath-storage-demo"),
  clientId: "vpath-storage-demo",
  windowTitle: "Storage Demo (standalone)",
  catalog: {
    id: "storage-demo",
    label: "Storage Demo",
    description: "Browse the app's declared storage folders",
    icon: "database",
  },
},
```

The standalone supervisor already injects `VPATH_RUNTIME=standalone`, the
platform API route used by the storage/version proxies, and `VPATH_API_BASE_URL`.
If that checkout contains a `PICKED_NEXT_APPS` allowlist, add
`vpath-storage-demo` to it as a separate, additive edit; otherwise the
registered app will not boot. No Python spawn entry is needed because this
example has no backend.

Then run the integrated Electron shell and execute the scenario named
`standalone-storage-demo`. The expected proof is limited to sidebar catalog
visibility, the rendered intro and declared-folders surface, and one honest
terminal state for the live roots (roots, empty, or fail-closed unavailable).

## Verification status

- Source, manifest, TypeScript, and Book gates: mechanically verifiable here.
- Render / empty-state path: scenario-authored; only verified after a real
  integrated-shell run.
- Storage API roundtrip (roots → listing → create): unverified in this
  environment (needs a running platform).
