# Installing the Console and Connecting It

> **Status: implemented.** Getting from a clone to a console driving a real
> instance. Per-setting detail lives in `.env.console.example`, which is the
> reference for every key; this document is the sequence, and the map from
> symptom to fix. For what to do once connected, `ADDING_AN_APP.md`.

## First decide where the console runs

This one choice determines everything below. The console is a local process
that talks to a remote platform; it is never installed *into* the cluster.

| Position | Engine | Reaches the box by | Can publish? |
|---|---|---|---|
| **On the box** (`/workspace` beside the checkout) | `local` or `gitops` | localhost | yes |
| **Workstation, through the tunnel** | `gitops` | SSH SOCKS proxy | only with a checkout |
| **Nothing at all** | `simulated` | — | no |

`simulated` is the default and needs no configuration, no box and no
credentials. Start there to see the surface; nothing it reports is real.

Publishing needs **both** halves — a server checkout to render from and the
Deploy-of-Record to install into. A console with only one declines at the
verb rather than half way through.

## Install

Prerequisites: Python 3.11+, git, and — for publishing — the GitHub CLI `gh`,
already authenticated for the organizations you will read (`gh auth status`).
Repositories are read through `gh` rather than cloned, so its authentication
is what reaches private and INTERNAL repos. [Trivy](https://trivy.dev) is
required for `make scan`.

```bash
git clone https://github.com/vpathai-git/vpath_platform_mgmt.git
cd vpath_platform_mgmt
make setup                      # venv, git hooks, CVE toolchain check
source venv/bin/activate        # Windows: venv\Scripts\activate
make install-dev
```

`httpx[socks]` is a declared dependency, so proxy support arrives with the
install — nothing extra to add for the tunnelled case.

## Create the instance profile

The console refuses to guess which box it drives: naming the instance is the
one thing it will not infer, because a console silently pointed at the wrong
box is the most expensive mistake this tooling can make.

```bash
cp .env.console.example .env.vm5   # gitignored; never commit a filled one
vpath-console --instance vm5       # http://127.0.0.1:8765
```

Read `.env.console.example` while filling it in — each key carries the reason
it exists, including three that are counter-intuitive and have each cost real
debugging time (browser issuer origin, JWKS URL, and which side
`KC_PROXY_PUBLIC` names). Real environment variables still win over the file,
so a one-off override on the command line works.

A profile that does not exist is an error, not a fallback to simulated. Being
handed a simulation when you asked for a real instance is exactly the failure
the check prevents.

## What the box must provide

### Two tokens

The Deploy-of-Record (Gitea) and the cluster (Kubernetes API) are separate
doors with separate credentials, and they fail for different reasons in
different places. Both go in the profile, which is gitignored.

Mint the Kubernetes one from the ServiceAccount the console runs as:

```bash
kubectl -n vpath-platform create token vpath-mgmt-console --duration=8760h
```

Never paste a token into a commit, a log, an issue or a chat. `make check`
runs a credential scan that fails the build if one reaches a tracked file.

### A ServiceAccount with the right to read

That ServiceAccount and its ClusterRole are defined in the **server** repo at
`platform_infra/kubernetes/mgmt-console/rbac.yaml` and applied by
`deploy-platform.sh`. The console reads and never writes, so the role is
read-only:

| Resource | Verbs | Used for |
|---|---|---|
| `argoproj.io` applications, applicationsets | get, list | reconciliation state, the cascade guard |
| namespaces | list | finding `kp-<app>-*` project namespaces |
| pods | list | the *Running applications* view |

Without `pods: list` everything else still works and the pods section says it
was refused. Verify what the token may actually do:

```bash
kubectl auth can-i list pods --as=system:serviceaccount:vpath-platform:vpath-mgmt-console -A
```

## Connect from a workstation

`10.0.0.4` has **no** route from a workstation. The operator's script opens an
SSH SOCKS proxy on `127.0.0.1:1085`; `ALL_PROXY` in the profile is what points
the console's HTTP clients through it. Without it every call hangs until it
times out — roughly 21 seconds of looking broken for no stated reason.

With `VPATH_MGMT_SSH_HOST`, `_USER`, `_KEY` and `_TUNNEL_PORT` set, the
console's **Start tunnel** button opens the proxy itself. It is offered only
for a routing failure, because that is the only failure it fixes — an expired
token is the same red badge and a different problem.

The tunnel is a plain `ssh -D`, so it can also be run by hand:

```bash
ssh -i <key> -D 127.0.0.1:1085 -N -o ExitOnForwardFailure=yes <user>@<host>
```

`Address already in use` means an earlier tunnel still holds the port; find it
before opening another, or the new one exits while the old one keeps working
and the two are easy to confuse.

## Verify, in this order

Each step tells you which layer failed, so stop at the first one that does.

```bash
vpath doctor        # overlay -> api reachable -> auth valid -> engine mode
```

Then open the console and read the badge in the header:

- **Connected · vm5** — both doors answered.
- **Unreachable** — the console runs, the box does not answer. The detail line
  names which door and why.
- **Disconnected** — the console's own backend is gone; nothing to do with
  the box.

Finally, confirm it sees real state: *Running applications* should list what
the server actually runs, and expanding an app should show its pods.

## When it does not work

| Symptom | Cause | Fix |
|---|---|---|
| Every call hangs ~21 s | no route to `10.0.0.4` | start the tunnel; set `ALL_PROXY` |
| Badge red, detail says no route | tunnel died | **Start tunnel**, or re-run `ssh -D` |
| Badge red, detail says token rejected | Gitea or k8s token expired | mint a new one; the detail names the door |
| Sign-in fails with "Failed to fetch" | opened on a different origin than `VPATH_MGMT_OIDC_BROWSER_ISSUER` | open the console at exactly that address — `localhost` and `127.0.0.1` are different origins |
| Valid sign-in rejected, WinError 10060 | `VPATH_MGMT_OIDC_JWKS_URL` points at the platform | point it at the console's own relay; PyJWT fetches keys with urllib, which ignores SOCKS |
| Discovery hands the browser unreachable endpoints | `VPATH_MGMT_KC_PROXY_PUBLIC` set to the console's address | it is **Keycloak's** public address, the URL form Keycloak emits |
| `dev` auth refused at startup | header-trust auth with a real engine | use `VPATH_MGMT_AUTH=oidc` |
| Pods section shows a 403 | ClusterRole lacks `pods: list` | apply the server repo's `mgmt-console/rbac.yaml` |
| Publish declines at the verb | only one half configured | publishing needs a checkout **and** the Deploy-of-Record |
| An app's namespace looks wrong | it is not the app's name | it comes from ArgoCD's `spec.destination.namespace`; on vm5 that differs for 7 of 18 apps |

## What never goes in a profile you share

`.env.<instance>` holds live credentials for a platform. It is gitignored, and
the pre-commit credential scan is the backstop, not the rule. When pasting
console output anywhere, check it carries no token: the console is built to
keep secrets off screen, but a shell transcript is not.

```yaml
validated: 2026-07-31
review_horizon_days: 180
```
