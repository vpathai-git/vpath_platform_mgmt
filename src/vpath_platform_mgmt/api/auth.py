"""Request identity. Two explicit modes, no silent fallback.

``dev``  — identity from explicit headers; for local development against the
           simulated engine only. Refuses requests without headers, and
           refuses to start at all with a real engine.
``oidc`` — Keycloak-validated bearer tokens (decision 6, api/oidc.py). The
           only mode allowed in front of a real engine.
"""

from __future__ import annotations

from dataclasses import dataclass

DEV_ACTOR_HEADER = "x-dev-actor"
DEV_ROLE_HEADER = "x-dev-role"

AUTH_MODES = ("dev", "oidc")


@dataclass(frozen=True)
class Identity:
    """Authenticated caller: who, and in which role."""

    actor: str
    role: str


class AuthError(Exception):
    """Request could not be authenticated (maps to HTTP 401)."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def dev_identity(actor: str | None, role: str | None) -> Identity:
    """Build an identity from dev headers; refuse if either is missing."""
    if not actor or not role:
        raise AuthError(
            f"dev auth requires headers {DEV_ACTOR_HEADER} and {DEV_ROLE_HEADER}"
        )
    return Identity(actor=actor, role=role)


def validate_auth_mode(mode: str, engine_name: str, has_validator: bool) -> None:
    """Fail hard on unknown modes and on unsafe mode/engine combinations."""
    if mode not in AUTH_MODES:
        raise ValueError(f"unknown auth mode '{mode}' (expected one of {AUTH_MODES})")
    if mode == "oidc" and not has_validator:
        raise ValueError(
            "oidc auth requires a configured validator — set "
            "VPATH_MGMT_OIDC_ISSUER (docs/ACCESS_MECHANISM.md)"
        )
    if mode == "dev" and engine_name != "simulated":
        raise ValueError(
            "refusing dev auth with a real engine: header-trust identity must "
            "never gate real verbs (docs/ACCESS_MECHANISM.md)"
        )
