# vpath_platform_mgmt

App build/deploy/health-check/uninstall pipeline and admin console for VPath
server instances.

This project isolates the app build/deploy/health-check/uninstall pipeline out
of the main server project into its own repository, and provides a console
(graphical or chatbot-assisted, TBD) for three roles:

- **App developers** — build+test locally, then deploy to an existing server
  instance without needing the server project's own code.
- **Administrators** — install/maintain server instances.
- **Server-project developers** — hotfixes/analysis directly on the server
  project.

None of the first two roles should need to work from within the VPath server
project itself, since that must stay stable.

## Primary goals — the three axes (2026-07-27)

Everything this console does hangs on three axes. This section is deliberately
self-contained: it should make sense to a reader who sees only this repository.

**Background in one paragraph.** A VPATH *platform instance* is one running
installation of the VPATH server platform. Two platform types exist: **server**
(a k3s cluster on a dedicated box or VM — e.g. the on-prem NUC boxes named
`mercury8`/`venus10`, the Azure VM `terra`) and **standalone** (a local
Electron-shell process, NATO-alphabet names `alpha`, `bravo`, …). Instance
*data* (hosts, users, keys) is a gitignored local register; the *mechanism*
around it is versioned here — see `src/vpath_platform_mgmt/instances/`
(registry, selector, transport, probe) and `analysis/instance-management/`.

### Axis 1 — Dualism: one view over both platform types

We manage server AND standalone platforms. The console renders a **generic
view** that both types share — status, apps, state, operations — plus the
**type-specific panels** that only one side has (examples: stack status and
load for servers; login and size-on-disk for standalones), plus an **OntoGate
link** per instance/app: it points at the OntoGate UI server, which serves the
OntoGate view of the respective project (server, standalone, app/workflow
specific) where one exists — a missing view is shown honestly as missing.

### Axis 2 — Instances: CRUD + health

Instances are created from **versioned type templates** — `nuc`, `standalone`,
and `remote` (the win-claas variant: a customer-side Windows cluster) — while
the resulting instance entries themselves stay gitignored payload. Every
instance can be created, updated, health-checked; the console shows error
logs, uptime, state and history. The register must answer, per instance:
where does it live (host + filesystem)? where does its build process live?
which source repositories does the build pull apps from? where do the
container images live?

### Axis 3 — Apps: CRUD + health

Every app can be built, deployed, undeployed and updated (forcefully if
needed). Apps have versions that may coexist side by side. **Iteration 1
target:** an existing in-server app (e.g. the Explorer app) is manageable from
here as an isolated app. The console offers manifest inspection and visibility
for the app's frontend part, backend part, its workflow templates, and for
**bundles** — app + workflow templates as one package.

**MVP scope (decided 2026-07-27):** the three axes above, targeted for the end
of this week. Five further dimensions are validated but deliberately
**backlog, post-MVP**: (a) platform lifecycle — install/upgrade/rollback/
uninstall/backup-restore of the platform stack itself on an instance; (b) app
catalog & compatibility — what can be picked, which app version runs on which
platform version (the pin chain is that truth), including the transport path
onto air-gapped boxes; (c) tenancy — Keycloak users, SSH access, roles;
(d) data lifecycle — what happens to an app's persisted data on undeploy and
update; (e) security upkeep — CVE-driven base-image waves, certificate and
secret rotation. Detail: `analysis/mgmt-console/summary.md`.

Derivation and open points: `analysis/mgmt-console/summary.md`.

