# Publishing a registered app repository, in one action

Date: 2026-07-30
Status: approved (design), not yet implemented
Follows: `2026-07-30-app-registry-design.md`

## Problem

Registering an app repository works and stops there. Getting that app running
takes four separate moves — `vpath app add`, `vpath app send`,
`./gradlew redeployApp` on the box, then an install verb — each with its own
preconditions, no shared view of where an app sits, and no gate that catches a
repository which cannot build until the build has already failed on the box.

The one real port on record failed exactly that way: source materialized
cleanly, then the image build died on `Can't resolve '@vpath/sdk'`, because the
repository declares `file:../../kit/sdk` while the server tree serves the SDK
at `apps_infra/sdk` (`07_app_source_delivery.md`). Nothing was published and
the running app was untouched, but the failure was found in the most expensive
possible place.

The missing piece is not a step. It is the spine connecting the steps, plus a
gate in front of them.

## Decisions

Five decisions were taken by the operator during design.

1. **One console action per app.** The operator submits a repository URL and
   the platform walks every stage as one job. Accepted cost: the console
   carries the manifest-generation form for repositories that ship no manifest.

2. **The job executes on the box's Ops API,** reached from a workstation
   through the tunnel. Accepted cost: the box must run the Ops API as a
   service, and the tunnel gains a port-forward. Rejected: driving the engine
   over SSH from a workstation, which would create the second authority the
   isolation plan warns against.

3. **A preflight gate refuses repositories that are not self-contained**,
   naming the file to fix. Accepted cost: onboarding a repository can require a
   change in that repository first. Rejected: rewriting dependency paths during
   materialization, which would put an invisible transformation in the
   management plane and is the kind of fallback this repository forbids.

4. **The flow starts at a URL and ends at a running app.** No terminal step.

5. **A failed publish is resumable and undoes nothing.** Partial state stays
   visible — a diff in the checkout, a commit in the record — and re-running
   skips what already succeeded.

## What already exists

Four of the five stages are built and tested. This design adds one gate and
the sequencing.

| Stage | Owner | State |
|---|---|---|
| preflight | `ops/app_preflight.py` | **new** |
| register | `ops/app_registry.py` | exists |
| send | `ops/source.py` | exists |
| render | `LocalEngine` (`redeployApp`) | exists |
| install | `GitOpsEngine` (InstalledSet + Argo wait) | exists |

## The two-engine fact

`redeployApp` builds the image, pushes it, renders manifests and commits them
into the Deploy-of-Record; that is `LocalEngine`'s `deploy`. Adding the name to
`installed-set.json` and waiting for ArgoCD is `GitOpsEngine`'s `deploy`. The
same verb name on two adapters, and `OpsService` holds exactly one engine.

Publish therefore cannot be a verb implemented inside an adapter. It is an
orchestrator that holds both.

## Design

### `ops/publish.py`

`PublishPipeline`, constructed with the units that own each concern:

```python
PublishPipeline(preflight, registry, materializer, local_engine, gitops_engine)
```

Sequencing and nothing else: no HTTP, no subprocess, no git, no filesystem
writes of its own. Every failure is attributable to exactly one owner, and the
pipeline's own tests need no network and no box.

Public surface: `run(request, emit) -> PublishResult`, where `emit` is the
existing `StepEmitter` so the console's job panel renders stages as steps with
no new progress machinery.

### `ops/app_preflight.py`

Read-only inspection of a fetched tree, before anything is written anywhere.
Refuses with the file, the offending value, and what to change in the app
repository:

- **Escaping dependency paths** — any `file:../` in `package.json`, any path
  dependency in `pyproject.toml` resolving outside the app tree. This is the
  recorded `@vpath/sdk` failure, caught at stage 0.
- **`spec.build.hash.dirs`** — every entry must name this app's own directory
  under `apps_infra/apps/`. An entry naming another app or a path outside that
  root is refused.
- **A buildable entrypoint** for the detected runtime: a build script in
  `package.json` for node, a `[project]` table in `pyproject.toml` for python.

Name, port and manifest validity stay the registry's job and are not
duplicated here.

### Verb and gates

`Verb.PUBLISH` joins the enum. `VERB_ROLE[PUBLISH] = Role.ADMIN`, because
publish subsumes source materialization, which is already admin-gated.
`lock_scope` returns `app:<name>`. Publish is not destructive — it adds and
never removes — so no typed confirmation is required.

Every existing gate applies unchanged: the job goes through `OpsService.submit`
like any other verb, so RBAC refusals are audited and the app lock serializes
concurrent publishes of one app.

## Resume by observation

No stage ledger is stored. The two expensive stages are asked whether they are
already done for the commit being published:

| Stage | Answered by |
|---|---|
| register | `apps/<name>/vpath-source.yaml` records this commit |
| send | the payload's own `vpath-source.yaml`, now materialized into the checkout |

This survives an Ops API restart and introduces no second source of truth.

**Render and install are never skipped.** Both are already idempotent in the
engine: an unchanged app rebuilds nothing, because the content hash in
`build.hash.dirs` matches (`07_app_source_delivery.md`), and an app already in
the InstalledSet only has its sync verified (`GitOpsEngine._deploy`). Observing
them would be worse than re-running them — a render present from an *earlier*
commit would make a resumed publish skip the rebuild the new commit needs.

