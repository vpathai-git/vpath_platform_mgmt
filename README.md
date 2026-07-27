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

### Running the Placeholder Module

```bash
vpath-platform-mgmt             # console script
python -m vpath_platform_mgmt   # as a module
make run                        # via make
```

Prints a placeholder greeting — replace with real code.

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
