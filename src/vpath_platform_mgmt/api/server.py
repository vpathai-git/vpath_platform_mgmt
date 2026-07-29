"""Entry point: build the service from environment config and serve it.

Configuration is explicit and fails hard (no silent fallbacks):

- ``VPATH_MGMT_ENGINE``: ``simulated`` (default), ``local`` or ``gitops``.
  ``local`` additionally requires ``VPATH_MGMT_SERVER_CHECKOUT`` to point at
  the server checkout on this host — it is only valid on the shared server.
  ``gitops`` is the API-only path (no checkout): it requires
  ``VPATH_MGMT_GITEA_URL`` + ``VPATH_MGMT_GITEA_TOKEN`` for the
  Deploy-of-Record and ``VPATH_MGMT_K8S_URL`` + ``VPATH_MGMT_K8S_TOKEN`` to
  observe ArgoCD reconciliation.
- ``VPATH_MGMT_AUTH``: ``dev`` (default) or ``oidc``. ``dev`` is refused
  with a real engine; ``oidc`` requires ``VPATH_MGMT_OIDC_ISSUER`` and
  accepts ``VPATH_MGMT_OIDC_AUDIENCE`` plus, for self-signed dev platforms
  only, the explicit ``VPATH_MGMT_OIDC_INSECURE_TLS=1``. The console page
  signs in with ``VPATH_MGMT_OIDC_CLIENT_ID`` (default ``vpath-console``),
  a public PKCE client that must exist in the realm.
  ``VPATH_MGMT_OIDC_JWKS_URL`` overrides only where signing keys are
  fetched from, for when the API reaches Keycloak by a different route
  than the browser (tunnel, overlay, in-cluster name). The issuer is still
  matched against the token exactly.
- ``VPATH_MGMT_HOST`` / ``VPATH_MGMT_PORT``: bind address (default
  127.0.0.1:8765 — never expose beyond the overlay).
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from vpath_platform_mgmt.api.app import create_app
from vpath_platform_mgmt.api.auth import BrowserAuthConfig
from vpath_platform_mgmt.api.kc_proxy import KeycloakProxy
from vpath_platform_mgmt.api.oidc import OidcConfig, OidcValidator
from vpath_platform_mgmt.ops.argocd import ArgoClient
from vpath_platform_mgmt.ops.engine import EngineAdapter, LocalEngine, SimulatedEngine
from vpath_platform_mgmt.ops.gitea import GiteaClient
from vpath_platform_mgmt.ops.gitops_engine import GitOpsEngine
from vpath_platform_mgmt.ops.apps import AppCatalog
from vpath_platform_mgmt.ops.service import OpsService
from vpath_platform_mgmt.ops.source import SourceMaterializer

ENGINE_MODES = ("simulated", "local", "gitops")
SIMULATED_STEP_DELAY = 0.8
TRUTHY = ("1", "true", "yes")
GITEA_OWNER = "platform"
GITEA_REPO = "k8s-manifests"
CONSOLE_CLIENT_ID = "vpath-console"


def require(env: Mapping[str, str], key: str, mode: str) -> str:
    """Read a mandatory setting, naming the mode that made it mandatory."""
    value = env.get(key, "")
    if not value:
        raise ValueError(f"engine mode '{mode}' requires {key}")
    return value


def build_gitops_engine(env: Mapping[str, str]) -> GitOpsEngine:
    """Gitea + Kubernetes clients for the API-only deploy path.

    Both endpoints sit inside the platform's private network, so this engine
    is only usable where that network is reachable (on the server, or through
    the operator's tunnel). ``VPATH_MGMT_INSECURE_TLS`` exists for the
    self-signed dev platform and must be set deliberately.
    """
    insecure = env.get("VPATH_MGMT_INSECURE_TLS", "").lower() in TRUTHY
    gitea = GiteaClient(
        base_url=require(env, "VPATH_MGMT_GITEA_URL", "gitops"),
        owner=env.get("VPATH_MGMT_GITEA_OWNER") or GITEA_OWNER,
        repo=env.get("VPATH_MGMT_GITEA_REPO") or GITEA_REPO,
        token=require(env, "VPATH_MGMT_GITEA_TOKEN", "gitops"),
        branch=env.get("VPATH_MGMT_GITEA_BRANCH") or "main",
        verify_tls=not insecure,
    )
    argo = ArgoClient(
        base_url=require(env, "VPATH_MGMT_K8S_URL", "gitops"),
        token=require(env, "VPATH_MGMT_K8S_TOKEN", "gitops"),
        verify_tls=not insecure,
    )
    return GitOpsEngine(gitea, argo)


def build_engine(env: Mapping[str, str]) -> EngineAdapter:
    """Choose the engine adapter from env; fail hard on bad config."""
    mode = env.get("VPATH_MGMT_ENGINE", "simulated")
    if mode not in ENGINE_MODES:
        raise ValueError(
            f"unknown engine mode '{mode}' (expected one of {ENGINE_MODES})"
        )
    if mode == "gitops":
        return build_gitops_engine(env)
    if mode == "local":
        checkout = env.get("VPATH_MGMT_SERVER_CHECKOUT", "")
        if not checkout:
            raise ValueError("engine mode 'local' requires VPATH_MGMT_SERVER_CHECKOUT")
        return LocalEngine(Path(checkout), extra_env=parse_engine_env(env))
    return SimulatedEngine(step_delay=SIMULATED_STEP_DELAY)


def parse_engine_env(env: Mapping[str, str]) -> dict[str, str]:
    """Parse ``VPATH_MGMT_ENGINE_ENV`` ("K=V,K2=V2") for the engine subprocess.

    The pipeline reads its topology from the environment (e.g.
    ``VPATH_INSTALL_MODE=nuc`` on a single-box target). Malformed entries
    fail hard rather than being skipped.
    """
    raw = env.get("VPATH_MGMT_ENGINE_ENV", "").strip()
    if not raw:
        return {}
    pairs: dict[str, str] = {}
    for item in raw.split(","):
        entry = item.strip()
        if not entry:
            continue
        if "=" not in entry:
            raise ValueError(f"VPATH_MGMT_ENGINE_ENV entry '{entry}' is not KEY=VALUE")
        key, value = entry.split("=", 1)
        if not key.strip():
            raise ValueError("VPATH_MGMT_ENGINE_ENV has an entry with an empty key")
        pairs[key.strip()] = value.strip()
    return pairs


def build_oidc_validator(env: Mapping[str, str]) -> OidcValidator | None:
    """Build the token validator when oidc mode is selected; fail hard."""
    if env.get("VPATH_MGMT_AUTH", "dev") != "oidc":
        return None
    issuer = env.get("VPATH_MGMT_OIDC_ISSUER", "")
    if not issuer:
        raise ValueError("auth mode 'oidc' requires VPATH_MGMT_OIDC_ISSUER")
    config = OidcConfig(
        issuer=issuer,
        audience=env.get("VPATH_MGMT_OIDC_AUDIENCE") or None,
        insecure_tls=env.get("VPATH_MGMT_OIDC_INSECURE_TLS", "").lower() in TRUTHY,
        jwks_url_override=env.get("VPATH_MGMT_OIDC_JWKS_URL", ""),
        leeway_seconds=float(env.get("VPATH_MGMT_OIDC_LEEWAY_SECONDS") or 60.0),
    )
    return OidcValidator(config)


def build_browser_auth(env: Mapping[str, str]) -> BrowserAuthConfig:
    """Discovery data the console page needs to run its own login.

    ``VPATH_MGMT_OIDC_BROWSER_ISSUER`` points the browser at a route it can
    actually reach — the console's own Keycloak relay — while the validator
    keeps matching tokens against the real ``VPATH_MGMT_OIDC_ISSUER``.
    """
    browser_issuer = env.get("VPATH_MGMT_OIDC_BROWSER_ISSUER", "")
    return BrowserAuthConfig(
        mode=env.get("VPATH_MGMT_AUTH", "dev"),
        issuer=browser_issuer or env.get("VPATH_MGMT_OIDC_ISSUER", ""),
        client_id=env.get("VPATH_MGMT_OIDC_CLIENT_ID") or CONSOLE_CLIENT_ID,
    )


def build_kc_proxy(env: Mapping[str, str]) -> KeycloakProxy | None:
    """Relay Keycloak through the console, when configured to.

    Needed only where the browser cannot reach Keycloak directly but the
    console can. Absent by default: the browser talks to Keycloak itself.
    """
    upstream = env.get("VPATH_MGMT_KC_PROXY_UPSTREAM", "")
    if not upstream:
        return None
    public = env.get("VPATH_MGMT_KC_PROXY_PUBLIC", "")
    if not public:
        raise ValueError(
            "VPATH_MGMT_KC_PROXY_UPSTREAM requires VPATH_MGMT_KC_PROXY_PUBLIC — "
            "the relay must know which absolute URLs to rewrite"
        )
    insecure = env.get("VPATH_MGMT_OIDC_INSECURE_TLS", "").lower() in TRUTHY
    return KeycloakProxy(upstream, public, verify_tls=not insecure)


def build_materializer(env: Mapping[str, str]) -> SourceMaterializer | None:
    """Materializer for the configured checkout, or None when there isn't one."""
    checkout = env.get("VPATH_MGMT_SERVER_CHECKOUT", "")
    if not checkout:
        return None
    return SourceMaterializer(Path(checkout))


def build_catalog(env: Mapping[str, str]) -> AppCatalog:
    """Catalog over this repo's ``apps/`` plus the server checkout, if any.

    ``VPATH_MGMT_APPS_DIR`` overrides the repo folder. Both sources use the
    same ``<dir>/<app>/vpath-app.yaml`` layout; repo apps win on name clash.
    """
    repo_apps = env.get("VPATH_MGMT_APPS_DIR", "") or str(
        Path(__file__).resolve().parents[3] / "apps"
    )
    directories = [Path(repo_apps)]
    checkout = env.get("VPATH_MGMT_SERVER_CHECKOUT", "")
    if checkout:
        directories.append(Path(checkout) / "apps_infra" / "apps")
    return AppCatalog(*directories)


def main() -> None:  # pragma: no cover - thin uvicorn wrapper
    """Serve the console; config errors abort startup loudly."""
    import uvicorn

    engine = build_engine(os.environ)
    service = OpsService(engine)
    app = create_app(
        service,
        auth_mode=os.environ.get("VPATH_MGMT_AUTH", "dev"),
        oidc_validator=build_oidc_validator(os.environ),
        materializer=build_materializer(os.environ),
        catalog=build_catalog(os.environ),
        platform_url=os.environ.get("VPATH_MGMT_PLATFORM_URL", ""),
        browser_auth=build_browser_auth(os.environ),
        kc_proxy=build_kc_proxy(os.environ),
    )
    uvicorn.run(
        app,
        host=os.environ.get("VPATH_MGMT_HOST", "127.0.0.1"),
        port=int(os.environ.get("VPATH_MGMT_PORT", "8765")),
    )
