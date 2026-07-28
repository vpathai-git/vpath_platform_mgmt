"""FastAPI wiring: a thin HTTP surface over ``OpsService``.

No endpoint contains ops logic — every gate lives in the service layer, so
CLI and console can never disagree (docs/PLATFORM_FUNCTIONS.md, Surfaces).
"""

from __future__ import annotations

from collections.abc import Callable
from importlib import resources

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel

from vpath_platform_mgmt.api import routes_apps
from vpath_platform_mgmt.api.auth import (
    DEV_ACTOR_HEADER,
    DEV_ROLE_HEADER,
    AuthError,
    Identity,
    dev_identity,
    validate_auth_mode,
)
from vpath_platform_mgmt.api.oidc import OidcValidator
from vpath_platform_mgmt.ops.apps import AppCatalog
from vpath_platform_mgmt.ops.model import OpsError
from vpath_platform_mgmt.ops.service import OpsService
from vpath_platform_mgmt.ops.source import SourceMaterializer

IdentityFn = Callable[[Request], Identity]

ASSET_TYPES = {"console.css": "text/css", "console.js": "application/javascript"}


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
    def state(request: Request) -> dict[str, object]:
        """Snapshot for the console: jobs, locks, audit, health, engine."""
        identity(request)
        return service.state()

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


def create_app(
    service: OpsService,
    auth_mode: str = "dev",
    oidc_validator: OidcValidator | None = None,
    materializer: SourceMaterializer | None = None,
    catalog: AppCatalog | None = None,
    platform_url: str = "",
) -> FastAPI:
    """Build the API around a service; refuses unsafe auth/engine pairings."""
    validate_auth_mode(auth_mode, service.engine_name, oidc_validator is not None)
    identity: IdentityFn
    if auth_mode == "oidc" and oidc_validator is not None:
        identity = _oidc_identity_fn(oidc_validator)
    else:
        identity = _dev_identity
    app = FastAPI(title="vpath platform mgmt — Ops API", version="0.1.0")
    _register_ops(app, identity, service)
    routes_apps.register(app, identity, service, catalog, materializer, platform_url)
    _register_console(app)
    return app
