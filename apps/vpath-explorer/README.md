# vpath-explorer (THROWAWAY extract)

**THROWAWAY.** This tree is a temporary extraction used to prove that the
Explorer app can be built and deployed from outside the server monorepo via
`vpath_platform_mgmt` (Axis 3 / M4). It is **not** a second long-term home.

## Future source of truth

When Arsany's Explorer app repository is ready, that remote becomes the only
source. This extract is then deleted or replaced by a pointer — do not keep
two maintenance copies.

## Health

- Manifest: `vpath-app.yaml`
- Health path: `/explorer/api/healthz` (see `src/app/api/healthz/route.ts`)

## Deploy demo

See `../../analysis/mgmt-console/explorer-deploy-demo.notes.md`.
