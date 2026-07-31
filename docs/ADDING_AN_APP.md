# Adding an Application

> **Status: implemented.** How an organization's repository becomes an app
> running under ArgoCD. For the verb surface this sits on, read
> `PLATFORM_FUNCTIONS.md`; for the design decisions behind the registry and
> the pipeline, `superpowers/specs/2026-07-30-app-registry-design.md` and
> `superpowers/specs/2026-07-30-app-publish-pipeline-design.md`.

## Four catalogues, and why they disagree

Most confusion about "is the app added?" comes from treating these as one
thing. They are four populations, and on a real installation they overlap
far less than people expect.

| Catalogue | Lives in | Says | Written by |
|---|---|---|---|
| **Console catalogue** | this repo's `apps/<name>/` | what this console can *describe* | `register` stage |
| **Server tree** | `apps_infra/apps/<name>/` on the box | what the build host can *build* | `send` stage |
| **InstalledSet** | Deploy-of-Record (Gitea) | what the server *runs* | `install` stage |
| **Platform catalogue** | `app-catalog` ConfigMap | what users *see in the sidebar* | `./gradlew deployAppCatalog` |

Measured on vm5, 2026-07-31: the console catalogue held 6 apps, the
InstalledSet held 18, and they overlapped in **one**. An app missing from the
console catalogue is not "not installed" — it means nobody registered it
here. The console's *Running applications* section reads the InstalledSet
precisely so it cannot inherit that blind spot.

The fourth is the one people forget: changing a sidebar label needs the
server manifest edited, `deployAppCatalog`, **and** a `vpath-web` rollout
restart, because the ConfigMap is mounted with `subPath` and Kubernetes never
refreshes those in a running pod.

## The five stages

`POST /api/apps/publish` runs all five as one job. Each is delegated to the
unit that already owns it, so a failure names exactly one owner.

```
preflight → register → send → render → install
```

| Stage | Does | Fails when |
|---|---|---|
| `preflight` | reads the repo through `gh`, refuses a tree that cannot build | the SDK rule below is broken, or there is no entrypoint |
| `register` | writes `apps/<name>/` in this repo | the name disagrees, or the port is taken |
| `send` | downloads the subtree and materializes it into the server checkout | no checkout is configured, or the tarball escapes its root |
| `render` | `./gradlew redeployApp` — builds the image, commits the render | the build host rejects it |
| `install` | adds the name to the InstalledSet, waits for ArgoCD | ArgoCD does not converge in time |

Nothing is cloned to inspect a repository: `preflight` asks GitHub through
`gh`, which already holds the operator's authentication. Cloning is used only
in `send`, where the whole tree genuinely is the payload.

**Resume is by observation, not a ledger.** Re-running after a failure skips
`register` and `send` only when the recorded commit matches exactly. `render`
and `install` are never skipped — both are already idempotent, so an
unchanged app rebuilds nothing and an installed app only has its sync
verified.

## What the repository must look like

### It needs a manifest, or the facts to generate one

A repository that ships `vpath-app.yaml` is taken as **authored**: the file is
copied byte for byte, and passing generation flags is refused as meaningless.
The name you publish under must equal its `metadata.name`.

A repository without one gets a manifest generated here, which needs
`name`, `port`, `base_path` and `title`. Ports are **never** assigned
automatically — pick a free one; a collision is refused naming the holder.

A generated manifest is provisional by design. `vpath-source.yaml` records
`manifest_origin: generated`, and `refresh` adopts an upstream manifest the
moment one appears. Upstream always wins.

### The SDK rule

This is the check that exists because of a real failure: source materialized
cleanly, then the image build died on `Can't resolve '@vpath/sdk'`. The
repository declared `file:../../kit/sdk` — its own layout — while the server
serves the SDK at `apps_infra/sdk`.

An app lands at `apps_infra/apps/<name>/`. Every path is resolved against
**that** directory, not pattern-matched. A dependency leaving the app's own
folder is not an error — `spec.build.sdks` is exactly how an app declares one,
and every app in `apps/` uses it. The rule is:

> For every `spec.build.sdks[]` entry, the `file:` dependency of the same name
> must resolve, relative to `apps_infra/apps/<name>`, to that entry's `source`.

A worked example. For an app named `vpath-knowledge-builder` declaring:

