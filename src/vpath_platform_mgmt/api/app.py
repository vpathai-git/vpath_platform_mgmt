"""FastAPI wiring: a thin HTTP surface over ``OpsService``.

No endpoint contains ops logic — every gate lives in the service layer, so
CLI and console can never disagree (docs/PLATFORM_FUNCTIONS.md, Surfaces).
"""

from __future__ import annotations

from importlib import resources

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from collections.abc import Callable

from vpath_platform_mgmt.api.auth import (
    DEV_ACTOR_HEADER,
    DEV_ROLE_HEADER,
    AuthError,
    Identity,
    dev_identity,
    validate_auth_mode,
)
from vpath_platform_mgmt.api.oidc import OidcValidator
from vpath_platform_mgmt.ops.model import OpsError
from vpath_platform_mgmt.ops.service import OpsService

IdentityFn = Callable[[Request], Identity]


class JobRequest(BaseModel):
    """Body of ``POST /api/jobs``."""

    verb: str
    app: str = ""
    confirm: str = ""


def _console_html() -> str:
    package = resources.files("vpath_platform_mgmt.api")
    return (package / "console.html").read_text(encoding="utf-8")


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


def create_app(
    service: OpsService,
    auth_mode: str = "dev",
    oidc_validator: OidcValidator | None = None,
) -> FastAPI:
    """Build the API around a service; refuses unsafe auth/engine pairings."""
    validate_auth_mode(auth_mode, service.engine_name, oidc_validator is not None)
    identity: IdentityFn
    if auth_mode == "oidc" and oidc_validator is not None:
        identity = _oidc_identity_fn(oidc_validator)
    else:
        identity = _dev_identity
    app = FastAPI(title="vpath platform mgmt — Ops API", version="0.1.0")

    @app.get("/", response_class=HTMLResponse)
    def console() -> str:
        """Serve the thin web console."""
        return _console_html()

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

    return app
