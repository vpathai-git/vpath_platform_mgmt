# Components 10–12 — Artifact Contract, Primary Target, Sensitivity

## 10. Artifact / registry contract ("bereits gebaute Apps deployen")

The prompt's App-Entwickler story is build-and-test *locally*, then install
that app on the shared server — and the Kernanforderung says already-built
apps get deployed *systematically*. v1's flow is build-from-git via the
server-side engine and never defines where a locally built image lives so
the server can pull it. Verified reality: the shared server already runs an
in-cluster `registry:2` on `REGISTRY_PORT` (`lib/pipeline/setup-registry.sh`,
GC via `gc-images.sh`); Gitea hosts image *sources*, not containers.

| Option | Weight | Pros | Cons |
|---|---|---|---|
| **A. The existing in-cluster `registry:2` is the contract: `deploy` takes an image reference resolvable there; local builds push to it first (recommended)** | **8/10** | Already deployed, bootstrapped, and GC'd — zero new services; on-cluster, so it works inside the airgap; GitOps digest pins resolve locally; one freshness authority | `registry:2` has no native auth/UI — exposing it to laptops needs an authenticated ingress route (Ops API–issued pull/push tokens) before multi-user use; capacity on a NUC-class box needs the GC tuned; claas-remote laptops may not reach even the exposed port |
| B. External managed registry (GHCR/ACR) mirrored inward | 5/10 | Robust, familiar tooling; good fit for the Azure `vm5` class; offloads storage | The airgapped CLAAS host cannot pull from it — a mirror pipeline becomes mandatory; adds an external dependency to "one central server"; Azure egress/firewall problems are already documented for these clusters |
| C. Image tarball transfer (`docker save` → scp → `k3s ctr images import`) | 4/10 alone, 7/10 as airgap adjunct | Works absolutely everywhere including claas-remote; zero new services; the pattern already exists in `setup-registry.sh`'s own bootstrap | No digest authority, no GC, manual and unscalable; unauditable side-channel if it becomes the normal path |

**Recommendation: A as the contract, C documented as the claas-remote
fallback, B only if the team ever goes Azure-primary.** The reasoning: the
registry the plan needs *already exists* — the missing 20% is reachability
and auth, which is exactly the Ops API's job: the `build` verb ends with
"image pushed to the platform registry, digest returned", the `deploy` verb
begins with "digest exists in the platform registry", and the API issues
short-lived push tokens so the bare `registry:2` never faces the network
naked. That single contract line also resolves the EasyAccess prerequisite
(component 5): base images and SDK images are published into the same
registry. C stays a documented, Admin-executed escape hatch because an
airgapped target will always need a sneakernet path — but making it explicit
and rare keeps it from becoming an invisible parallel pipeline.

## 11. Primary shared target ("everyone uses one central server")

v1 deferred this as operator call #1 and called it non-blocking. It is
blocking: registry exposure (10), Ops API reachability, EasyAccess defaults,
and the bootstrap runbook (8) all differ per target.

| Option | Weight | Pros | Cons |
|---|---|---|---|
| **A. NUC (the shared physical team box) as the daily shared dev/deploy instance (recommended)** | **8/10** | LAN-reachable by the team; build host == deploy host, the simplest topology; existing `.env.nuc` overlay and `VPATH_INSTALL_MODE=nuc` path is battle-tested; physical control, no cloud cost | Single box — quotas/locks (component 4) carry real load; LAN address means remote teammates need VPN; capacity ceilings on registry + concurrent builds |
| B. claas-remote (airgapped enterprise host) | 5/10 | Production-like; where the product ultimately must run; enterprise placement pleases stakeholders | Airgap + AD-prefixed logins kill self-service DX; no npm/node on the host, builds must happen elsewhere and transfer in; every console iteration fights the transfer path — as the *daily* shared server it would slow all three roles |
| C. `vm5` (Azure VM class) | 6/10 | Reachable from anywhere without VPN; disposable — reinstall practice already exists (2026-07-21 report); good CI target | Running cost; documented Azure firewall trouble (LLM endpoints); public exposure demands hardening the Ops API on day one; "central server the team trusts" is weaker on a box that gets erased |

**Recommendation: A — NUC as the shared instance; claas-remote remains the
production-like target that Admins exercise; vm5 stays the disposable
integration target.** The reasoning: the prompt's center of gravity is DX
("Temakollegen direkt in der Umgebung Apps erstellen") and iteration speed;
the NUC is the only target where the whole loop — push image, deploy, health,
logs — happens on one LAN-local box with an already-proven env overlay.
Choosing the airgapped box as the daily server would import its friction
into every developer's day, which is precisely what this project exists to
remove; instead the airgap stays an Admin-run *installation exercise*
(components 8 + 10's tarball path) so production-likeness is still
validated. Consequences to pin in config, not prose:
`VPATH_MNGMT_TARGET=nuc` as default, registry ingress on the NUC, VPN note
in the onboarding doc. Decisions unblocked by this call: 10 (registry
exposure), 8 (which runbook is primary), EasyAccess defaults, and the
Ops API's listen address.

## 12. Connection-contract sensitivity (what may live in git)

v1's §4 puts internal hostnames, public/private IPs, an AD username, and SSH
usernames into a bundle destined for this repo's README — no secrets, but
infrastructure-recon data, and irreversible the moment the repo is shared.

| Option | Weight | Pros | Cons |
|---|---|---|---|
| **A. Split: architecture/roles/verbs public in `docs/`; hosts, users, IPs in gitignored `docs/CONNECTION.local.md` + `config/targets.yaml`; committed `config/targets.example.yaml` with placeholder stubs (recommended)** | **9/10** | Repo stays shareable (EasyAccess will be shown around); constitution-aligned (nothing identifying leaves the machine via git); example stubs keep onboarding one-copy-away; schema for targets is still versioned | Two places to maintain; onboarding gains a "fetch the local file from the team vault" step; drift between example and real file possible — mitigate with a startup validation that fails loud on placeholder values |
| B. Everything in the repo README (v1 default) | 3/10 | One paste, fully self-contained onboarding | AD usernames + internal hostnames + IPs become recon data on first share/fork; un-publishing from git history is practically impossible; violates the spirit of the no-secrets rule even though no credential is technically present |
| C. Everything in the wiki / password manager only | 5/10 | Maximum secrecy; single team-managed location | Repo docs become non-actionable; config schema and reality drift apart with no validation; every automation needs out-of-band setup anyway |

**Recommendation: A.** The reasoning: the useful, stable part of v1 §4 is
its *shape* — which env vars exist, the URL path table, where secrets live —
and shape is safe to commit; only the *bindings* (which host, which user)
are sensitive, and they are exactly the part that belongs in per-operator
config anyway because they differ by target. Committing the schema plus a
validating loader (fail hard on missing/placeholder values, per the
template's no-silent-fallback rule) gives the onboarding convenience B
promises without B's irreversibility. This supersedes v1's "paste §4 into
README" todo; the v1 plan file itself should stay uncommitted or be
scrubbed the same way.
