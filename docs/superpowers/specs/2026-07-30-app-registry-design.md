# Registering app repositories for deployment

Date: 2026-07-30
Status: approved (design), not yet implemented

## Problem

App repositories now arrive regularly, and each one has to become an entry the
console lists and the server can be sent. Today that path does not exist: the
only way in is to hand-write a manifest into `apps/<name>/`, and the only way
out is a manual tar upload.

The gap is narrow, because the far half is already built. `ops/source.py`
(decision 16) materializes app source into `apps_infra/apps/<name>/` on the
server checkout, is paranoid about traversal and symlinks, is admin-gated, and
already refuses an upload that carries no `vpath-app.yaml`. What is missing is
the near half: turning a git URL into a registered, describable app.

The first repository offered — `vpathai_publish_knowledge_app` — is the ADK
kit rather than an app and carries no manifest of its own. That case is the
normal case, not an exception, so the design must answer it directly.

## Decisions

Three decisions were taken by the operator during design; each is recorded
with the trade-off that was accepted.

1. **`apps/<name>/` holds a manifest and a pointer, not vendored source.**
   Source is fetched from git at send time, so what ships is always a named
   commit. Accepted cost: sending needs network access to the repository.

2. **A repository without a manifest gets one generated here.** Accepted cost:
   the app's manifest then has two possible homes and they can disagree. This
   is mitigated, not ignored — see *Manifest origin* below. The alternative
   (refuse, and emit a skeleton to commit upstream) was considered and
   declined for speed of onboarding.

3. **CLI first, console afterwards, over one shared module.** The registry is
   a library; the CLI and the later console action are both thin callers, so
   the behaviour cannot fork between them.

## Design

Four units, each with a single responsibility.

### `ops/repo_fetch.py`

Given a repository URL and a ref, produce a shallow checkout in a temporary
directory and report the resolved commit sha. It wraps `git clone --depth 1`
through an injected runner, so tests assert on argv and never reach the
network. It knows nothing about applications, manifests or the catalog.

No clone caching: a shallow fetch is cheap, and a stale cache would report a
commit that is not what would ship.

### `ops/app_registry.py`

The only unit that writes `apps/<name>/`. It produces exactly two files.

`vpath-app.yaml` — upstream's file when the repository has one, byte for byte;
otherwise generated (see below).

`vpath-source.yaml` — provenance:

```yaml
repo: https://github.com/org/repo.git
ref: main
commit: 08f7f9e8c753a2ad2f71ecea43dabbc5ac58b0eb
manifest_origin: upstream | generated
added_at: 2026-07-30T09:12:00Z
```

Public surface: `register(...)`, `refresh(name)`, `entries()`.

### CLI

`vpath app add <url>`, `vpath app refresh <name>`, `vpath app list`. Thin
shells over the registry, so a batch of repositories is a shell loop. Added to
the existing typer CLI.

### Send leg

`vpath app send <name>` fetches the **commit recorded in provenance**, packs a
tar, and posts it to the existing source endpoint. `ops/source.py` is not
modified: it already enforces every guard that matters, including the presence
of a manifest in the upload.

That endpoint materializes into a server checkout, so it only answers on a
console configured with `VPATH_MGMT_SERVER_CHECKOUT` — in practice a console
running on the box. Sending from a workstation console reports that as its
reason rather than failing obscurely; registering, listing and refreshing work
anywhere, because they touch only this repository.

## Manifest generation

Generation happens only when the repository ships no manifest. When it ships
one, its `metadata.name` names the app and every flag below is rejected as
meaningless — the manifest is taken as authored.

When generating, these are required and refused rather than defaulted:
`--name`, `--port`, `--base-path`, `--title`.

Derived, never asked for: `metadata.namespace` and `spec.image` and
`spec.auth.oidcClient` all take the app name; `spec.health.readiness` and
`spec.health.liveness` are `<base-path>/api/healthz` with `scheme: HTTPS`;
`spec.build.hash.dirs` is `apps_infra/apps/<name>`.

`spec.build.runtime` is detected from the repository — `package.json` implies
node, `pyproject.toml` implies python. When both or neither are present,
detection is ambiguous and the command refuses, requiring `--runtime`.

`spec.ui.description` defaults to empty and `spec.ui.icon` to `box`; both are
cosmetic and editable afterwards. `spec.ui.sidebar` is `true`.

A generated manifest is parsed through the existing `AppCatalog` before it is
written. The console can therefore never be handed a file it cannot read.

## Manifest origin, and why it matters

`manifest_origin` is what keeps decision 2 from rotting. `refresh` re-fetches
the recorded ref and, if upstream has since gained its own `vpath-app.yaml`,
adopts it and rewrites `manifest_origin: upstream`. A generated manifest is
therefore always visibly provisional, and an app repository can take ownership
of its own manifest at any time without anyone remembering to delete our copy.

Upstream always wins on refresh. A locally generated manifest is never
preferred over one the app repository ships.

## Failure modes

All fail hard with a message naming the specific cause, per the repository's
no-fallbacks rule:

| Condition | Behaviour |
|---|---|
| Repository unreachable or ref absent | refuse, naming URL and ref |
| Generating without `--port` / `--base-path` / `--title` | refuse, listing every missing flag at once |
| Runtime not detectable and `--runtime` absent | refuse, naming what was found |
| App name already registered | refuse unless `--replace` |
| Port already claimed by another manifest | refuse, naming the app that holds it |
| Generated manifest fails `AppCatalog` parsing | refuse, write nothing |

Port collisions are checked across every manifest the catalog can see. Ports
are never auto-assigned: silently choosing a free port is how two apps come to
fight over one later.

## Testing

- `repo_fetch`: injected runner, asserts argv and the shallow-clone flags; no
  network in any test.
- `app_registry`: a fake fetcher supplies trees. Covers upstream-manifest
  adoption, generation golden file, every refusal in the table above, and
  `refresh` adopting a manifest that appeared upstream.
- Integration: `AppCatalog` parses a generated manifest and the console's
  `/api/apps` lists it with its provenance.
- Regression guard: registering a repository without a manifest and without
  the required flags must fail; that is the ADK case that started this.

## Out of scope

Building or deploying the app on the server (the existing engine verbs own
that), the console UI action (same module, later), clone caching, automatic
port assignment, and any change to `ops/source.py`.
