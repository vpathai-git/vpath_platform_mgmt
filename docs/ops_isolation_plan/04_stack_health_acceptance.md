# Components 13–14, Acceptance Criteria, Operator Calls

## 13. Tech stack for Ops API / CLI / console

v1 sketched `src/api`, `src/cli`, `src/web` but never chose a stack. This
repo is a Python template with hard gates (85% coverage, 250-line files,
`make check`), which is itself a fact to weigh.

| Option | Weight | Pros | Cons |
|---|---|---|---|
| **A. Python: FastAPI (Ops API) + Typer (CLI) + deliberately thin web UI — server-rendered Jinja/htmx or a small static bundle (recommended)** | **8/10** | Fits the already-initialized template and its test/coverage gates; team context is Python-heavy; first-class OIDC libs for the Keycloak flow; async job endpoints natural in FastAPI; harness support exists (fastapi-reviewer) | Rich GUI work is weaker in Python-land — acceptable only while the GUI stays thin; long-running jobs need an explicit worker model (queue + subprocess runner), not request-scoped execution |
| B. TypeScript: NestJS/Express API + React console | 5/10 | Richest GUI ecosystem; one language across web surface | Abandons the template's wired gates; new toolchain to govern; nothing in the verified environment suggests a JS-fluent ops team; node absence on claas-remote hosts complicates any engine-side reuse |
| C. Go: single static binary serving API + embedded UI, cobra CLI | 5/10 | One-binary distribution is elegant for a CLI+API tool; strong SSH/concurrency stdlib | New language for the team; slower iteration during a phase that is all iteration; template mismatch means rebuilding all quality gates |

**Recommendation: A.** The reasoning: the console's value is verbs, RBAC,
locks, and auditability — none of which need a rich frontend, and the v1
console decision (component 3) already committed to "thin GUI". Choosing the
stack the repo template already enforces means the quality gates
(coverage, file size, CVE scan) apply from commit one instead of being
re-plumbed; that is worth more than React's widget ecosystem for a job list
and a confirm-form. The one real risk in A — job execution — is addressed by
structure, not framework: an in-process queue table + worker loop in the
MVP, swappable for a real queue when quotas demand it. Revisit only if the
GUI scope grows beyond job list / deploy form / health board / confirmations
(that would be a scope alarm before it is a stack alarm). Suggested layout
stays inside the template: `src/vpath_platform_mgmt/{api,cli,jobs,web}/`.

## 14. `health` verb design

The prompt names health-checking as first-class; v1 lists the verb but no
design. Verified surface today: five `health-check-*.sh` gates
(infra/platform/apps/data/workflow-ready) in `lib/pipeline/`, `bin/vpath
status`, the §4.3 HTTPS path table, and the OIDC discovery probe.

| Option | Weight | Pros | Cons |
|---|---|---|---|
| **A. Aggregate existing signals server-side: Ops API `health` runs the `health-check-*` gates via the engine + probes the URL table, returns one structured verdict; results persisted per job (recommended)** | **8/10** | Zero new infrastructure; reuses the exact gates the install already trusts (PhaseGate semantics); server-side probing works across NAT/airgap where a laptop cannot reach; history for free via job records | Point-in-time, no alerting; gate scripts become an API dependency — their output needs a stable, parseable format (small engine-side change) |
| B. Monitoring stack: Prometheus/blackbox exporter + dashboards + alerts | 5/10 now | Continuous history, alerting, SLO-grade | Heavy for an MVP; a Monitor service already exists at `/monitor/` — building a second one duplicates it; alerting is nobody's stated requirement yet |
| C. Client-side probes: CLI hits the URL table directly | 4/10 | Trivial to build; no server dependency | Asymmetric reachability (client often cannot see what the server sees, especially airgapped); logic duplicated across CLI and GUI; no shared history |

**Recommendation: A, with `/monitor/` linked for depth; B deferred until
someone asks for alerting.** The reasoning: health for these roles answers
"did my deploy work and is the platform sane," which is a point-in-time,
on-demand question — precisely what the existing install gates already
compute. Wrapping them keeps one definition of "healthy" shared between
installation, deploy verification, and the console, instead of three
drifting ones. Persisting each result on the job record turns the same call
into a cheap timeline. The only engineering cost worth naming is making the
gate scripts emit machine-readable output — a small, non-breaking engine
change that also benefits GitOps post-sync hooks later.

## Acceptance criteria per delivery phase

Each phase of v1's plan gains a testable exit criterion derived from the
role stories. A phase is done when its criterion passes, not when its code
merges.

| Phase | Exit criterion |
|---|---|
| 1. Contract freeze | Demand + spine expressions reviewed; "no fourth deploy authority" and deviations 1–3 (README) signed off by operator |
| 2. Ops API MVP | An authenticated `deploy` + `health` of a sample app succeeds on the primary target with the server monorepo checkout absent from the calling machine |
| 3. CLI redirect | **The isolation criterion:** an App-Entwickler with no clone of `vpath_server` can build, deploy, health-check, and uninstall their own app end-to-end via `vpath` CLI |
| 4. Thin GUI | A second user watches the first user's running job live; `reinstall` is refused without Admin role + typed confirmation; lock holder visible |
| 5. EasyAccess | A Temakollege goes from nothing to an app deployed on the shared server using only the template repo, the CLI, and the onboarding doc |
| 6. Engine extract + bootstrap bundle | `vpath bootstrap <target>` installs a fresh server from a pinned release artifact on a clean VM; developer machines need no monorepo for any verb |
| 7. GitOps cutover | The temporary `redeployApp` adapter is deleted; deploys flow only via Gitea→Argo; the adapter's removal breaks no acceptance test above |
| 8. Chatbot (optional) | Chatbot can propose but not execute destructive verbs; audit log attributes every action to a human confirmation |

## Operator calls — restated with what they block

1. **Primary shared target** (component 11 recommends NUC) — blocks: registry
   exposure (10), bootstrap runbook target (8), Ops API listen address,
   EasyAccess defaults, VPN/onboarding doc.
2. **Must App-devs build fully offline, or is "local = standalone +
   published images" enough?** — blocks: scope of EasyAccess local path
   (component 5) and whether the CLI needs an offline `build` at all. The
   plan assumes the latter; a "fully offline" answer pulls engine extraction
   (7) forward.
3. **Who promotes shared-dev → production channel?** — blocks: the `promote`
   verb's RBAC (component 4) and whether claas-remote installs are Admin-only
   ceremonies or a pipeline stage.

These three plus the deviation sign-offs are one `/decide-next` session.