**Resume is keyed to the commit, never to the app name.** A different commit
resets the walk from register, because a stage completed for an older commit
says nothing about this one.

Stage `send` gains one addition: the provenance file travels in the payload
next to the manifest, so the checkout can answer "sent at which commit"
without asking this repository.

## Surfaces

`POST /api/apps/publish` beside the existing app routes:

```json
{"url": "...", "ref": "main",
 "generate": {"name": "...", "port": 0, "base_path": "...", "title": "..."},
 "replace": false}
```

`generate` is omitted for a repository that ships its own manifest, and the
registry refuses it as meaningless if sent anyway — that decision stays in one
place.

The console gains an **Add app** form. Submitting returns a job id; the
existing job panel renders the five stages.

A workstation console points at the box's Ops API through the tunnel:
`tunnel.py`'s argv gains an `-L` port-forward beside the `-D` SOCKS proxy. That
remains configuration-only — no caller input reaches the argv, which is the
boundary that module defends.

## Failure modes

All fail hard, naming the stage and the remedy, per the no-fallbacks rule.

| Condition | Behaviour |
|---|---|
| Preflight finds an escaping dependency path | refuse, naming file and value; nothing written |
| Preflight finds a foreign `hash.dirs` entry | refuse, naming the entry |
| Runtime detected but no buildable entrypoint | refuse, naming what was expected |
| Registration refusal (name, port, manifest) | refuse, unchanged from the registry |
| Send refused (no checkout on this host) | refuse, naming that publish runs on the box's Ops API |
| Render fails in the engine | refuse with the output tail; the checkout diff is left for review |
| ArgoCD does not converge in time | refuse, stating the record was committed and convergence was not observed |

Nothing is rolled back. Rollback is git in the checkout and a normal revert in
the record, both already documented by the units that own them.

## Testing

- `app_preflight`: fixture trees, no network. The `file:../../kit/sdk` tree is
  a golden refusal.
- `publish`: stage doubles. Asserts stage order, asserts an observed-done stage
  is skipped, asserts a failure stops the walk and names its stage.
- **Regression guard**: publishing a tree whose dependency path escapes the app
  must refuse at preflight and write nothing. This is the failure recorded in
  `07_app_source_delivery.md`; the test fails if the gate is reverted.
- Integration: a full walk against `SimulatedEngine`, a temporary checkout and
  a fake Gitea, asserting the five stages and the resulting job record.

## Findings from the real repository (checked 2026-07-31)

`vpathai-git/vpathai_publish_knowledge_app` is INTERNAL, default branch
`main`. Its root is `vpath-platform-app-template` — an npm **workspace root**
(`"private": true`, `"workspaces": ["examples/*"]`), not an app. The apps live
under `examples/`, and the one not yet registered here is
`examples/vpath-knowledge-builder`. Two corrections follow.

### The app is not the repository root

`repo_probe.probe` reads `vpath-app.yaml`, `package.json` and
`pyproject.toml` **at the root**. For this repository the root has no manifest
and a workspace `package.json` with no `scripts.build`, so registration would
refuse it as an app needing a generated manifest — which is the wrong answer,
not a wrong repository.

The registry, the probe and the pipeline therefore need a **path within the
repository**: `PublishRequest.path`, defaulting to `""` (the root). It selects
which directory is the app; provenance records it beside `repo`, `ref` and
`commit`, and the send stage ships that subtree rather than the whole tree.

### The SDK check is exact, not a heuristic

`examples/vpath-knowledge-builder/vpath-app.yaml` declares:

```yaml
  build:
    runtime: node
    hash:
      dirs: [apps_infra/apps/vpath-knowledge-builder, apps_infra/sdk]
    sdks:
      - name: "@vpath/sdk"
        source: apps_infra/sdk
```

and its `package.json` declares `"@vpath/sdk": "file:../../kit/sdk"`.

`spec.build.sdks[]` is the server pipeline's first-class SDK mapping, so both
the second `hash.dirs` entry and the escaping dependency are **expected** —
what is wrong is only the path. The app materializes at
`apps_infra/apps/vpath-knowledge-builder`, from which `../../kit/sdk` resolves
to `apps_infra/kit/sdk`, which does not exist; `../../sdk` resolves to
`apps_infra/sdk`, which is what `sdks[].source` names. That single mismatch is
the recorded build failure, and it is computable:

> For every `spec.build.sdks[]` entry, the `file:` dependency of the same name
> must resolve, relative to `apps_infra/apps/<name>`, to that entry's `source`.

So the two preflight rules are stated exactly:

- **Escaping dependency** — a `file:` path leaving the app tree is refused
  *unless* a `spec.build.sdks[]` entry declares that dependency name, in which
  case the resolved path must equal its `source`. The remedy names both paths:
  "change `file:../../kit/sdk` to `file:../../sdk`".
- **`hash.dirs`** — every entry must be either `apps_infra/apps/<name>` or the
  `source` of a declared SDK. Hashing the SDK is correct: the app must rebuild
  when the SDK changes.

A rule that simply refused every escaping dependency would reject this app for
a reason that is not its bug, and would still not tell the author what to fix.

## Out of scope

Uninstall and rollback of a published app (the existing verbs own both),
publishing automatically on push, publishing to several instances in one
action, and the end state where app repositories build their own images in CI
and the platform only records a digest.
