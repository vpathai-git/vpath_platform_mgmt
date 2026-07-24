# Components 1–6 — Carried over from v1 (unchanged decisions)

Condensed from the v1 brainstorm. Full pros/cons tables live in
`ops_isolation_brainstorm_753e62fe.plan.md`; only the decision, the losing
alternatives, and the reasoning that still binds are restated here.

## 1. Overall topology — **Coolify inversion (9/10)**

Alternatives: (B, 5/10) extract full Gradle/`lib/pipeline` into the
management repo and SSH/kubectl at the server; (C, 3/10) stay monorepo and
only document roles.

Decision: the engine runs once on the shared server; clients (CLI, console)
only trigger it through the Ops API. B was rejected because it creates a
second home for the same ~60 scripts and drifts; C fails the design
constraint outright. The "separate project" the prompt asks for is the
**control plane** (API + console + CLI + contracts), not a fork of the build
machinery onto every laptop.

## 2. Pipeline hosting — **A→B staged (8/10 → 7/10)**

Alternatives: (C, 4/10) git submodule/subtree of `lib/pipeline`.

Decision: short term the Ops API wraps today's Gradle verbs on the shared
server (single source of truth stays the server monorepo); medium term the
pipeline is published as a versioned OCI job image consumed by the control
plane. Never submodules — the scripts assume monorepo paths (`lib/vm.sh`,
`apps_infra/apps`). Timing of the A→B switch is now governed by component 7.

Border law (unchanged): server monorepo = platform product; this repo =
management product; app repos = `vpath-app.yaml` + code + published SDK,
never pipeline; deploy authority = GitOps (Gitea→Argo) once live — the Ops
API writes desired state to git and must not become a fourth kubectl
authority.

## 3. Console surface — **Hybrid CLI-first + thin GUI (9/10)**

Alternatives: (B, 5/10) GUI only — weak for hotfix/automation flows;
(C, 4/10) chatbot-first — unsafe for destructive ops, hard to audit;
(D, 7/10) chatbot layered on top later — accepted as phase 2.

Decision: one API, two thin surfaces. The chatbot may *propose*
`deploy/health/uninstall`; destructive actions always route through
confirmed structured forms plus role gates. Verbs v1: `build`, `deploy`,
`health`, `uninstall`, `status`, `logs`; Admin-only: `reinstall`, `erase`.

## 4. Multi-user model — **Teams→Projects→Environments→Jobs + locks (9/10 + 8/10)**

Alternatives: (B, 2/10) shared SSH bastion + honor system; (C, 6/10)
per-developer namespaces without a shared plane — contradicts "one central
server".

Decision: Coolify-shaped hierarchy on the one shared server, with a queue
and locks as the concurrency mechanism: concurrent deploys of *different*
apps allowed; cluster-wide ops (reinstall/erase) take an exclusive lock and
the UI shows who holds it. Identity via the existing Keycloak realm; ops
RBAC is separate from app-level OpenFGA tuples.

Role matrix (binding):

- **App-Entwickler** — create app (EasyAccess), build, deploy to shared env,
  health, uninstall *own* apps, logs. Never needs the server checkout.
- **Administrator** — all of the above + install/reinstall/erase server,
  teams/quotas, promote apps. Break-glass monorepo access allowed.
- **Serverprojekt-Entwickler** — read-only deep diagnostics; write only via
  Admin-approved break-glass lease; clones the monorepo for code analysis,
  not for day-to-day ops.

## 5. EasyAccess — **Template org + scaffolder CLI → register with Ops API (9/10)**

Alternatives: (B, 2/10) monorepo `new-app` — violates isolation; (C, 7/10)
in-console "Create App" wizard — accepted as UX layered on A, not as the
mechanism.

Decision: EasyAccess is a scaffolder + contract + pointer to the shared Ops
API, not another copy of the server. Local test path: standalone sink or a
local K3s *consumer* of the same published base images. Critical-path
prerequisite (named MISSING in the Coolify research): publish the SDKs and
base images to a registry the airgapped server can mirror — see component 10.

## 6. AuthN / target binding — **Keycloak OIDC end-to-end (9/10)**

Alternatives: (B, 3/10) long-lived kubeconfigs for every developer;
(C, 2/10) SSH keys to the deploy VM for everyone — both destroy role
separation and auditability, and C collides with the no-dropper/AV rules.

Decision: console and CLI authenticate via Keycloak (device-code or
short-lived tokens); the Ops API holds the only service account that may
write to the cluster; admin kubeconfigs are never distributed to App-devs.
