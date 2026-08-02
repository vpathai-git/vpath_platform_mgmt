# The instance register, the selector and the status probe

Every VPATH environment — a k3s box or a local Electron standalone — is
declared once, in one gitignored file, and driven from here. This document is
the schema and the boundary; the working template is
[`instances.example.env`](../instances.example.env).

## The two halves

| Tracked in this repository | Never tracked |
|---|---|
| the schema (this file) | your addresses, users, key paths |
| the template `instances.example.env` | your `instances.local.env` |
| the mechanism (`src/vpath_platform_mgmt/instances/`) | the boxes themselves |

Verify the second column stays out:

```bash
git check-ignore -v instances.local.env      # .gitignore:99:instances.local.*
```

## The boundary — the one rule that keeps this small

**The register says *where* an environment is and *from where* it is driven.
It never says *how* anything is built, installed or deployed.**

The *how* is the server project's pipeline and stays there. Concretely: the
register names an env profile (`config/dot_env/.env.<profile>` in the checkout
on the box) and nothing out of it. The platform port, the workspace path and
the build target directory are read from that profile at the moment they are
needed. Copying one of them into the register would create a second home for a
value that already has one, and the two would drift — silently, because both
would still look right.

That is why the server field list is as short as it is:

```
<NAME>_KIND  <NAME>_SSH_HOST  <NAME>_SSH_USER  <NAME>_SSH_KEY
<NAME>_ENV_PROFILE  <NAME>_CHECKOUT
```

## Schema

`KEY=VALUE`, one per line. `#` starts a comment **only at the start of a
line** — the same posture as the server's `config/dot_env` profiles, which are
guarded against inline comments for the same reason. `~` and `$HOME` are
expanded in path fields. A line that is neither blank, nor a comment, nor an
assignment is an error, not a line quietly dropped.

`VPATH_INSTANCES` lists every instance, whitespace-separated. Fields are
prefixed with the upper-cased instance name.

| Field | Kinds | Meaning |
|---|---|---|
| `KIND` | all | `server-nuc`, `server-cloud-vm` or `standalone` |
| `LIFECYCLE` | all | `live` (default) or `planned` — named, not built yet |
| `NOTES` | all | one line of free text |
| `SSH_HOST` | server | address the dev machine connects to |
| `SSH_USER` | server | login user on the box |
| `SSH_KEY` | server | private key path; omit for the ssh default |
| `SSH_KEY_SOURCE` | server | where to extract the key from, if it is not there yet |
| `SSH_ALIAS` | server | `~/.ssh/config` alias, informational |
| `ENV_PROFILE` | server | drives `./gradlew -Penv=<profile>` |
| `CHECKOUT` | server | server checkout **on the box**: delivery target and Gradle cwd |
| `SOURCE_CHECKOUT` | server | server checkout **on this machine**: where `deliver` reads the commit from. Required for `deliver` |
| `APP_ROOT` | standalone | app repository carrying the Electron shell |
| `HOME` | standalone | `VPATH_STANDALONE_HOME` — runtime state, keys, KPs |

Fields required for a kind are enforced when the register is read. A
`LIFECYCLE=planned` instance is exempt: its coordinates cannot be known before
it exists.

### Naming — two classes

Server environments carry planet names in acquisition order (`mercury8`,
`venus10`, `terra`, then `mars`, …); the numeric suffix is the NUC generation,
a cloud VM has none. Standalone environments carry NATO alphabet names
(`alpha`, `bravo`, …). Decided 2026-07-27; the earlier `terra12` reservation
for a NUC was withdrawn in the same decision.

## The selector

```bash
python -m vpath_platform_mgmt.instances.selector list
python -m vpath_platform_mgmt.instances.selector show mercury8 [--mask]
python -m vpath_platform_mgmt.instances.selector exec  mercury8 -- uptime
python -m vpath_platform_mgmt.instances.selector gradle venus10 -- deployPipeline
python -m vpath_platform_mgmt.instances.selector deliver terra --sha <sha>
```

`gradle` resolves to exactly one line on the box:

```
cd <CHECKOUT> && ./gradlew -Penv=<ENV_PROFILE> <your args>
```

`--print` shows that line instead of running it — worth using before anything
that changes a box.

`deliver` is the server README's own delivery channel (use case 4b): push the
commit into the box's checkout over SSH, then fast-forward **only** there. The
push and the merge are chained; a failed push never leaves the merge to run.

Both ends of that push come from the register: the commit is read from
`SOURCE_CHECKOUT` (`git -C`) and lands in `CHECKOUT` on the box. That is why
the call behaves identically from any working directory. Before, it resolved
the sha against the process working directory, so following the runbook line —
`cd .../vpath_platform_mgmt && … selector deliver …` — died with
`fatal: bad object <sha>` / `remote unpack failed`, and only a shell that had
already `cd`-ed into the server checkout worked. A register without
`SOURCE_CHECKOUT` aborts with exit `2` naming the field; it never falls back to
the working directory.

Exit codes: `0` ran and succeeded · `1` ran on the instance and failed there ·
`2` could not be established (no register, unknown name, missing key,
unreachable, an action the kind cannot do). There is no default instance: an
unknown name aborts.

## The status probe

```bash
python -m vpath_platform_mgmt.instances.probe [--instance mercury8]
```

Per server instance, in one SSH round trip, all of it read-only:

| Reported | Read from |
|---|---|
| running | deployments ready, `k3s kubectl get deploy -A` |
| platform | the platform's own `/api/version` answering |
| version | `build_id` out of that answer |
| last install | mtime of `<CHECKOUT>/<TARGET_DIR>/phase-gates/platformReady.marker` |
| image sha | the `vpath.git.sha` label the build stamps onto an image |
| checkout | `git -C <CHECKOUT> rev-parse HEAD` |

The probe does **not** run the pipeline's `health-check-platform-ready.sh`: it
is a Gradle-orchestrated gate wanting the full environment, and it *touches the
phase-gate marker*. A status tool must not mutate what it measures.

A missing `vpath.git.sha` label means **not establishable**, never unhealthy —
images built before labelling was introduced simply do not carry one.

### What a standalone cannot tell you

The Electron shell allocates every port through `allocatePort()` → `listen(0)`.
A running standalone therefore has **no address knowable from outside**. The
probe reads what it can — process presence, `runtime/state.db` mtime,
`kit/VERSION` — and reports health and running version as *named gaps*. It does
not guess, and it does not report the gap as "down".

Exit codes: `0` all live instances healthy · `1` one answered and is unhealthy ·
`2` a fact could not be established · `3` the register no longer describes
reality (a `planned` instance that exists, a box running something other than
its checkout). Precedence `2 > 1 > 3 > 0` — a run that could not look is not a
run that found nothing.

## Related

- `analysis/instance-management/` — why the register looks like this
- `analysis/instance-status/` — why the probe judges the way it does
- server: `README.md` use case 4b (delivery), `config/dot_env/README.md` (profiles)
