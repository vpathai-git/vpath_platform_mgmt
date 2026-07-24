# Component 15 — Multi-User Remote Access / Tunneling

The NUC recommendation (component 11) stands or falls with reachability: the
box sits on a LAN, remote Temakollegen do not. "Multi-user access" here has
two layers that must not be conflated:

- **Authorization** is already decided: Keycloak OIDC (component 6) + Ops API
  RBAC and locks (component 4). Nothing at the network layer may grant ops
  rights.
- **Reachability** is what tunneling solves: who can open a TCP connection to
  which port. The tunnel is a doorbell, never a badge.

What each role must be able to reach on the shared server:

| Role | Needs reachable | Never gets |
|---|---|---|
| App-Entwickler | Ops API/console (443), registry push (`REGISTRY_PORT`), platform HTTPS (`VPATH_PORT`) | SSH, kubectl |
| Administrator | All of the above + SSH (22) | — |
| Serverprojekt-Entwickler | HTTPS surfaces, read-only diagnostics | SSH except via time-boxed break-glass |

The airgapped claas-remote target is explicitly out of tunnel scope — it is
reached by Admins on-site/enterprise-network only (components 8, 10).

| Option | Weight | Pros | Cons |
|---|---|---|---|
| **A. WireGuard mesh overlay — NetBird self-hosted on the vm5-class VPS, wired to the existing Keycloak realm; Tailscale SaaS as the managed fallback (recommended)** | **9/10** | No port forwarding or public exposure of the NUC (NAT traversal); one client covers HTTPS, registry push, and SSH; NetBird accepts any OIDC IdP, so login is the same VPath Keycloak account — one identity authority end-to-end; network ACL groups map 1:1 onto the three roles; control plane runs on infrastructure the team already owns | A client install on every device; self-hosting the coordination server is one more service to operate (mitigated: it lives on the VPS, not on the NUC, and Tailscale remains the zero-ops fallback) |
| B. Identity-aware HTTPS publish — Cloudflare Tunnel + Access, or the NetBird reverse proxy / Pangolin on the VPS | 6/10 (7/10 as phase-2 addition) | Zero client install — browser-only access to console and API; only HTTP(S) surfaces ever leave the LAN | HTTP(S) only: SSH and kubectl need a second mechanism anyway; registry pushes break on free-tier body-size limits (~100 MB per upload) — large image layers fail; Cloudflare Access adds a second identity layer unless OIDC-federated back to Keycloak; a third party sits in the data path |
| C. Classic WireGuard server + router port-forward | 4/10 | Zero third parties; minimal moving parts; cheap | Needs a stable public IP/port-forward on a home-grade LAN (CGNAT risk); manual key lifecycle — offboarding a teammate means touching the server, the exact multi-user weakness; no SSO tie-in |
| D. SSH bastion / reverse tunnel via the vm5 VPS (`ssh -J`, autossh) | 3/10 as target, 6/10 as stopgap | Works today with existing assets and zero new software | Per-user SSH keys to shared boxes were already rejected in component 6 (no role separation, no audit, AV rules); long-lived reverse tunnels are fragile; every user gets network-level access far beyond their role |

**Recommendation: A — with B as an optional phase-2 convenience, never as
the primary path.** The reasoning: the decisive property is that the overlay
carries *all three* protocols the roles need (HTTPS, registry, SSH) under
*one* login, and that login can be the Keycloak account the platform already
issues — no second identity system, which options B and C both smuggle in.
NetBird self-hosted keeps the control plane on team infrastructure (the
vm5-class VPS is already paid for) and its ACL groups become the network
mirror of the role matrix: `role:app-dev` reaches 443 + `REGISTRY_PORT` +
`VPATH_PORT`, `role:admin` additionally 22, `role:server-dev` HTTPS only
with SSH granted via a time-boxed break-glass group. If operating the
coordination server proves more friction than it is worth, Tailscale is the
drop-in managed fallback (same WireGuard mesh, external control plane,
per-user pricing beyond the small free tier). Option D may serve as the
stopgap while the overlay is set up, and must be retired when phase 3's
isolation criterion is measured.

DX contract (so tunneling is "easy", not just possible):

- Onboarding is three steps in the EasyAccess doc: install client → log in
  with the VPath account → `vpath status` confirms reachability.
- `vpath doctor` checks the overlay first and prints the exact fix when the
  server is unreachable, instead of failing deep in a deploy.
- The CLI and console always address the server by its stable overlay DNS
  name (e.g. `nuc.vpath.internal`), never by LAN IP — configs stay identical
  for local and remote users.
