"""Domain API for the Agentic Resource Modeler — the only thing this app writes.

Auth: every route depends on ``require_auth`` (the platform verifies identity,
CLAUDE.md §1/§3). Three endpoints:

  GET  /providers        — the cognition catalog the editor offers.
  POST /validate         — validate a (provider, auth_mode, model) selection
                           (reachability + capability), FAIL-HARD with a
                           structured 422 on rejection; returns the projected
                           agent-provider resource shape on success.
  GET  /resource/status  — the CURRENTLY-BOUND agent-provider (read-only, via
                           the SDK ResourceManifest). Reports bound:false (a real
                           first-run state, not a fabricated default) when none.

This app NEVER reads/stores/prompts an LLM API key — the secret is
platform-injected (envfrom) and out of the app's hands (CLAUDE.md §1; plan §9).
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from vpath_backend_sdk import AuthContext, ResourceManifest, require_auth

from .axes import CognitionError, ModelRequirements
from .catalog import describe_catalog
from .validate import validate_selection

router = APIRouter()

_NOT_BOUND_MSG = (
    "no agent-provider resource is bound to this app — bind one in the platform "
    "shell (the manifest declares it as user-selectable)."
)
_NO_MANIFEST_MSG = (
    "no resource manifest delivered yet — the platform writes it at pod startup "
    "once an agent-provider is bound."
)


class RequirementsBody(BaseModel):
    """The capability "fuel" the caller requires (axis 4). All-default = no gate."""

    function_calling: bool = False
    vision: bool = False
    reasoning: bool = False
    structured_output: bool = False
    min_context: int = Field(default=0, ge=0)


class ValidateRequest(BaseModel):
    """A cognition-shape selection to validate and project."""

    provider: str = Field(min_length=1, max_length=64)
    auth_mode: str = Field(min_length=1, max_length=32)
    model: str = Field(min_length=1, max_length=128)
    variant: str = Field(min_length=1, max_length=64)
    requirements: Optional[RequirementsBody] = None


@router.get("/providers")
def providers(ctx: AuthContext = Depends(require_auth)) -> dict:
    """The catalog (providers x auth-modes x model sources, plus variants)."""
    return describe_catalog()


@router.post("/validate")
def validate(body: ValidateRequest, ctx: AuthContext = Depends(require_auth)) -> dict:
    """Validate the selection; 422 (structured) on any cognition rejection."""
    reqs = body.requirements or RequirementsBody()
    try:
        return validate_selection(
            provider=body.provider,
            auth_mode_value=body.auth_mode,
            model=body.model,
            variant=body.variant,
            requirements=ModelRequirements(
                function_calling=reqs.function_calling,
                vision=reqs.vision,
                reasoning=reqs.reasoning,
                structured_output=reqs.structured_output,
                min_context=reqs.min_context,
            ),
        )
    except CognitionError as exc:
        # FAIL-HARD surfaced as a structured 422 — never a soft pass / fallback.
        # detail is a string ("<code>: <message>") so the SDK mutation hook
        # surfaces the full reason to the editor.
        raise HTTPException(
            status_code=422, detail=f"{exc.code}: {exc.message}"
        ) from exc


@router.get("/resource/status")
def resource_status(ctx: AuthContext = Depends(require_auth)) -> dict:
    """The live agent-provider binding (read-only).

    Reads the platform-delivered resource manifest via the SDK (never a hand
    read of the platform-delivered resource.json). A status query finding none
    reports ``bound: false`` with the real reason — that is the truthful state
    of a first-run app, NOT a fabricated default (CLAUDE.md §7).
    """
    try:
        manifest = ResourceManifest.load()
    except FileNotFoundError:
        return {
            "bound": False,
            "reason": "manifest_unavailable",
            "message": _NO_MANIFEST_MSG,
        }
    entry = manifest.get("agent-provider")
    if entry is None:
        return {"bound": False, "reason": "not_bound", "message": _NOT_BOUND_MSG}
    return {
        "bound": True,
        "variant": entry.variant,
        "delivery_mode": entry.delivery_mode,
        "provider": entry.get("provider"),
        "model": entry.get("model"),
        "properties": entry.properties,
    }
