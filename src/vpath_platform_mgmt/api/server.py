"""Entry point: build the service from environment config and serve it.

Configuration is explicit and fails hard (no silent fallbacks):

- ``VPATH_MGMT_ENGINE``: ``simulated`` (default) or ``local``. ``local``
  additionally requires ``VPATH_MGMT_SERVER_CHECKOUT`` to point at the
  server checkout on this host — it is only valid on the shared server.
- ``VPATH_MGMT_AUTH``: ``dev`` (default) or ``oidc``. ``dev`` is refused
  with a real engine; ``oidc`` requires ``VPATH_MGMT_OIDC_ISSUER`` and
  accepts ``VPATH_MGMT_OIDC_AUDIENCE`` plus, for self-signed dev platforms
  only, the explicit ``VPATH_MGMT_OIDC_INSECURE_TLS=1``.
- ``VPATH_MGMT_HOST`` / ``VPATH_MGMT_PORT``: bind address (default
  127.0.0.1:8765 — never expose beyond the overlay).
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from vpath_platform_mgmt.api.app import create_app
from vpath_platform_mgmt.api.oidc import OidcConfig, OidcValidator
from vpath_platform_mgmt.ops.engine import EngineAdapter, LocalEngine, SimulatedEngine
from vpath_platform_mgmt.ops.service import OpsService

ENGINE_MODES = ("simulated", "local")
SIMULATED_STEP_DELAY = 0.8
TRUTHY = ("1", "true", "yes")


def build_engine(env: Mapping[str, str]) -> EngineAdapter:
    """Choose the engine adapter from env; fail hard on bad config."""
    mode = env.get("VPATH_MGMT_ENGINE", "simulated")
    if mode not in ENGINE_MODES:
        raise ValueError(
            f"unknown engine mode '{mode}' (expected one of {ENGINE_MODES})"
        )
    if mode == "local":
        checkout = env.get("VPATH_MGMT_SERVER_CHECKOUT", "")
        if not checkout:
            raise ValueError("engine mode 'local' requires VPATH_MGMT_SERVER_CHECKOUT")
        return LocalEngine(Path(checkout))
    return SimulatedEngine(step_delay=SIMULATED_STEP_DELAY)


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
    )
    return OidcValidator(config)


def main() -> None:  # pragma: no cover - thin uvicorn wrapper
    """Serve the console; config errors abort startup loudly."""
    import uvicorn

    engine = build_engine(os.environ)
    service = OpsService(engine)
    app = create_app(
        service,
        auth_mode=os.environ.get("VPATH_MGMT_AUTH", "dev"),
        oidc_validator=build_oidc_validator(os.environ),
    )
    uvicorn.run(
        app,
        host=os.environ.get("VPATH_MGMT_HOST", "127.0.0.1"),
        port=int(os.environ.get("VPATH_MGMT_PORT", "8765")),
    )
