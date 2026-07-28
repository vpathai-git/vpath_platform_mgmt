"""Projection — the heart of this example: map a cognition-shape selection onto
the platform's ``agent-provider`` resource shape (declared, never hand-built).

The mapping (concept ↔ platform resource):

  | cognition axis             | platform agent-provider                       |
  |----------------------------|-----------------------------------------------|
  | Provider (llm_provider)    | resource.properties.provider                  |
  | Model (from the catalog)   | resource.properties.model                     |
  | Wrapper / runtime          | resource.variant                              |
  | Credentials (secret half)  | *_API_KEY via envfrom — PLATFORM-OWNED, never |
  |                            | touched by the app                            |
  | AuthMode / Requirements /  | NOT expressed in the resource today — the     |
  | catalog source             | app's modeling layer ADDS this, validating    |
  |                            | the selection BEFORE it becomes a resource    |

This module produces two artifacts the editor renders: a resource.json PREVIEW
(the ``ResolvedResourceEntry`` shape the platform writes at pod startup, non-secret
half only) and the manifest ``resourceRequirements`` snippet the app DECLARES so
the platform provisions/injects it.
"""

from __future__ import annotations

# The platform always delivers agent-provider's non-secret config via the
# resource.json manifest (L2); the secret key arrives separately via envfrom
# (L3) and is NEVER part of what the app declares or reads.
_DELIVERY_MODE = "resource_json"


def project_resource_json(
    provider: str, model: str, variant: str, auth_mode: str
) -> dict:
    """The non-secret ``ResolvedResourceEntry`` the platform would write.

    Note the secret half is ABSENT by construction: the app models config, not
    credentials (the ``*_API_KEY`` arrives via envfrom, platform-owned).
    ``auth_mode`` is carried as a property here as the MODELING layer's addition
    — the platform's agent-provider schema does not express it today.
    """
    return {
        "type": "agent-provider",
        "variant": variant,
        "delivery_mode": _DELIVERY_MODE,
        "properties": {
            "provider": provider,
            "model": model,
            # Modeling-layer addition (not in the platform resource schema today):
            "auth_mode": auth_mode,
        },
    }


def project_manifest_snippet(variant: str) -> str:
    """The ``resourceRequirements`` block the app DECLARES in vpath-app.yaml.

    Only the class + variant + actions are platform vocabulary; provider/model
    are runtime properties (resource.json), and auth_mode is the modeling
    layer's concern — so they are intentionally NOT in the declaration.
    """
    return (
        "spec:\n"
        "  resourceRequirements:\n"
        "    required:\n"
        "      - class: agent-provider\n"
        f"        variant: {variant}\n"
        "        actions: [use]\n"
        "        delivery: resource_json\n"
    )


def mapping_rows(provider: str, model: str, variant: str, auth_mode: str) -> list[dict]:
    """The axis -> target rows the editor renders as the mapping table."""
    return [
        {
            "axis": "Provider (llm_provider)",
            "value": provider,
            "target": "resource.properties.provider",
        },
        {
            "axis": "Model (from the catalog)",
            "value": model,
            "target": "resource.properties.model",
        },
        {
            "axis": "Wrapper / runtime",
            "value": variant,
            "target": "resource.variant",
        },
        {
            "axis": "Credentials (secret half)",
            "value": f"{provider.upper()}_API_KEY",
            "target": "envfrom — platform-owned; the app never edits it",
        },
        {
            "axis": "AuthMode",
            "value": auth_mode,
            "target": "modeling-layer validation (not in the resource today)",
        },
    ]


def project(provider: str, model: str, variant: str, auth_mode: str) -> dict:
    """The full projection: resource.json preview + manifest snippet + mapping."""
    return {
        "resource_json": project_resource_json(provider, model, variant, auth_mode),
        "manifest_snippet": project_manifest_snippet(variant),
        "mapping": mapping_rows(provider, model, variant, auth_mode),
    }
