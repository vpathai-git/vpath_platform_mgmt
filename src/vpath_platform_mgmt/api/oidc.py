"""OIDC bearer-token validation against the platform Keycloak (decision 6).

The Ops API is a resource server: every request carries a Keycloak-issued
JWT, validated here for signature (via the realm's JWKS), issuer, and
expiry. Platform roles come from the token's realm roles — the highest-
ranked of ``server-dev`` / ``app-dev`` / ``admin`` wins; a token with none
of them is not a platform user and is refused.
"""

from __future__ import annotations

import ssl
from dataclasses import dataclass
from typing import Any, Protocol

import jwt

from vpath_platform_mgmt.api.auth import AuthError, Identity
from vpath_platform_mgmt.ops.model import ROLE_RANK, Role

SIGNING_ALGORITHMS = ["RS256"]


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


def _platform_role(claims: dict[str, Any]) -> Role:
    realm_roles = set(claims.get("realm_access", {}).get("roles", []))
    held = [role for role in Role if role.value in realm_roles]
    if not held:
        raise AuthError(
            "token carries no platform role (expected one of "
            f"{[role.value for role in Role]} in realm roles)"
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
        role = _platform_role(claims)
        actor = str(claims.get("preferred_username") or claims.get("sub") or "")
        if not actor:
            raise AuthError("token carries neither preferred_username nor sub")
        return Identity(actor=actor, role=role.value)
