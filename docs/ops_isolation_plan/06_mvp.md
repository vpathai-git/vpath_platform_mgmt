# MVP Sketch — The Smallest System That Passes Three Tests

Synthesis of the recommended option from every component (1–15). The MVP is
not "a bit of everything"; it is the minimum build that makes these three
tests pass, in order:

| Test | Source | Statement |
|---|---|---|
| **T1** | Phase 2 | An authenticated `deploy` + `health` of a sample app succeeds with no server checkout on the calling machine |
| **T2** | Phase 3 (isolation criterion) | An App-Entwickler with no clone of `vpath_server` builds, deploys, health-checks and uninstalls their own app end-to-end |
| **T3** | Component 15 | A Temakollege with a fresh laptop and an invite link reaches a deployed app in under 10 minutes, no admin involvement after the invite, never editing a VPN or SSH config |

## Architecture (MVP-concrete)

```text
Laptop (any OS)                    vm5-class VPS              NUC (shared server)
┌─────────────────┐               ┌──────────────┐           ┌──────────────────────────┐
│ vpath CLI (Typer)│──overlay────▶│ NetBird mgmt │◀─overlay──│ netbird client           │
│ browser → console│              │ (OIDC ↔ KC)  │           │ Ops API (FastAPI)        │
└─────────────────┘               └──────────────┘           │  ├─ SQLite: jobs/locks/  │
        │  OIDC device flow                                  │  │   invites/audit       │
        ▼                                                    │  ├─ worker → subprocess  │
   Keycloak realm (existing, on NUC) ◀───────────────────────│  │   ./gradlew …, bin/…  │
                                                             │  ├─ thin web (Jinja/htmx)│
                                                             │  └─ /enroll → setup keys │
                                                             │ registry:2 (existing)    │
                                                             │ k3s + engine (existing)  │
                                                             └──────────────────────────┘
```

Decisions applied: Coolify inversion (1) — the API lives beside the engine on
the NUC; temporary Gradle adapter (2); CLI + thin web (3); locks + audit (4);
EasyAccess template v0 (5); Keycloak everywhere (6); no extraction yet (7);
Admin runbook for first install (8); this repo, this name (9); existing
`registry:2` reached **only via the overlay** — no public ingress, ACLs gate
push access, API-issued registry tokens deferred (10, 15); NUC as target
(11); bindings gitignored (12); FastAPI + Typer + Jinja/htmx (13); `health`
wraps the five existing gates (14); invite → `vpath join` onboarding (15).

Job execution: a single in-process worker consumes a SQLite-backed queue and
runs the engine verbs as local subprocesses on the NUC (build host ==
deploy host, so no SSH hop, no dropper pattern, no paramiko).
`# ponytail: SQLite + single worker; upgrade trigger: concurrent job volume
or a second server instance.`

## Surfaces

**CLI (`pipx install vpath`):** `join <code>` · `login` · `new <app>` ·
`build` · `deploy` · `health` · `status` · `logs` · `uninstall` · `doctor` ·
`leave`. Admin: `invite --team --role` · `reinstall` · `erase` (both with
typed confirmation + exclusive lock).

**Ops API (v0):** `POST /enroll` (invite code → single-use, role-scoped
overlay setup key) · `POST /invites` (Admin) · `POST /jobs` → 202 + id ·
`GET /jobs/{id}` + log stream · `GET/POST /apps` (register from scaffold) ·
`GET /health` (aggregate verdict) · `GET /locks` · `GET /audit` (Admin).

**Web console (thin):** job list with live status · deploy form · health
board · invite management · lock holder visibility. No SPA framework; pages
are server-rendered, htmx for the live bits.

**Data model:** `users` (Keycloak subject mirror) · `teams` · `apps` (owner
team) · `jobs` (verb, app, state, requested_by, log ref) · `invites` (code,
team, role, expiry, used_at) · `locks` (scope, holder, acquired_at) ·
`audit_events` (who, verb, target, result, timestamps).

**RBAC map (verb → minimum role):** all verbs → `app-dev` (own apps only);
`reinstall`/`erase`/`invite` → `admin`; `server-dev` = read-only `status` /
`health` / `logs` / diagnostics, writes only via Admin-approved lease.

## Milestones — each gated by a measurable exit

| # | Name | Scope | Exit test |
|---|---|---|---|
| M0 | Wire | NetBird mgmt on VPS with OIDC against the existing Keycloak; NUC joined; role groups + ACLs; overlay DNS name | A remote laptop passes `vpath doctor` (overlay up, console URL reachable, OIDC discovery OK) |
| M1 | One verb | Ops API skeleton + worker; `deploy` + `health` of one sample app; CLI `login`/`deploy`/`health` | **T1** |
| M2 | All verbs + locks | `build`/`uninstall`/`status`/`logs`; per-app locks; audit log; web job list + deploy form + health board | **T2** |
| M3 | Onboarding | `POST /invites` + `/enroll`; `vpath join`; `vpath new` from EasyAccess template v0 (one example app, `vpath-app.yaml` contract) | **T3**, stopwatch-measured |
| M4 | Admin hardening | `reinstall`/`erase` behind typed confirmation + exclusive lock; break-glass lease for server-devs; install runbook doc (component 8) | Phase-4 criteria: second user sees live job; `reinstall` refused without Admin + confirmation; lock holder visible |

Sequencing note: M0 has no code dependency on M1–M4 and de-risks the
environment first; everything after M0 is testable remotely from day one.

## Explicitly out of MVP scope

Engine extraction and the bootstrap bundle (7, 8-B — wait for the trigger) ·
GitOps cutover (the Gradle adapter stays, flagged temporary) · chatbot ·
monitoring stack (link `/monitor/`, wrap gates only) · registry tokens and
public ingress (overlay ACLs suffice until then) · quotas · `promote` verb
(blocked on operator call Q3) · web-portal installers (15-B) · any
claas-remote flow beyond the Admin runbook.

## Safety rules the MVP inherits (non-negotiable)

No dropper pattern on remotes; no Python/paramiko for remote SSH; no silent
fallbacks — fail hard with a clear message; destructive verbs = Admin role +
typed confirmation + exclusive lock; secrets never in git — bindings live in
gitignored config validated at startup (component 12).
