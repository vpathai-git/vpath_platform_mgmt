"""FastAPI wiring: a thin HTTP surface over ``OpsService``.

No endpoint contains ops logic — every gate lives in the service layer, so
CLI and console can never disagree (docs/PLATFORM_FUNCTIONS.md, Surfaces).
"""

from __future__ import annotations

from collections.abc import Callable
from importlib import resources
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel

from vpath_platform_mgmt.api import kc_proxy as kc_proxy_module
from vpath_platform_mgmt.api import routes_apps, routes_instances, routes_runtime
from vpath_platform_mgmt.api.kc_proxy import KeycloakProxy
from vpath_platform_mgmt.api.auth import (
    DEV_ACTOR_HEADER,
    DEV_ROLE_HEADER,
    AuthError,
    BrowserAuthConfig,
    Identity,
    dev_identity,
    validate_auth_mode,
    validate_browser_auth,
)
from vpath_platform_mgmt.api.oidc import OidcValidator
from vpath_platform_mgmt.ops.app_runtime import RuntimeReader
from vpath_platform_mgmt.ops.apps import AppCatalog
from vpath_platform_mgmt.ops.model import OpsError
from vpath_platform_mgmt.ops.service import OpsService
from vpath_platform_mgmt.ops.source import SourceMaterializer
from vpath_platform_mgmt.ops.served_catalog import ServedCatalogReader
from vpath_platform_mgmt.ops.tunnel import TunnelError

IdentityFn = Callable[[Request], Identity]

ASSET_TYPES = {
    "console.css": "text/css",
    "console.js": "application/javascript",
    "auth.js": "application/javascript",
    "store.js": "application/javascript",
    "runtime.js": "application/javascript",
    "instances.js": "application/javascript",
}


class JobRequest(BaseModel):
    """Body of ``POST /api/jobs``."""

    verb: str
    app: str = ""
    confirm: str = ""


def _asset(name: str) -> str:
    package = resources.files("vpath_platform_mgmt.api")
    return (package / name).read_text(encoding="utf-8")


def _dev_identity(request: Request) -> Identity:
    try:
        return dev_identity(
            request.headers.get(DEV_ACTOR_HEADER),
            request.headers.get(DEV_ROLE_HEADER),
        )
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=exc.message) from exc


def _oidc_identity_fn(validator: OidcValidator) -> IdentityFn:
    def identity(request: Request) -> Identity:
        try:
            return validator.identity(request.headers.get("authorization"))
        except AuthError as exc:
            raise HTTPException(status_code=401, detail=exc.message) from exc

    return identity


def _submit(service: OpsService, caller: Identity, body: JobRequest) -> dict[str, str]:
    try:
        job = service.submit(
            verb_name=body.verb,
            app=body.app,
            actor=caller.actor,
            role_name=caller.role,
            confirm=body.confirm,
        )
    except OpsError as exc:
        raise HTTPException(status_code=exc.http_status, detail=exc.message) from exc
    return {"job": job.id}


def _register_console(app: FastAPI) -> None:
    """Console page and its static assets."""

    @app.get("/", response_class=HTMLResponse)
    def console() -> str:
        """Serve the thin web console."""
        return _asset("console.html")

    @app.get("/{asset}", include_in_schema=False)
    def console_asset(asset: str) -> Response:
        """Serve console.css / console.js."""
        media = ASSET_TYPES.get(asset)
        if media is None:
            raise HTTPException(status_code=404, detail="not found")
        return Response(_asset(asset), media_type=media)


def _register_ops(app: FastAPI, identity: IdentityFn, service: OpsService) -> None:
    """Job submission and state."""

    @app.get("/api/state")
    def state(request: Request, fresh: bool = False) -> dict[str, object]:
        """Snapshot for the console; ``fresh`` forces an instance re-probe."""
        identity(request)
        return service.state(fresh=fresh)

    @app.post("/api/instance/tunnel")
    def start_tunnel(request: Request) -> dict[str, str]:
        """Open this instance's SSH tunnel; admin only, audited in the service."""
        caller = identity(request)
        try:
            return {"result": service.start_tunnel(caller.actor, caller.role)}
        except OpsError as exc:
            raise HTTPException(
                status_code=exc.http_status, detail=exc.message
            ) from exc
        except TunnelError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/jobs", status_code=202)
    def submit(request: Request, body: JobRequest) -> dict[str, str]:
        """Submit a verb as a job; typed ops errors map to HTTP statuses."""
        return _submit(service, identity(request), body)

    @app.get("/api/jobs/{job_id}")
    def job_detail(request: Request, job_id: str) -> dict[str, object]:
        """One job with its full log."""
        identity(request)
        job = service.job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail=f"no job {job_id}")
        return job.to_dict()


def _register_identity(
    app: FastAPI, identity: IdentityFn, browser_auth: BrowserAuthConfig
) -> None:
    """How to sign in, and who the caller turned out to be."""

    @app.get("/api/auth-config")
    def auth_config() -> dict[str, str]:
        """Public discovery data so the browser can start a login."""
        return browser_auth.to_dict()

    @app.get("/api/me")
    def me(request: Request) -> dict[str, str]:
        """The caller's identity and the role their token actually grants."""
        caller = identity(request)
        return {"actor": caller.actor, "role": caller.role}


def create_app(
    service: OpsService,
    auth_mode: str = "dev",
    oidc_validator: OidcValidator | None = None,
    materializer: SourceMaterializer | None = None,
    catalog: AppCatalog | None = None,
    platform_url: str = "",
    browser_auth: BrowserAuthConfig | None = None,
    kc_proxy: KeycloakProxy | None = None,
    served_catalog: ServedCatalogReader | None = None,
    runtime: RuntimeReader | None = None,
    instances_register: Path | None = None,
    instances_probe_timeout: int = 12,
) -> FastAPI:
    """Build the API around a service; refuses unsafe auth/engine pairings."""
    validate_auth_mode(auth_mode, service.engine_name, oidc_validator is not None)
    browser_auth = browser_auth or BrowserAuthConfig(mode=auth_mode)
    validate_browser_auth(browser_auth)
    identity: IdentityFn
    if auth_mode == "oidc" and oidc_validator is not None:
        identity = _oidc_identity_fn(oidc_validator)
    else:
        identity = _dev_identity
    app = FastAPI(title="vpath platform mgmt — Ops API", version="0.1.0")
    _register_identity(app, identity, browser_auth)
    _register_ops(app, identity, service)
    routes_apps.register(
        app, identity, service, catalog, materializer, platform_url, served_catalog
    )
    routes_runtime.register(app, identity, service, runtime)
    routes_instances.register(
        app,
        identity,
        instances_register,
        probe_timeout=instances_probe_timeout,
    )
    # Ahead of the console's catch-all asset route, which would swallow it.
    if kc_proxy is not None:
        kc_proxy_module.register(app, kc_proxy)
    _register_console(app)
    return app
