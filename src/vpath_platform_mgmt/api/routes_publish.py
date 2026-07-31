"""The publish route: walk a repository from URL to running under ArgoCD.

Split out of ``routes_apps`` along the seam between "browsing and listing
apps" (that module) and "marshalling and submitting a publish job" (this
one), to keep each module under the project's line limit.
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import FastAPI, HTTPException, Request

from vpath_platform_mgmt.api.auth import Identity
from vpath_platform_mgmt.ops.app_registry import DEFAULT_ICON, Generated
from vpath_platform_mgmt.ops.model import OpsError
from vpath_platform_mgmt.ops.repo_fetch import FetchError
from vpath_platform_mgmt.ops.repo_probe import clean_ref
from vpath_platform_mgmt.ops.service import OpsService

IdentityFn = Callable[[Request], Identity]


def _generated(block: object) -> Generated | None:
    """The manifest facts as the registry's own type, or a 400 naming the gap.

    The console sends ``generate`` as JSON, and every stage below here expects
    a ``Generated``. Marshalling at the boundary is what turns a malformed
    block into an answerable refusal instead of an ``AttributeError`` on a
    worker thread nobody is watching.
    """
    if block is None:
        return None
    if not isinstance(block, dict):
        raise HTTPException(
            status_code=400, detail="publish 'generate' must be an object"
        )
    wanted = ("name", "port", "base_path", "title")
    missing = [key for key in wanted if not block.get(key)]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"publish 'generate' needs {', '.join(missing)}",
        )
    try:
        port = int(str(block["port"]))
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"publish 'generate.port' must be a number, not "
            f"'{block['port']}'",
        ) from exc
    return Generated(
        name=str(block["name"]),
        port=port,
        base_path=str(block["base_path"]),
        title=str(block["title"]),
        description=str(block.get("description") or ""),
        icon=str(block.get("icon") or DEFAULT_ICON),
        runtime=str(block.get("runtime") or ""),
    )


def _publish_request(body: dict[str, object]) -> tuple[str, dict[str, object]]:
    """The app name and job payload, refusing a request that cannot be run."""
    missing = [key for key in ("url", "name") if not body.get(key)]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"publish needs {' and '.join(missing)}",
        )
    try:
        ref = clean_ref(str(body.get("ref") or "main"))
    except FetchError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return str(body["name"]), {
        "url": str(body["url"]),
        "ref": ref,
        "path": str(body.get("path") or ""),
        "generate": _generated(body.get("generate")),
        "replace": bool(body.get("replace", False)),
    }


def _register_publish(app: FastAPI, identity: IdentityFn, service: OpsService) -> None:
    @app.post("/api/apps/publish", status_code=202)
    async def publish(request: Request) -> dict[str, object]:
        """Walk a repository from URL to running under ArgoCD (Admin)."""
        caller = identity(request)
        name, payload = _publish_request(await request.json())
        try:
            job = service.submit(
                "publish", name, caller.actor, caller.role, payload=payload
            )
        except OpsError as exc:
            raise HTTPException(
                status_code=exc.http_status, detail=exc.message
            ) from exc
        return job.to_dict()
