"""OIDC bearer-token validation against the platform Keycloak (decision 6).

The Ops API is a resource server: every request carries a Keycloak-issued
JWT, validated here for signature (via the realm's JWKS), issuer, and
expiry. Platform roles come from the token's realm roles — the highest-
ranked of ``server-dev`` / ``app-dev`` / ``admin`` wins; a token with none
of them is not a platform user and is refused.
"""

from __future__ import annotations

import ssl
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

import jwt

from vpath_platform_mgmt.api.auth import AuthError, Identity
from vpath_platform_mgmt.ops.model import ROLE_RANK, Role

SIGNING_ALGORITHMS = ["RS256"]

# The VPath realm authorizes by GROUP, not realm role — verified against the
# live realm on 2026-07-28, where the only realm roles are Keycloak defaults
# and tokens carry full group paths such as ["/vpath-admins"]. Realm roles are
# still honored when present, so a role-based realm keeps working unchanged.
DEFAULT_GROUP_ROLES: dict[str, Role] = {
    "/vpath-admins": Role.ADMIN,
    "/kp-maintainers": Role.APP_DEV,
    "/kp-users": Role.SERVER_DEV,
}


class SigningKeyProvider(Protocol):
    """Resolves the key a token was signed with (PyJWKClient-compatible)."""

    def get_signing_key_from_jwt(self, token: str) -> Any:
        """Return an object whose ``.key`` verifies the token."""
        ...  # pragma: no cover - protocol signature


@dataclass(frozen=True)
class OidcConfig:
    """Where and how to validate tokens.

    ``insecure_tls`` exists for the self-signed dev platform only and must
    be set explicitly — there is no silent fallback to unverified TLS.
    """

    issuer: str
    audience: str | None = None
    insecure_tls: bool = False
    group_roles: Mapping[str, Role] = field(
        default_factory=lambda: dict(DEFAULT_GROUP_ROLES)
    )

    @property
    def jwks_url(self) -> str:
        """Keycloak realm JWKS endpoint derived from the issuer."""
        return self.issuer.rstrip("/") + "/protocol/openid-connect/certs"


def make_jwk_client(config: OidcConfig) -> SigningKeyProvider:
    """Build the JWKS client; explicit opt-in for self-signed platforms."""
    if config.insecure_tls:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return jwt.PyJWKClient(config.jwks_url, ssl_context=context)
    return jwt.PyJWKClient(config.jwks_url)


def _bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthError("missing bearer token — run 'vpath login'")
    return authorization.split(" ", 1)[1].strip()


def _normalized_groups(claims: dict[str, Any]) -> set[str]:
    raw = claims.get("groups", []) or []
    paths = (str(group) for group in raw)
    return {path if path.startswith("/") else "/" + path for path in paths}


def _platform_role(claims: dict[str, Any], group_roles: Mapping[str, Role]) -> Role:
    """Highest platform role the token grants, via realm roles or groups."""
    realm_roles = set(claims.get("realm_access", {}).get("roles", []))
    held = [role for role in Role if role.value in realm_roles]
    groups = _normalized_groups(claims)
    held.extend(role for path, role in group_roles.items() if path in groups)
    if not held:
        raise AuthError(
            "token carries no platform role: none of the realm roles "
            f"{[role.value for role in Role]} and none of the mapped groups "
            f"{sorted(group_roles)} are present"
        )
    return max(held, key=lambda role: ROLE_RANK[role])


class OidcValidator:
    """Validates bearer tokens and derives the caller's identity."""

    def __init__(
        self, config: OidcConfig, jwk_client: SigningKeyProvider | None = None
    ) -> None:
        self._config = config
        self._jwks = jwk_client or make_jwk_client(config)

    def identity(self, authorization: str | None) -> Identity:
        """Validate the Authorization header; raise ``AuthError`` if invalid."""
        token = _bearer_token(authorization)
        try:
            signing_key = self._jwks.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=SIGNING_ALGORITHMS,
                issuer=self._config.issuer,
                audience=self._config.audience,
                options={
                    "require": ["exp", "iss"],
                    "verify_aud": self._config.audience is not None,
                },
            )
        except jwt.PyJWTError as exc:
            raise AuthError(f"token rejected: {exc}") from exc
        role = _platform_role(claims, self._config.group_roles)
        actor = str(claims.get("preferred_username") or claims.get("sub") or "")
        if not actor:
            raise AuthError("token carries neither preferred_username nor sub")
        return Identity(actor=actor, role=role.value)