```yaml
spec:
  build:
    runtime: node
    sdks:
      - name: "@vpath/sdk"
        source: apps_infra/sdk
```

its `package.json` must say `"@vpath/sdk": "file:../../sdk"`. Writing
`file:../../kit/sdk` resolves to `apps_infra/kit/sdk`, which the server does
not put in the tree, and preflight refuses with that exact remedy.

Python is the same rule stated for `path = "..."` dependencies:
`vpath-backend-sdk` at `apps_infra/sdk-python/vpath-backend-sdk` is written
`path = "../../sdk-python/vpath-backend-sdk"`.

### The other three checks

- **`spec.build.hash.dirs`** may name only this app's directory and the
  sources of SDKs it declares. The content hash is what makes the app rebuild
  when its SDK changes; anything else in there hashes a directory this app
  does not consume.
- **A node app needs `package.json` with a `scripts.build`** — the image build
  runs that step.
- **A python app needs `pyproject.toml`.**

Preflight reports **every** finding at once, each with the one-line fix, so a
repository is not corrected one round-trip at a time. It writes nothing and
reaches nothing; a refusal leaves no half-registered app behind.

## Running it

### From the console (the normal path)

Server Dashboard → **Add an application**. Fill in the repository URL, the
ref, the app name, and — only if the repository ships no manifest — expand
*The repository ships no vpath-app.yaml* and give port, base path and title.

`path` selects the app **inside** the repository. Organization repositories
are usually npm workspace roots whose apps live under `examples/`; the root is
not the app, and reading it would describe the workspace. Leave it blank only
when the repository root really is the app.

### From the API

```bash
curl -X POST http://127.0.0.1:8765/api/apps/publish \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"url":"github.com/org/repo","ref":"main",
       "path":"examples/my-app","name":"vpath-my-app"}'
```

Admin only; returns `202` with a job id. Watch it in *Recent jobs*, or
`GET /api/jobs/<id>` for the full log. `400` means the request itself was
malformed, `403` that the caller is not an admin.

### From the CLI (one stage at a time)

There is **no** `publish` command — the one-shot walk is HTTP only. The CLI
exposes the stages separately, which is what you want when a publish failed
part-way and you are fixing one thing:

```bash
vpath app add github.com/org/repo --ref main   # register only
vpath app send <name>                          # into the server checkout
vpath app refresh <name>                       # re-fetch, adopt upstream manifest
vpath app list                                 # what is registered here
```

## Verifying it actually runs

A commit into the Deploy-of-Record is not a deployment. `install` waits for
ArgoCD, but the honest check is what the cluster is doing:

Server Dashboard → **Running applications** → expand the app. It shows the
namespace ArgoCD deploys it into and the pods running there, plus any
`kp-<app>-<user>` project namespaces. Note the namespace is read from ArgoCD's
`spec.destination.namespace` and is frequently **not** the app's name — on vm5
that is true for 7 of 18 installed apps.

Requires `VPATH_MGMT_K8S_URL` and `VPATH_MGMT_K8S_TOKEN`, and the console's
ServiceAccount needs `pods: list` (see `vpath_server`'s
`platform_infra/kubernetes/mgmt-console/rbac.yaml`). Without them the section
says so rather than showing an empty list.

If ArgoCD sits on a stale revision — observed for hours despite
`selfHeal: true` — force it:

```bash
kubectl -n argocd annotate application <app> argocd.argoproj.io/refresh=hard --overwrite
```

## Reading a refusal

Every failure is prefixed with the stage that produced it, and no stage
writes anything before it refuses.

| Message begins | Means |
|---|---|
| `preflight:` | the repository as it stands cannot build — fix the repo |
| `register:` | name or port conflict here — nothing reached the server |
| `send:` | the server checkout is missing or the payload was rejected |
| `render:` | the build host refused; run the named gradle task there |
| `install:` | committed, but ArgoCD did not converge — the record is authoritative |

Two refusals are deliberate rather than bugs:

- **`'<name>' is already registered — pass --replace`.** Overwriting destroys
  the existing checkout directory, so it needs saying out loud.
- **`the repository's manifest names 'X', not 'Y'`.** Publish under the name
  the repository declares; the platform derives the sidebar id from it.

```yaml
validated: 2026-07-31
review_horizon_days: 180
```
