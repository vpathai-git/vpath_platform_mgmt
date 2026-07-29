---
name: vm5-access
description: Reach the vm5 platform and the ops console — tunnels, which browser can show what, and running builds on the box. Use when opening the platform GUI, signing in to the console, running gradlew on vm5, or when a page shows "cannot reach Keycloak", "Invalid parameter: redirect_uri", or "Invalid Server Actions request".
---

# Reaching vm5

Nothing on vm5 is exposed to the internet. Everything below assumes the
operator's SSH SOCKS tunnel is up on `127.0.0.1:1085` (their
`connect-vm5.ps1`), plus port-forwards this repo's console needs.

Canonical addresses:

| What | Address |
|---|---|
| SSH | `azureuser@20.86.32.146`, key `~/.vpath/creds/vm5/vpath-ai-vm5-win_key.pem` |
| Platform (ingress) | `https://10.0.0.4:30600` — self-signed cert |
| Kubernetes API | `https://10.0.0.4:6443` |
| Server checkout | `/workspace` on vm5, owned by `azureuser` |

## Which browser shows what

This is the part that wastes hours if guessed.

**Ops console (this repo) → built-in browser works.** It is served at
`127.0.0.1:8765` and proxies Keycloak at `/keycloak/*` (`api/kc_proxy.py`),
so the whole login stays on one origin. The `vpath-console` Keycloak client
is registered with `http://127.0.0.1:*` redirect URIs precisely so this works.

**Platform GUI → built-in browser CANNOT work.** Three independent walls,
each verified the hard way:

1. No route to `10.0.0.4` — a fetch times out after ~21 s.
2. The self-signed cert cannot be accepted; the pane denies the navigation.
3. Proxying it to a loopback origin breaks its auth: Next.js Server Actions
   reject `Origin != Host` ("Invalid Server Actions request"), and
   `vpath-web` builds its OIDC `redirect_uri` from an internal address
   (`https://targetvm:30443/...`), so registering the proxy origin in
   Keycloak does NOT help. Do not add redirect URIs to `vpath-web` for this.

**Use the operator's SOCKS Chrome for the platform:**

```powershell
Start-Process "C:\Program Files\Google\Chrome\Application\chrome.exe" -ArgumentList @(
  '--proxy-server=socks5://127.0.0.1:1085',
  '--ignore-certificate-errors',
  "--user-data-dir=$env:TEMP\vpath-platform-profile",
  '--new-window', 'https://10.0.0.4:30600/')
```

A read-only proxy (`platform_view.py` pattern: forward to the tunnelled
ingress, rewrite `https://10.0.0.4:30600` → the local origin, force the
public `Host`, strip `Secure` and HSTS) is fine for *looking* at pages and
proving cluster state. It cannot carry logins or form posts. Never leave one
running where it can be mistaken for the real thing.

## Running builds on vm5

```bash
ssh … azureuser@20.86.32.146
cd /workspace && VPATH_ENV=vm5 ./gradlew <task>
```

Both parts matter and both fail confusingly if missed:

- **Never `sudo`.** `/workspace` is `azureuser`-owned, and the pipeline's
  loopback hop (`vm::ssh_nuc` → `azureuser@10.0.0.4`) uses that user's key.
  Under `sudo` it runs as root, which has no key, and `bootstrapVMs` fails
  with "the NUC is not reachable over SSH" even though `ssh … echo ok` works.
- **`VPATH_ENV=vm5`** selects `config/dot_env/.env.vm5`, which supplies
  `VPATH_INSTALL_MODE=nuc`, `NUC_HOST`, `NUC_USER`. Without it: "run_build_vm
  called on deploy VM". With the mode but no overlay: "NUC_HOST and NUC_USER
  must be set". This is the "from-within" topology — see
  `reports/from-within-install.md`.

Background long builds and read the exit marker; never `| tee` (it masks the
exit code):

```bash
nohup sh -c "./gradlew … > /tmp/b.log 2>&1; echo ===EXIT=\$?=== >> /tmp/b.log" &
```

## Getting code onto /workspace

`/workspace` has **no git remote** and no credentials, deliberately. Use a
bundle, based on the commit the box already has:

```bash
git -C <repo> bundle create /tmp/x.bundle <deployed-sha>..<branch>
scp /tmp/x.bundle azureuser@20.86.32.146:/tmp/
ssh … "cd /workspace && git fetch /tmp/x.bundle <branch>:refs/heads/tmp && git merge --ff-only tmp"
```

Branch from the **deployed** commit, not local HEAD — the local clone is
usually ahead, and bundling from HEAD ships unpushed work to the box.

## A commit is not a deployment

`redeployApp` renders and commits to the Deploy-of-Record, then ArgoCD
reconciles — but it has been observed sitting on a stale revision for hours
despite `automated: {selfHeal: true}`. Always compare the running image
digest against the rendered one; if they differ, force it:

```bash
kubectl -n argocd annotate application <app> argocd.argoproj.io/refresh=hard --overwrite
```

## The app catalog needs three steps, not one

The platform sidebar reads `spec.ui.title` from the **server** manifest
(`vpath_server/apps_infra/apps/<app>/vpath-app.yaml`), compiled into the
`app-catalog` ConfigMap. This repo's `apps/<app>/vpath-app.yaml` feeds only
the ops console. To change a platform label:

1. edit the server manifest
2. `./gradlew deployAppCatalog`
3. `kubectl -n vpath-apps-v2 rollout restart deploy/vpath-web`

Step 3 is required: the ConfigMap is mounted with `subPath`, which Kubernetes
never refreshes in a running pod. After step 2 the ConfigMap is correct while
the pod's file is still stale — verify by reading the file *in the pod*, not
the ConfigMap.
