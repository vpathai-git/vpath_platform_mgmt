# Platform Functions Reference

> **Status: design specification.** The committed function surface of the
> management platform, per decisions 1–15 and the MVP sketch. Everything here
> is testable: each function names its role gate, lock scope, and underlying
> engine call. Until the GitOps cutover (phase 7), engine calls go through
> the temporary Gradle adapter on the shared server — flagged per row.

## The verb set

| Verb | Role | Lock scope | Engine call today | Result |
|---|---|---|---|---|
| `build` | app-dev | `app:<name>` | `./gradlew buildApp -Papp=<name>` | Image built and **pushed to the platform registry; digest returned** |
| `deploy` | app-dev (own apps) | `app:<name>` | `./gradlew redeployApp -Papp=<name>` | App running; health gate result attached |
| `health` | app-dev | none (read) | `health-check-*.sh` gates + HTTPS probes | Structured verdict, persisted on the job |
| `status` | app-dev | none (read) | `bin/vpath status` | Apps, versions, digests, cluster summary |
| `logs` | app-dev (own apps) | none (read) | engine log surface | Streamed job/app logs |
| `uninstall` | app-dev (own apps) | `app:<name>` | `bin/vpath uninstall <app>` | App removed; verified gone |
| `reinstall` | **admin** + typed confirm | `cluster` (exclusive) | `./gradlew goReinstall` | Server reinstalled; full health gate |
| `erase` | **admin** + typed confirm | `cluster` (exclusive) | `goReinstall -Pfull` (eraseInstallation) | Installation erased |
| `invite` | **admin** | none | Ops API native | Single-use onboarding link (see `ACCESS_MECHANISM.md`) |
| `promote` | *reserved* | — | — | Blocked on operator call Q3; not in MVP |

Rules that apply to every verb: RBAC checked per call from validated token
claims; refusals are audited, not silent; no fallbacks — a failed
precondition fails the job with the reason; destructive verbs additionally
require typing the verb name.

## The job model

Every verb invocation (CLI or console) becomes a **job**:

- **Record:** `id, verb, app, requested_by, role, state, step, timestamps,
  log ref, health verdict (if any)`.
- **Lifecycle:** `queued → running → succeeded | failed`. The current step
  is always visible ("gradlew redeployApp", "waiting for rollout", …).
- **Queue semantics (MVP):** single worker on the shared server; jobs with
  disjoint lock scopes run concurrently, same-scope jobs queue in order.
- **Logs:** streamed live to CLI (`vpath logs --job <id>`) and console;
  retained with the job record.

## Locks

| Scope | Taken by | Effect |
|---|---|---|
| `app:<name>` | build / deploy / uninstall | Serializes jobs per app; other apps unaffected |
| `cluster` | reinstall / erase | Exclusive: blocks **all** jobs until released |

Locks are visible (holder, since, job id) in console and `vpath status`.
There is no manual lock API in the MVP — locks exist only as job side
effects, so they cannot leak. A crashed worker releases its locks on
restart by reconciling against live jobs.

## Health model

One definition of "healthy", shared by install, deploy verification and the
console (decision 14): the five engine gates — `infra`, `platform`, `apps`,
`data`, `workflow-ready` — plus HTTPS path probes (landing, Keycloak, Argo
CD, Gitea, Argo Workflows, monitor) and the OIDC discovery endpoint.
`health` returns a single structured verdict listing each check; every
deploy attaches one automatically. History = the job list. Deep/continuous
monitoring stays with the existing `/monitor/` service; the platform links
to it rather than duplicating it.

## Registry contract

The platform registry is the existing in-cluster `registry:2`, reachable
only over the overlay (decisions 10, 15):

- `build` **ends** with "digest pushed to the platform registry".
- `deploy` **begins** with "digest exists in the platform registry" — it
  never builds implicitly.
- Local builds are first-class: push your locally built image to the
  platform registry, then `vpath deploy --digest <sha256:…>`.
- Garbage collection: the engine's existing `gc-images.sh`, scheduled.
- Airgapped exception: image transfer to claas-remote is an Admin-executed
  tarball procedure (documented, audited, rare) — never the routine path.

## Apps, teams, ownership

- `vpath new <app>` scaffolds from the EasyAccess template: app code +
  `vpath-app.yaml` contract + registration with the Ops API. No app repo
  ever contains pipeline code (decision 2 border law).
- Every app belongs to a **team**; membership comes from Keycloak groups.
- "Own apps" for RBAC purposes = apps owned by a team you belong to.
- Registration is idempotent; re-registering updates the contract.

## Audit

Append-only record of: verb invocations (incl. refused ones and their
reason), invite mints and uses, lock acquisitions of cluster scope,
break-glass leases (grant, use, expiry), reinstall/erase confirmations.
Each entry: timestamp, actor, role, action, target, result. Readable by
Admins via console and `GET /audit`; server-devs see a read-only view.

## Surfaces

**CLI** (`pipx install vpath`): the verbs above plus `join`, `login`,
`doctor`, `leave`, `new`. Exit codes are meaningful (0 success, distinct
codes for refused / lock-wait / failed) so CI can consume them.

**Web console** (thin, same API): live job list · deploy form · health
board · lock visibility · app inventory · Admin: invites, server panel,
audit. No console-only capabilities — anything the console does, the API
does.

**Ops API** (v0): `POST /enroll` · `POST /invites` · `POST /jobs` ·
`GET /jobs/{id}` (+ log stream) · `GET/POST /apps` · `GET /health` ·
`GET /locks` · `GET /audit`. OpenAPI schema published by the service;
the CLI and console are its only intended clients until stabilized.

## Explicitly not functions of this platform (today)

Chatbot control (phase 8, propose-only when it comes) · quotas ·
`promote` (operator call Q3) · GitOps authority (arrives with the cutover;
the API then writes desired state to Gitea instead of calling Gradle) ·
direct kubectl/SSH for non-admins · any operation on the airgapped target
beyond the documented Admin runbooks.
