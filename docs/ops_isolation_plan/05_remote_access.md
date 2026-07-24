# Component 15 — Easy Access: Self-Service Registration & Connection

The requirement (from the original prompt's EasyAccess ask): a Temakollege
must be able to **register, get connected, and use the platform** — easily.
The tunnel is not the product; the onboarding flow is. Success is measured
in minutes-to-first-deploy, and the user never learns what WireGuard is.

## The target flow (invite → deployed app, under 10 minutes)

1. **Invite.** An Admin clicks "Invite teammate" in the console (or runs
   `vpath invite --team <t> --role app-dev`). Out comes a single link, bound
   to team, role, and an expiry.
2. **Register.** The link opens Keycloak self-registration (or SSO). Because
   the invite carries team + role, the account lands in the right groups
   automatically — no admin follow-up, no ticket.
3. **Connect.** The success page shows exactly one command:
   `pipx install vpath && vpath join <code>`. The `join` command performs the
   OIDC device-flow login, calls `POST /enroll` on the Ops API, receives a
   **single-use, role-scoped tunnel enrollment key**, silently installs and
   configures the overlay client, and verifies reachability. The user typed
   one command; the tunnel happened to them.
4. **Build & deploy.** The same terminal now works:
   `vpath new my-app` scaffolds from the EasyAccess template,
   `vpath deploy` ships it, and the command prints the console URL and the
   app's HTTPS endpoint.

Every step is revocable at one place: disable the Keycloak account and both
the ops rights and the network path die with it.

## Options for the onboarding UX

| Option | Weight | Pros | Cons |
|---|---|---|---|
| **A. Invite link + one-command CLI join (`vpath join <code>`) (recommended)** | **9/10** | One command from zero to connected; tunnel enrollment fully automated via Ops-API-issued single-use keys; invite carries team/role so RBAC is set before first contact; same flow on every OS; auditable (who invited whom, when) | The CLI must handle per-OS overlay-client install; the `/enroll` endpoint and invite management are real MVP scope |
| B. Web-portal onboarding with downloadable preconfigured installer | 6/10 | No CLI needed to start; friendly for non-terminal users | Per-OS installer bundles to build and keep current; more steps than one command; app work needs the CLI anyway, so the portal only delays it |
| C. Documented manual onboarding (admin creates account, user installs VPN by hand) | 2/10 | Zero build cost | Exactly the friction being complained about; error-prone; every new teammate costs admin time; keys outlive people |
| D. No tunnel at onboarding — expose console/API/registry publicly behind auth | 5/10 | Absolute simplest first contact: register, open URL, done; nothing to install | The platform becomes a public attack surface guarded only by app auth; registry push through public proxies hits body-size limits; SSH for Admins needs a second mechanism anyway; contradicts keeping the NUC unexposed |

**Recommendation: A, with B's portal page as the invite landing page (it
shows the one command), and D reconsidered later for console-read-only
viewers.** The reasoning: the flow is only "easy" if registration and
connectivity are **one** motion. Option A is the only one where the thing
that makes tunnels painful — key exchange and client configuration — is
executed by software holding a scoped, expiring credential, not by a human
following a wiki page. B alone still ends in the CLI, so it adds a detour
rather than removing one. C is the status quo this component exists to kill.
D trades the team's security posture for a convenience A already delivers.

## Transport underneath (implementation detail, not the product)

The enrollment-key mechanism decides the transport: it must support
programmatic, single-use, group-scoped enrollment. Both candidates do —
**NetBird self-hosted** (setup keys; OIDC against the existing Keycloak
realm; control plane on the vm5-class VPS) or **Tailscale** (auth keys;
managed control plane; per-user pricing). Preference: NetBird for the single
identity authority and self-hosted control plane; Tailscale as the drop-in
managed fallback. Role groups mirror the role matrix: `app-dev` reaches
console/API (443), registry (`REGISTRY_PORT`), platform HTTPS
(`VPATH_PORT`); `admin` additionally SSH (22); `server-dev` HTTPS with SSH
only via a time-boxed break-glass group. The airgapped claas-remote target
is out of tunnel scope entirely (components 8, 10). A tunnel grants
reachability only — authorization stays in Keycloak + Ops API RBAC
(components 4, 6); network access must never imply ops rights.

## Ongoing ease (after day one)

- `vpath doctor` checks the overlay first and prints the exact fix when the
  server is unreachable, instead of failing deep inside a deploy.
- CLI and console address the server by its stable overlay DNS name
  (e.g. `nuc.vpath.internal`), never a LAN IP — identical config for local
  and remote users.
- Leaving is as clean as joining: `vpath leave` deregisters the device;
  disabling the Keycloak account revokes everything else.

## Acceptance criterion (sharpens phase 5)

A Temakollege with a fresh laptop and an invite link reaches a deployed app
on the shared server in **under 10 minutes**, with **no admin involvement
after the invite** and **without ever editing a VPN or SSH config**.
