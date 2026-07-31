# Running applications and their pods in the console

Date: 2026-07-31
Status: approved (design), not yet implemented

## Problem

The console can say which applications *exist* (the catalog) and which of them
are *installed* (the InstalledSet). It cannot say what is actually **running**.
An operator looking at a green "Installed" chip has no way to see that the
app's backend pod is crashlooping, or that a user's workflow project was
provisioned at all.

The gap is narrow, because the far half is already built. `ops/argocd.py`
holds an authenticated Kubernetes API client that already reads ArgoCD
Applications and already censuses `kp-<app>-*` project namespaces for the
uninstall guard. What is missing is the near half: listing the pods in those
namespaces and putting them under a toggle in the dashboard.

## Decisions

Four decisions were taken by the operator during design; each is recorded with
the trade-off that was accepted.

1. **Its own section on the Server Dashboard**, not a second toggle on the
   left-nav app rows. Accepted cost: an installed app now appears in two
   places — the nav explorer and the runtime section. The alternative put two
   competing toggles (files, pods) on one narrow 290px row.

2. **Pods from the app namespace *and* every `kp-<app>-*` project namespace.**
   Accepted cost: one extra namespace census per expansion. This is what makes
   a workflow pod visible at all — `spec.workflow.autoProvision` creates those
   pods only inside a per-user project namespace, never in the app's own.

3. **Lazy on expand, re-polled every 5s while open.** Accepted cost: the
   collapsed row shows install state only, not live health. The dashboard's
   own poll is 1s; putting a pod census on it would multiply cluster load by
   the number of installed apps for data nobody is looking at.

4. **Pods are grouped by namespace, not classified as frontend/backend/
   workflow.** Accepted cost: the roles the operator asked for are implied by
   pod name and namespace kind rather than stated. Nothing in this repository
   records which label the server's manifest renderer emits for a component,
   and a guessed label that renders confidently is worse than an absent one.
   Upgrade trigger: an observed `app.kubernetes.io/component` label on the
   real cluster.

## What the cluster corrected (2026-07-31)

Three assumptions in the decisions above were tested against vm5 and two of
them were wrong. Recorded here rather than silently edited, because the wrong
version is the one a reader would otherwise reinvent.

1. **An app's name is not its namespace.** 7 of the 18 installed apps deploy
   somewhere else: `vpath-web` → `vpath-apps-v2`, `vpath-resource-gate` →
   `vpath-platform`, and every `<app>-api` into its frontend's namespace
   (`vpath-agent-chat-api` → `vpath-agent-chat`). The namespace now comes from
   ArgoCD's `spec.destination.namespace`, and an app with no Application says
   its namespace is unknown rather than guessing. This also answers the
   original "frontend pod, backend pod" question: on this installation those
   are two separately installed *apps* sharing one namespace.

2. **The runtime list must come from the InstalledSet, not the catalog.**
   This repo's `apps/` holds 6 apps; the server runs 18; they overlap in
   exactly one (`vpath-explorer`). A section built from the catalog showed
   1/18 of what was running, and hid the only app with a project namespace.
   `/api/apps` now carries `installed_apps`, and an installed app with no
   catalog entry gets a row marked *not in the catalog*.

3. **The Kubernetes token cannot list pods.** Confirmed, not inferred: the
   console runs as `system:serviceaccount:vpath-platform:vpath-mgmt-console`,
   whose ClusterRole `vpath-mgmt-console-read` grants `argoproj.io`
   applications/applicationsets and `namespaces: list` — nothing else. Pods,
   services, deployments, replicasets and events are all denied. This is the
   one open blocker; see *Required cluster grant* below.

## Required cluster grant

The feature needs one verb the console does not have. Least privilege, no
`get`, no `pods/log`, no write:

```yaml
- apiGroups: [""]
  resources: [pods]
  verbs: [list]
```

Two facts about the target make this a decision rather than a chore. The
ClusterRole carries a `kubectl.kubernetes.io/last-applied-configuration`
annotation and no ArgoCD tracking labels, and `grep -r vpath-mgmt-console
/workspace` finds nothing — so the console's own RBAC was applied by hand and
lives in **no** source of truth. Extending it in place perpetuates that;
putting it under version control first is the larger, better change.

## What is shown

A `Running applications` section below the existing `Applications` block on the
Server Dashboard. One row per app that `/api/apps` reports as
`installed === true`; apps whose install state is unknown are listed with that
said plainly, never as "not running".

