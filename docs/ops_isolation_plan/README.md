# Ops Isolation Plan v2 — Full Decision Map

Builds out the v1 handoff bundle (`ops_isolation_brainstorm_753e62fe.plan.md`,
main-repo root) into a complete, argued decision map. v1's six components are
carried over unchanged; nine new components close the gaps found in review:
a silent requirement deviation, the first-time-install bootstrap hole, the
repo-name mismatch, the missing artifact/registry contract, the deferred
target choice, connection-contract sensitivity, the undecided tech stack, the
undesigned `health` verb, and multi-user remote access over tunneling — plus
per-phase acceptance criteria.

Format everywhere: alternatives, weighted pros/cons, one recommendation with
reasoning. Weights are /10 for fit with the design constraint ("no role must
operate from inside the server project") and the realities verified in the
repos on 2026-07-24.

## Decision index

| # | Component | Recommendation | Weight | File |
|---|-----------|----------------|--------|------|
| 1 | Overall topology | Coolify inversion — engine on shared server, clients trigger | 9/10 | [01](01_carryover_decisions.md) |
| 2 | Pipeline hosting | A→B staged: wrap today's Gradle, later versioned job image | 8/10 | [01](01_carryover_decisions.md) |
| 3 | Console surface | Hybrid CLI + thin GUI; chatbot phase-2 | 9/10 | [01](01_carryover_decisions.md) |
| 4 | Multi-user model | Teams→Projects→Environments→Jobs + locks | 9/10 | [01](01_carryover_decisions.md) |
| 5 | EasyAccess | Template + scaffolder CLI → register with Ops API | 9/10 | [01](01_carryover_decisions.md) |
| 6 | AuthN / binding | Keycloak OIDC; no kubeconfig for App-devs | 9/10 | [01](01_carryover_decisions.md) |
| 7 | Pipeline extraction timing | Keep staged extraction, but as a signed-off deviation with a defined trigger | 8/10 | [02](02_pipeline_bootstrap_naming.md) |
| 8 | First-time install bootstrap | Documented Admin runbook now; bootstrap bundle at engine-extract time | 8/10 | [02](02_pipeline_bootstrap_naming.md) |
| 9 | Repo naming | Adopt `vpath_platform_mgmt` (reality); retire `vpath-server-mngmt` | 8/10 | [02](02_pipeline_bootstrap_naming.md) |
| 10 | Artifact / registry contract | Existing in-cluster `registry:2` as the deploy contract; tarball path for airgap | 8/10 | [03](03_artifacts_targets_sensitivity.md) |
| 11 | Primary shared target | NUC for shared dev; claas-remote stays the production-like Admin target | 8/10 | [03](03_artifacts_targets_sensitivity.md) |
| 12 | Connection-contract sensitivity | Split: architecture public, hosts/users gitignored + example stubs | 9/10 | [03](03_artifacts_targets_sensitivity.md) |
| 13 | Tech stack | Python: FastAPI + Typer CLI + deliberately thin web | 8/10 | [04](04_stack_health_acceptance.md) |
| 14 | Health verb design | Aggregate existing PhaseGate/health-check scripts + URL probes via Ops API | 8/10 | [04](04_stack_health_acceptance.md) |
| 15 | Remote access / tunneling | WireGuard mesh overlay (NetBird on the VPS, wired to Keycloak); Tailscale fallback | 9/10 | [05](05_remote_access.md) |

Acceptance criteria per delivery phase and the restated operator calls (with
what each one blocks) are in [04](04_stack_health_acceptance.md).

## Deviations from the original request (require sign-off)

1. **"Build-Pipeline in ein separates Repository isolieren"** is NOT done in
   v1 of the build. The engine stays in the server monorepo until the
   extraction trigger fires (component 7). What ships instead is isolation of
   *operation*: no role needs the server checkout to build/deploy/health/
   uninstall. Approve or veto explicitly — this is the plan's largest
   reinterpretation of the prompt.
2. **CLI added** although the prompt asked "grafisch oder chatbot-gestützt".
   Rationale in component 3: scriptability for CI and Serverprojekt-Entwickler.
   The GUI remains the primary surface for Temakollegen.
3. **Chatbot deferred to phase 2** rather than being a v1 option (component 3,
   destructive-op auditability).

## Verified facts this plan relies on (checked 2026-07-24)

- `vpath_server/lib/pipeline/` exists with ~60 scripts, including
  `setup-registry.sh`, `gc-images.sh`, and five `health-check-*.sh` gates.
- The shared server runs an in-cluster `registry:2` on `REGISTRY_PORT`
  (bootstrapped by `setup-registry.sh`); Gitea hosts image *sources*, it is
  not the container registry.
- `bin/vpath` is the current ops surface; no console exists.
- This repo is `vpath_platform_mgmt`, initialized from `vpath_empty_project`
  (Python template, 85% coverage gate, 250-line file rule).

## Next actions (supersedes v1 todo list)

1. Operator answers the three calls in [04](04_stack_health_acceptance.md)
   and signs off the deviations above (suited to a `/decide-next` session).
2. Rename pass: `vpath-server-mngmt` → `vpath_platform_mgmt` across the v1
   bundle before any of it is pasted into this repo (component 9).
3. Split-paste the v1 handoff: architecture/roles/verbs into `docs/`,
   connection tables into gitignored local docs (component 12) — this
   replaces v1's "paste §4 into README" todo.
4. Capture OntoGate demand + impact-sim against `install_deploy` /
   `gitops_deploy` spines (unchanged from v1).
5. Scaffold Ops API MVP per component 13; verbs per v1 §5.
