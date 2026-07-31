"""Application routes: catalog, explorer browsing, and source upload."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from fastapi import FastAPI, HTTPException, Request

from vpath_platform_mgmt.api.auth import Identity
from vpath_platform_mgmt.api.routes_publish import _register_publish
from vpath_platform_mgmt.ops.apps import AppCatalog, AppEntry
from vpath_platform_mgmt.ops.served_catalog import (
    ServedCatalogError,
    ServedCatalogReader,
    compare,
)
from vpath_platform_mgmt.ops.browse import AppBrowser, BrowseError
from vpath_platform_mgmt.ops.engine import EngineFailure
from vpath_platform_mgmt.ops.model import Role
from vpath_platform_mgmt.ops.service import OpsService
from vpath_platform_mgmt.ops.source import (
    SourceError,
    SourceMaterializer,
    SourceProvenance,
)

IdentityFn = Callable[[Request], Identity]


def _materialize(
    materializer: SourceMaterializer | None,
    caller: Identity,
    app_name: str,
    body: bytes,
    request: Request,
) -> dict[str, object]:
    if materializer is None:
        raise HTTPException(
            status_code=409,
            detail="no server checkout configured — source materialization "
            "requires VPATH_MGMT_SERVER_CHECKOUT",
        )
    if caller.role != Role.ADMIN.value:
        raise HTTPException(
            status_code=403,
            detail="materializing app source requires role admin — refused",
        )
    provenance = SourceProvenance(
        repo=request.headers.get("x-source-repo", ""),
        ref=request.headers.get("x-source-ref", ""),
        commit=request.headers.get("x-source-commit", ""),
        dirty=request.headers.get("x-source-dirty", "") == "true",
    )
    replace = request.headers.get("x-source-replace", "") == "true"
    try:
        return materializer.materialize(app_name, body, provenance, replace=replace)
    except SourceError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


def _register_catalog(
    app: FastAPI,
    identity: IdentityFn,
    catalog: AppCatalog | None,
    platform_url: str,
    service: OpsService,
    served: ServedCatalogReader | None = None,
) -> None:
    @app.get("/api/apps")
    def list_apps(request: Request) -> dict[str, object]:
        """The app store: what exists, which of it is installed, and what the
        platform's own sidebar currently offers."""
        identity(request)
        entries = catalog.entries() if catalog is not None else []
        try:
            installed = service.installed_apps()
        except EngineFailure:
            # The store still renders, but every app reports 'unknown'
            # rather than a guess: showing "not installed" for a running app
            # invites an install nobody asked for.
            installed = None
        apps = []
        for entry in entries:
            row = entry.to_dict(platform_url)
            row["installed"] = None if installed is None else entry.name in installed
            apps.append(row)
        return {
            "platform_url": platform_url,
            "apps": apps,
            "installed_known": installed is not None,
            "catalog": _catalog_state(entries, installed, served),
        }


def _catalog_state(
    entries: Sequence[AppEntry],
    installed: list[str] | None,
    served: ServedCatalogReader | None,
) -> dict[str, object]:
    """Counts the console is sure of, plus what the platform serves.

    An unreadable platform catalog is reported as its reason, never as an
    empty one: "the platform offers nothing" and "we could not ask" look
    identical in a summary line and mean opposite things.
    """
    state: dict[str, object] = {
        "total": len(entries),
        "installed": None if installed is None else len(installed),
        "installed_here": (
            None
            if installed is None
            else sum(1 for entry in entries if entry.name in installed)
        ),
    }
    if served is None:
        state["platform"] = None
        state["platform_error"] = "no platform URL configured"
        return state
    try:
        state["platform"] = compare(entries, served.entries())
        state["platform_error"] = None
    except ServedCatalogError as exc:
        state["platform"] = None
        state["platform_error"] = str(exc)
    return state


def _register_browse(
    app: FastAPI, identity: IdentityFn, catalog: AppCatalog | None
) -> None:
    @app.get("/api/apps/{app_name}/tree")
    def app_tree(request: Request, app_name: str) -> dict[str, object]:
        """File tree of one application, for the explorer."""
        identity(request)
        if catalog is None:
            raise HTTPException(status_code=404, detail="no application catalog")
        try:
            nodes = AppBrowser(catalog).tree(app_name)
        except BrowseError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"app": app_name, "nodes": [node.to_dict() for node in nodes]}

    @app.get("/api/apps/{app_name}/file")
    def app_file(request: Request, app_name: str, path: str) -> dict[str, object]:
        """Text content of one file inside an application."""
        identity(request)
        if catalog is None:
            raise HTTPException(status_code=404, detail="no application catalog")
        try:
            return AppBrowser(catalog).read(app_name, path)
        except BrowseError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


def _register_source(
    app: FastAPI,
    identity: IdentityFn,
    service: OpsService,
    materializer: SourceMaterializer | None,
) -> None:
    @app.post("/api/apps/{app_name}/source", status_code=201)
    async def put_source(request: Request, app_name: str) -> dict[str, object]:
        """Materialize uploaded app source into the server checkout (Admin)."""
        caller = identity(request)
        body = await request.body()
        summary = _materialize(materializer, caller, app_name, body, request)
        service.record_source(app_name, caller.actor, caller.role, summary)
        return summary


def register(
    app: FastAPI,
    identity: IdentityFn,
    service: OpsService,
    catalog: AppCatalog | None,
    materializer: SourceMaterializer | None,
    platform_url: str,
    served: ServedCatalogReader | None = None,
) -> None:
    """Attach every /api/apps route to the FastAPI app."""
    _register_catalog(app, identity, catalog, platform_url, service, served)
    _register_browse(app, identity, catalog)
    _register_source(app, identity, service, materializer)
    _register_publish(app, identity, service)
