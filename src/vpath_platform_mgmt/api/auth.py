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


@dataclass(frozen=True)
class BrowserAuthConfig:
    """What the browser needs in order to sign in.

    Served by ``GET /api/auth-config``, which is deliberately unauthenticated:
    a client that cannot yet authenticate has to be told how. It carries only
    public discovery data — an issuer URL and a public client id — never a
    secret.
    """

    mode: str
    issuer: str = ""
    client_id: str = ""

    def to_dict(self) -> dict[str, str]:
        """JSON view; dev mode advertises nothing beyond the mode itself."""
        if self.mode != "oidc":
            return {"mode": self.mode}
        return {
            "mode": self.mode,
            "issuer": self.issuer,
            "client_id": self.client_id,
        }


def validate_browser_auth(config: BrowserAuthConfig) -> None:
    """Refuse an oidc console the browser could never complete a login against."""
    if config.mode != "oidc":
        return
    missing = [
        name
        for name, value in (
            ("VPATH_MGMT_OIDC_ISSUER", config.issuer),
            ("VPATH_MGMT_OIDC_CLIENT_ID", config.client_id),
        )
        if not value
    ]
    if missing:
        raise ValueError(
            f"oidc auth requires {' and '.join(missing)} — without it the "
            "console loads but no browser can ever sign in"
        )


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
