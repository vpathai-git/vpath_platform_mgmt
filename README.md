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

### What of this runs today (2026-07-28)

| Axis | State |
|---|---|
| 1 — dualism | **Built.** One generic view (status, uptime, apps, state, operations) over all four instance kinds, plus type-specific panels and the per-instance OntoGate link — `src/vpath_platform_mgmt/console/`. |
| 2 — instances | **Built.** Versioned type templates (`nuc`, `cloud-vm`, `standalone`, `remote`) with create/update/remove against the gitignored register — `src/vpath_platform_mgmt/instances/`. |
| 3 — apps | **Not started.** The console reports apps as unmanaged and names the issue that changes it. Iteration 1 (Explorer extracted and deployed) needs the server monorepo plus a live instance. |

Two things are deliberately *not* guessed and are visible as such in the
console. **Uptime is not measured yet** — the decided figure is "platform
services healthy since", which no probe computes today. And the `remote`
(win-claas) type is reachable but **not permitted**: its access path was
surveyed against the server project on 2026-07-28 and is established (SSH,
key-based, no jump host), but what the console may do on a customer production
system is an operator decision no repository can answer. So `CONSOLE_PERMITTED`
stays open, the transport refuses that kind outright, and the probe measures
nothing. Knowing how to reach a machine is not permission to touch it.
Detail: `analysis/mgmt-console/remote-type-survey.issue.md`.

### Running the console

```bash
python -m vpath_platform_mgmt.console.api view          # register only
python -m vpath_platform_mgmt.console.api view --probe  # measure now
python -m vpath_platform_mgmt.console.api templates     # the type templates
```

The same commands with `--json` are exactly what the Electron shell consumes;
the shell renders that payload and holds no logic of its own.

```bash
make console-install    # once: the shell's Node dependencies
make console            # run the shell from this checkout
```

### Building distributables

```bash
make dist            # both halves
make dist-python     # wheel + sdist  -> dist/
make dist-console    # console binary -> src/vpath_platform_mgmt/console/electron/dist/
```

The console binary is a **renderer, not a self-contained application**: it
spawns a Python interpreter that must have `vpath-platform-mgmt` installed —
which is what the wheel is for. Point `VPATH_PYTHON` at that interpreter if it
is not the default `python3`/`python`. Running from a checkout needs no install
at all; the shell puts `src/` on `PYTHONPATH` itself.

A packaged build has no repository next to it, so it reads its register from
`<userData>/instances.local.env` unless `VPATH_INSTANCES_FILE` says otherwise.

`electron-builder` does not cross-compile between platforms — run
`make dist-console` on each platform you want an artifact for.

Creating an instance goes through a template rather than an editor — the
template decides which fields exist and which are mandatory, and the edit is
kept only if the resulting register still parses:

```bash
python -m vpath_platform_mgmt.console.api create mars --template nuc --set SSH_HOST=... --set SSH_USER=... --set CHECKOUT=...
```

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
