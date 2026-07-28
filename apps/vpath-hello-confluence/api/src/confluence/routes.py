"""Domain API over Confluence — the only thing this app writes.

Auth: each route depends on `require_auth` (the platform verifies identity). The
resource-gate already authorized credential use before the request arrives, so —
like vpath-jira-demo — the app does NOT call ctx.can for the credential itself.
Failures are structured and loud (CLAUDE.md §7): not-bound → 422 resource_not_bound;
upstream failure → 502 confluence_error. No empty-list fallback.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from vpath_backend_sdk import AuthContext, require_auth

from .credential import ResourceNotBound, client_for, is_bound
from .errors import ConfluenceError

router = APIRouter()


def _not_bound() -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": "resource_not_bound",
            "detail": (
                "No Confluence credential is bound for your account. A platform "
                "administrator binds the 'confluence' resource — then your "
                "spaces appear."
            ),
        },
    )


def _upstream(e: ConfluenceError) -> JSONResponse:
    return JSONResponse(
        status_code=502,
        content={"error": "confluence_error", "status": e.status, "detail": e.detail},
    )


@router.get("/resource/status")
def resource_status(request: Request, ctx: AuthContext = Depends(require_auth)) -> dict:
    """Whether a Confluence credential is bound for this user.

    Drives the UI's first-run state.
    """
    return {"resource": "confluence", "bound": is_bound(request)}


@router.get("/spaces")
def list_spaces(request: Request, ctx: AuthContext = Depends(require_auth)):
    try:
        client = client_for(request)
    except ResourceNotBound:
        return _not_bound()
    try:
        return {"spaces": [s.to_dict() for s in client.list_spaces()]}
    except ConfluenceError as e:
        return _upstream(e)
    finally:
        client.close()


@router.get("/spaces/{space_id}/pages")
def space_root_pages(
    space_id: str, request: Request, ctx: AuthContext = Depends(require_auth)
):
    try:
        client = client_for(request)
    except ResourceNotBound:
        return _not_bound()
    try:
        return {"pages": [p.to_dict() for p in client.space_root_pages(space_id)]}
    except ConfluenceError as e:
        return _upstream(e)
    finally:
        client.close()


@router.get("/pages/{page_id}/children")
def page_children(
    page_id: str, request: Request, ctx: AuthContext = Depends(require_auth)
):
    try:
        client = client_for(request)
    except ResourceNotBound:
        return _not_bound()
    try:
        return {"pages": [p.to_dict() for p in client.page_children(page_id)]}
    except ConfluenceError as e:
        return _upstream(e)
    finally:
        client.close()
