# Component 16 — App Source Delivery (verified against the real repos)

Decision 10 settled how *images* reach the server. This settles how *source*
reaches the engine — the seam that blocks deploying an app that lives in an
app repo rather than in the server monorepo.

## Verified facts (checked 2026-07-28 against `vpath_server` and `vpath_standard_apps@port-vpath-explorer`)

- **The verb commands in `LocalEngine` are correct.** `build.gradle.kts`
  registers `buildApp` ("Usage: `./gradlew buildApp -Papp=<name>`") and
  `redeployApp` ("Rebuild, transfer, and redeploy a single app: `-Papp=<name>`").
  `bin/vpath` provides `deploy` / `uninstall` / `status`.
- **Apps are auto-discovered by manifest**, from
  `apps_infra/apps/<name>/vpath-app.yaml`: "Adding a new app: create folder +
  vpath-app.yaml → build/transfer/deploy tasks auto-generated." Both gradle
  tasks validate `-Papp=` against that registry and fail loud on an unknown
  app.
- **Therefore the engine can only build an app whose source sits in the
  server checkout** at `apps_infra/apps/<name>/`.
- `vpath-explorer` is already present there and is the "Explorer" tile
  running on the shared server today.
- The ported copy (`vpath_standard_apps/apps/vpath-explorer`, 96 files vs 47)
  adds docs, OntoGate artifacts and tests, and one manifest change —
  `spec.deploy.readinessBudget: 300`. Its `build.hash.dirs` and
  `build.sdks[].source` still point at `apps_infra/apps/vpath-explorer` and
  `apps_infra/sdk`, i.e. **the ported app is not yet self-contained**; it
  still expects to be built from inside the server tree.

## Integration findings from the first real deploy (2026-07-28)

Running the Ops API on the shared server with `LocalEngine` surfaced two
things no amount of reading would have:

1. **Authorization is by group, not realm role.** The realm defines no custom
   realm roles; tokens carry `groups: ["/vpath-admins"]`. The validator now
   maps groups → platform roles (decision 6 unchanged in intent, corrected in
   mechanism).
2. **The engine needs the target's environment.** `lib/vm.sh` resolves its
   topology from the environment and aborts loudly otherwise
   (`run_build_vm called on deploy VM (linux)`). The right configuration for
   a target is its overlay selector — `VPATH_ENV=vm5` loads
   `config/dot_env/.env.vm5`, which supplies `VPATH_INSTALL_MODE` and the
   `NUC_*` host variables. The Ops API passes this through
   `VPATH_MGMT_ENGINE_ENV`, so each target is configured, never guessed.

Both failures were loud, correctly attributed, and left the platform
untouched — the fail-hard rule doing its job on first contact.

## Options

| Option | Weight | Pros | Cons |
|---|---|---|---|
| **A. Ops API materializes app source: fetch `<repo>@<ref>` and place it at `apps_infra/apps/<name>/` on the server, then run the engine verb (recommended)** | **8/10** | Works with today's pipeline unchanged; gives `deploy` a real, auditable source contract (repo + ref + commit recorded on the job); app repos stay the authoring home; matches manifest auto-discovery exactly | Source exists in two places transiently; needs a pinned ref and a clean materialize step (replace, never merge); concurrent deploys of one app already serialized by the app lock |
| B. Keep apps in the server monorepo; abandon the port | 3/10 | Zero work; status quo ships today | Contradicts the isolation goal and the app-repo direction the team is already building; app authors keep needing the server checkout |
| C. Make apps self-contained: fix `build.hash.dirs` + SDK resolution so an app builds from its own repo | 9/10 as end state | The real target — app repos become genuinely independent; no materialize step at all | Blocked on server-side pipeline work (the same class as the documented `vpath_server#19` SDK-resolve shim); not available now |
| D. Git submodule the app repo into the server checkout | 4/10 | Mechanical | Submodule pain; the monorepo-path assumptions remain; decision 2 already rejected this pattern for the pipeline |

**Recommendation: A now, C as the end state, never B or D.** The reasoning:
A is the smallest change that makes a management-plane deploy of an app-repo
app *possible today*, and it produces exactly the artifact the plan has been
missing — a source contract (`repo`, `ref`, resolved commit) stamped on the
job next to the image digest from decision 10, so a deploy is fully
traceable. It does not touch the stable server pipeline, honoring the design
constraint. C remains the goal because materialization is a workaround for
manifests that still name monorepo paths; when the SDK-resolve and hash-dir
work lands server-side, the materialize step deletes itself. The verb surface
does not change between A and C — only where the source comes from — so
nothing built now is wasted.

## Contract this adds to the `deploy` verb

- Input gains an optional source: `deploy <app> --from <repo>@<ref>`
  (default: whatever is already in the server checkout).
- The Ops API records `source_repo`, `source_ref`, and the resolved commit on
  the job, and refuses to materialize over a dirty target without an explicit
  replace (no silent overwrite).
- Materialization is Admin-gated at first, since it writes into the server
  checkout on the shared box.

## What this means for `vpath-explorer` specifically

Deploying the **monorepo copy** needs nothing new: `deploy vpath-explorer`
maps to `./gradlew redeployApp -Papp=vpath-explorer` and works as soon as the
Ops API runs on the server. Deploying the **ported copy** additionally needs
the materialize step above — and, before it can build unchanged, either its
manifest keeps pointing at `apps_infra/...` (fine under A, since that is
where it lands) or option C lands.
