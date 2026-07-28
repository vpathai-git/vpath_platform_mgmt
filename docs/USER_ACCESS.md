# Accessing the Platform as a User

> **Status: design specification.** Describes the target behavior defined in
> `docs/ops_isolation_plan/` (decisions 1–15) and delivered by MVP milestones
> M0–M3 (`06_mvp.md`). Commands are the committed interface; they do not work
> yet. Acceptance bar: invite → deployed app in **under 10 minutes**.

## Who you are determines what you see

| Role | You can | You cannot |
|---|---|---|
| **App-Entwickler** | Create apps, build, deploy, health-check, view logs, uninstall **your own** apps | Touch other teams' apps; SSH to the server; run reinstall/erase; see admin panels |
| **Administrator** | Everything above, plus: invite teammates, reinstall/erase the server, manage teams, first-time installs | — |
| **Serverprojekt-Entwickler** | Read-only diagnostics: status, health, logs across all apps | Any write verb, unless an Admin grants a time-boxed break-glass lease |

You never need: a VPN config, SSH keys, a kubeconfig, or a checkout of
`vpath_server`. If a workflow seems to require one of those, that is a bug in
the platform, not a step you missed.

## First-time access (from a fresh laptop)

**1. Get invited.** An Administrator sends you a single link. It is bound to
your team and role and expires (default 24 h). Nothing else arrives — no
password, no key file.

**2. Register.** The link opens the VPath Keycloak registration page. Create
your account (or sign in via SSO if configured). Because the invite carries
team + role, your account lands in the right groups automatically — there is
no follow-up ticket.

**3. Connect.** The success page shows exactly one command:

```bash
pipx install vpath && vpath join <code>
```

`vpath join` does four things you never see: logs you in (OIDC device flow —
your browser opens once), exchanges the invite code for a **single-use,
role-scoped enrollment key**, installs and configures the network overlay
client for your OS, and verifies it can reach the server. When it prints
`connected — nuc.vpath.internal reachable`, you are done.

**4. First deploy.**

```bash
vpath new my-app        # scaffold from the EasyAccess template
cd my-app
vpath deploy            # build + ship; prints console URL + your app's HTTPS endpoint
```

## Day-to-day access

- **CLI:** `vpath build | deploy | health | status | logs | uninstall`.
  Sessions use short-lived tokens; when one expires the CLI tells you and
  `vpath login` renews it in one browser round-trip.
- **Web console:** `https://nuc.vpath.internal` — job list (live), deploy
  form, health board, lock visibility ("who is deploying what right now"),
  and for Admins the invite and server panels. Same login as the CLI.
- **Both surfaces are thin.** Every action is a job in the same queue with
  the same RBAC and the same audit trail, so CLI and console never disagree.

Concurrency you will notice: deploys of *different* apps run in parallel;
two jobs on the *same* app queue behind a per-app lock; server-wide actions
(reinstall) take an exclusive lock — the console shows who holds it and
since when.

## Access as Administrator

Everything above, plus:

- `vpath invite --team <t> --role <r>` (or the console button) mints invite
  links. Every invite is audited: who invited whom, when, into what role.
- `vpath reinstall` / `vpath erase` require your Admin role **and** typing
  the verb name to confirm. They take the exclusive cluster lock.
- First-time installation of a brand-new server machine is the one flow that
  uses the server checkout, on the install side only — follow
  `docs/INSTALL_RUNBOOK.md` (decision 08; runbook lands with milestone M4).

## Access as Serverprojekt-Entwickler

Your default surface is read-only: `vpath status`, `vpath health`,
`vpath logs <app>`, and the console's diagnostics views across all apps.
For a hotfix that needs write access, an Administrator grants a
**break-glass lease** — time-boxed, audited, and revoked automatically at
expiry. For code analysis you still clone `vpath_server`; for operations you
never need to.

## When something fails

Run `vpath doctor` first. It checks in order — overlay up → server
reachable → login valid → API healthy — and prints the exact fix for the
first failing step, e.g.:

| Symptom | Doctor says | Fix |
|---|---|---|
| Any command hangs/timeouts | `overlay down` | Start the overlay client it names; or `vpath join` again |
| `401` on any verb | `token expired` | `vpath login` |
| `refused: requires role …` | RBAC working as intended | Ask an Admin if you believe your role is wrong — the refusal is audited either way |
| `lock held by <user>` | Not an error | Wait, or coordinate; the console shows the running job |

## Leaving

`vpath leave` deregisters your device from the overlay. When you leave the
team, an Administrator disables your Keycloak account — that single action
revokes console, CLI, API, and network access together. There are no
per-user keys left behind on any server.