```
▾ Running applications                    3 of 6 installed
  ▸ ● Explorer Deployment Test                    vpath-explorer
  ▾ ● Workflow Demo                          vpath-workflow-demo
      ┌ application  vpath-workflow-demo                Synced / Healthy
      │  vpath-workflow-demo-6c4d9-nn8x   Running  2/2   0   4d
      └ project      kp-vpath-workflow-demo-klemens
         text-insight-demo-3821-exec      Running  1/1   0  12m
  ▸ ? Fortune Teller                     install state unknown
```

Per pod: name, phase, ready containers, restart count, age. Every field comes
from the Kubernetes API; none is derived or inferred.

## The endpoint

`GET /api/apps/{name}/pods` — read-only, same identity gate as the rest of
`/api/apps`, no role escalation. Pods are cluster state, and every role that
may already list the catalog may see them.

```json
{"app": "vpath-workflow-demo",
 "sync": "Synced",
 "health": "Healthy",
 "namespaces": [
   {"name": "vpath-workflow-demo",
    "kind": "application",
    "pods": [{"name": "vpath-workflow-demo-6c4d9-nn8x",
              "phase": "Running", "ready": "2/2",
              "restarts": 0, "started_at": "2026-07-27T09:12:44Z"}]},
   {"name": "kp-vpath-workflow-demo-klemens",
    "kind": "project",
    "pods": [...]}]}
```

`kind` is `application` for the namespace matching the app's name and
`project` for anything under the `kp-<app>-` prefix — the same prefix
`ArgoClient.app_namespaces` already relies on.

Age is not computed server-side: `started_at` is passed through and the
console formats it. A server-rendered "4d" goes stale the moment it is sent.

## Modules and boundaries

| File | Change | Why here |
|---|---|---|
| `ops/argocd.py` (179) | `+pods(namespace)` | The Kubernetes client already exists; a second HTTP client to the same API with the same token would be the duplication |
| `ops/app_runtime.py` **new** | Shapes raw pod JSON into the response | No network in it, so it is testable from fixtures alone |
| `api/routes_runtime.py` **new** | The route and its capability refusal | `routes_apps.py` is at 184 lines; this keeps both under the limit |
| `api/builders.py` (227) | `+build_runtime_reader(env)` | Same `None`-when-unavailable pattern as `build_publish_pipeline` |
| `api/console.html/.js/.css` | The section and its toggle | `console.js` is at 247 lines — the new code goes in `store.js` (195) or its own file, not into `console.js` |

`ops/argocd.py` returns raw API objects. `ops/app_runtime.py` owns every
decision about shape: which namespaces belong to an app, how a ready count is
derived from `status.containerStatuses`, and what `kind` a namespace has. The
route marshals and refuses; it holds no logic.

## Failure handling

No fallbacks, no soft passes. Three distinct refusals, each naming its own fix:

| Condition | Response | Message |
|---|---|---|
| No cluster configured | 409 | *this console has no cluster connection — pod state requires `VPATH_MGMT_K8S_URL` and `VPATH_MGMT_K8S_TOKEN`* |
| Cluster unreachable or token rejected | 502 | the existing `ArgoError` text, which already distinguishes no-route from refused |
| App not in the InstalledSet | 404 | *`<name>` is not installed, so it has no namespace to read* |

The governing rule: **an unreadable namespace is never rendered as an empty
one.** "No pods are running" and "we could not ask" look identical in a list
and mean opposite things — the same distinction `_catalog_state` already draws
for the platform catalog. A namespace that fails to read carries its error
string into the response and the console shows that string where the pods
would be.

The RBAC of the configured Kubernetes token is not verified by this design. It
already lists namespaces cluster-wide, so pod-list permission is likely but
unconfirmed. If it is absent the failure is a clean 403 from the API surfaced
through the unreachable path above — a visible refusal, not a blank list.

## Testing

- `ops/app_runtime.py`: fixture-driven pytest over shaping — ready counts from
  `containerStatuses`, namespace `kind` assignment, a crashlooping pod's
  restart count, and an app with no project namespaces.
- The empty-versus-unreadable distinction gets its own test: a namespace that
  errors must not serialize as `"pods": []`.
- `ArgoClient.pods`: stubbed `httpx` client, matching
  `test_ops_gitops_clients.py`.
- The route: 409 without a configured reader, 404 for an uninstalled app, 200
  with the expected shape.
- Console JS: string-grep tests, matching the coverage gap already accepted on
  this branch.

Coverage stays at or above 85%; `make check` is the gate.

## Out of scope

Pod logs, `kubectl exec`, pod deletion, and events. This section answers *what
is running*; acting on a pod is a different surface with a different role gate.