The full concept, roles, and open questions live in the Jira task — that is the
source of truth:
**[EIP-222 · Server Stabilisierung und Administration](https://vpathai-team-l8xgdmtm.atlassian.net/browse/EIP-222)**

**Coding agents:** your contract is [`AGENTS.md`](AGENTS.md) (Claude Code
loads it via `CLAUDE.md`).

## Related repositories

- **Server project** — <https://github.com/vpathai-git/vpath_server>
- **Platform App Template** — <https://github.com/vpathai-git/vpath_platform_app_templ>

## Quick Start

### Prerequisites

- Python 3.10 or higher
- pip, git
- [Trivy](https://trivy.dev/latest/getting-started/installation/) — the
  mandatory dependency CVE scanner (`brew install trivy` on macOS)

### Installation

```bash
git clone https://github.com/vpathai-git/vpath_platform_mgmt.git
cd vpath_platform_mgmt
make setup                      # venv, git hooks, CVE toolchain check
source venv/bin/activate        # Windows: venv\Scripts\activate
make install-dev
```

### Running the console

The console drives exactly one platform instance, named on the command line.
`--instance vm5` loads the gitignored `.env.vm5` profile beside this README —
copy `.env.console.example` to create one. Naming the instance is deliberate:
silently guessing which box a console talks to is the most expensive mistake
this tooling can make.

```bash
vpath-console --instance vm5    # http://127.0.0.1:8765
vpath-console                   # no profile: simulated engine, no real box
```

Everything it reaches — Gitea, the Kubernetes API, Keycloak — sits inside the
platform's private network, so a real instance also needs that network
reachable (on the box, or through the operator's SSH tunnel; the console
offers a **Start tunnel** button for the one failure that fixes).

### Running the CLI

Same gates, same service layer, no console:

```bash
vpath doctor                    # layered reachability; prints the first fix
vpath status                    # engine, recent jobs, held locks
vpath app add github.com/org/repo --ref main
vpath deploy <app>
```

`vpath --help` lists the rest. The CLI and the console cannot disagree: every
gate lives in the service layer, never in a command or an endpoint.

The `vpath-platform-mgmt` entry point is still the template's placeholder and
prints a greeting; the real surfaces are the two above.

## Documentation

| Read this | When |
|---|---|
| [`docs/ADDING_AN_APP.md`](docs/ADDING_AN_APP.md) | turning an organization's repository into a running app |
| [`docs/PLATFORM_FUNCTIONS.md`](docs/PLATFORM_FUNCTIONS.md) | which verb exists, its role gate and lock scope |
| [`docs/USER_ACCESS.md`](docs/USER_ACCESS.md) | what a user may do, and how they get in |
| [`docs/ACCESS_MECHANISM.md`](docs/ACCESS_MECHANISM.md) | how that access actually works, and why it is safe |
| [`docs/INSTANCES.md`](docs/INSTANCES.md) | what an instance is and how one is registered |
| [`context/CHECKLIST.md`](context/CHECKLIST.md) | finishing a change: the done/commit/release gate |
| [`docs/superpowers/specs/`](docs/superpowers/specs/) | why a design is the way it is, with the trade-off accepted |

Docs marked *design specification* describe intent; `ADDING_AN_APP.md` is
marked *implemented* and its values were checked against the code.

## Development

The full quality gate (identical to CI) runs before every commit via the
activated pre-commit hook:

```bash
make check      # black + flake8 + mypy + pytest (coverage >= 85%)
make scan       # dependency CVE gate (Trivy; blocks CRITICAL/HIGH)
make format     # apply black formatting
```

Versioning follows [SemVer](https://semver.org/) with a
[Keep a Changelog](https://keepachangelog.com/) `CHANGELOG.md`. The canonical
done/commit/release checklist is `context/CHECKLIST.md`.

## Template Lineage

This project was stamped from `vpath_empty_project` (`main` flavor); the
stamped template commit is recorded in `.template-version`. It is a fresh,
pristine stamp — no intentional divergences from the template yet. Check for —
and pull in — template improvements at any time:

```bash
python3 scripts/check_template_drift.py            # read-only drift report
python3 scripts/sync_from_template.py              # dry-run upgrade plan
python3 scripts/sync_from_template.py --apply      # copy new + update pristine
```

OntoGate adoption is recommended once a real domain model develops — see
`context/RECOMMENDED_WAYS_OF_WORKING.md` and the `/ontogate` skill.

## License

This project is licensed under the terms in the LICENSE.TXT file.
