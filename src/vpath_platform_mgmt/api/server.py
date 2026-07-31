"""Entry point: build the service from environment config and serve it.

``vpath-console --instance <name>`` loads that instance's ``.env.<name>``
profile from the repo root (gitignored; see ``.env.console.example``) before
reading anything below, so a real instance is one flag rather than a screenful
of exports. Explicit environment variables still win over the profile.

Configuration is explicit and fails hard (no silent fallbacks):

- ``VPATH_MGMT_ENGINE``: ``simulated`` (default), ``local`` or ``gitops``.
  ``local`` additionally requires ``VPATH_MGMT_SERVER_CHECKOUT`` to point at
  the server checkout on this host — it is only valid on the shared server.
  ``gitops`` is the API-only path (no checkout): it requires
  ``VPATH_MGMT_GITEA_URL`` + ``VPATH_MGMT_GITEA_TOKEN`` for the
  Deploy-of-Record and ``VPATH_MGMT_K8S_URL`` + ``VPATH_MGMT_K8S_TOKEN`` to
  observe ArgoCD reconciliation.
- ``VPATH_MGMT_INSTANCE``: register name of the instance this console
  drives (e.g. ``vm5``). Required for real engines; ``sim`` when simulated.
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

import argparse
import os
from collections.abc import Mapping, MutableMapping
from pathlib import Path

from dotenv import dotenv_values

from vpath_platform_mgmt.api.app import create_app
from vpath_platform_mgmt.api.auth import BrowserAuthConfig
from vpath_platform_mgmt.api.builders import (
    TRUTHY,
    build_catalog,
    build_engine,
    build_publish_pipeline,
    build_runtime_reader,
    build_served_catalog,
    build_tunnel_config,
    repo_root,
    resolve_instance_name,
)
from vpath_platform_mgmt.api.kc_proxy import KeycloakProxy
from vpath_platform_mgmt.api.oidc import OidcConfig, OidcValidator
from vpath_platform_mgmt.ops.service import OpsService
from vpath_platform_mgmt.ops.source import SourceMaterializer

CONSOLE_CLIENT_ID = "vpath-console"


def load_profile(
    instance: str, env: MutableMapping[str, str], root: Path | None = None
) -> Path | None:
    """Apply ``.env.<instance>`` so a console starts without a long command line.

    Real environment variables win over the file, so a one-off override on the
    command line still works. A named profile that does not exist is an error:
    silently falling back to the simulated default would put a console that was
    asked for a real instance in front of a simulation.
    """
    if not instance:
        return None
    profile = (root or repo_root()) / f".env.{instance}"
    if not profile.is_file():
        raise ValueError(
            f"no profile for instance '{instance}' at {profile} — copy "
            ".env.console.example there and fill in that instance's values"
        )
    for key, value in dotenv_values(profile).items():
        if value is not None:
            env.setdefault(key, value)
    env.setdefault("VPATH_MGMT_INSTANCE", instance)
    return profile


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


def main() -> None:  # pragma: no cover - thin uvicorn wrapper
    """Serve the console; config errors abort startup loudly."""
    import uvicorn

    parser = argparse.ArgumentParser(
        prog="vpath-console",
        description="Serve the ops console for one platform instance.",
    )
    parser.add_argument(
        "--instance",
        default=os.environ.get("VPATH_MGMT_INSTANCE", ""),
        help="drive this instance, loading its .env.<name> profile",
    )
    load_profile(parser.parse_args().instance, os.environ)

    engine = build_engine(os.environ)
    service = OpsService(
        engine,
        instance_name=resolve_instance_name(os.environ, engine.name),
        tunnel_config=build_tunnel_config(os.environ),
        publish=build_publish_pipeline(os.environ),
    )
    app = create_app(
        service,
        auth_mode=os.environ.get("VPATH_MGMT_AUTH", "dev"),
        oidc_validator=build_oidc_validator(os.environ),
        materializer=build_materializer(os.environ),
        catalog=build_catalog(os.environ),
        platform_url=os.environ.get("VPATH_MGMT_PLATFORM_URL", ""),
        browser_auth=build_browser_auth(os.environ),
        kc_proxy=build_kc_proxy(os.environ),
        served_catalog=build_served_catalog(os.environ),
        runtime=build_runtime_reader(os.environ),
    )
    uvicorn.run(
        app,
        host=os.environ.get("VPATH_MGMT_HOST", "127.0.0.1"),
        port=int(os.environ.get("VPATH_MGMT_PORT", "8765")),
    )
