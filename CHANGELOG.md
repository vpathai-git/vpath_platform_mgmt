# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html):
breaking changes bump MAJOR, new features bump MINOR, fixes bump PATCH.
The version lives in `pyproject.toml` (source of truth) and is mirrored in the
package `__init__.py` `__version__` — bump both together (see
`context/CHECKLIST.md`, Gate 3).

## [Unreleased]

## [0.2.0] - 2026-08-10

### Added
- Ops control plane: the platform verbs (deploy, uninstall, health-check,
  publish) behind one guarded service with engine adapters and a job runner —
  one state, two surfaces, the `vpath` CLI and the console.
- GitOps engine: deploy and uninstall are commits against the instance's ops
  repository rather than commands fired at a cluster; ArgoCD reads the result
  and the console reads it back.
- Ops console: Server Dashboard and Application Explorer, a connection badge
  that names the instance and probes its reachability, and an Applications
  view that lists both catalogs — ours and the platform's — with install state
  in both directions.
- Publish pipeline: a repository URL walks to a running application in five
  delegated stages. `vpath app add` registers a repository by asking GitHub, so
  INTERNAL repositories work; `vpath app send` ships it at its recorded commit
  and sends provenance with the source.
- Preflight: a repository whose SDK path is not where its manifest says is
  refused before anything is written; an application may be a directory inside
  its repository.
- Instances: one register, one selector, one status probe, and a tunnel that
  forwards the box's Ops API port.
- Authentication: Keycloak token validation, device-flow login for the CLI,
  browser sign-in over PKCE through a split-route relay, authorization by realm
  group.
- Credential gate (`make credentials`, part of `make check`): no credential
  value may reach a console, a log or a tracked file.
- Docs: installing and connecting the console
  (`docs/INSTALLING_THE_CONSOLE.md`), and how a repository becomes an app
  (`docs/ADDING_AN_APP.md`).

### Changed
- Python floor raised to `>=3.11.4` — the fleet standard is 3.11, and 3.11.4 is
  where `tarfile.extractall(..., filter=...)` lands on that line. CI matrix,
  classifiers, black target versions and mypy language level follow.
- Console wording is sentence case throughout, and the engine badge is gone:
  the connection badge already says what it said.
- Publish guards, publish stages, job execution, the publish route, the tarball
  download and the environment-config builders each moved out of the module
  that had grown around them.

### Fixed
- The delivery push carries the register's SSH key, and `deliver` resolves the
  source commit from the register instead of the process working directory.
- Publish validates its input, refuses a silent overwrite, never strands its
  lock, and renders network and parse failures instead of swallowing them.
- An absent namespace is not an empty one and `Succeeded` is not a failure; the
  pod namespace is derived from ArgoCD, and only the pods an app owns are
  listed.
- A dead console backend explains itself instead of going quiet.
- The Keycloak relay was configured backwards and said so misleadingly; the
  device flow sends PKCE, as the realm client requires.
- Registration refuses an unsafe path instead of sanitising it, and describes a
  refused register line without echoing it.
- Ports are validated with `int()` rather than `isdigit()`, so every
  non-numeric value is caught.
- Cross-platform: the instance registry and selector suites run on Windows, and
  the completion-chime asset resolves on every platform.

## [0.1.0] - 2026-07-24

### Added
- Initialized from the `vpath_empty_project` template (commit `0390b41`):
  src-layout package, pytest suite, the strict CI gate
  (black/flake8/mypy/pytest with a coverage floor), the dependency CVE gate,
  and the agent governance under `.claude/` and `context/`.
