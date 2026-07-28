"""OIDC validation tests: real RS256 tokens against a stubbed JWKS."""

from __future__ import annotations

import time
from types import SimpleNamespace
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from vpath_platform_mgmt.api import create_app
from vpath_platform_mgmt.api.auth import AuthError
from vpath_platform_mgmt.api.oidc import OidcConfig, OidcValidator
from vpath_platform_mgmt.ops import OpsService, SimulatedEngine

ISSUER = "https://10.0.0.4:30600/keycloak/realms/vpath"

PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PUBLIC_KEY = PRIVATE_KEY.public_key()


class FakeJwks:
    """Stands in for PyJWKClient: always returns the test public key."""

    def get_signing_key_from_jwt(self, token: str) -> Any:
        return SimpleNamespace(key=PUBLIC_KEY)


def make_token(
    roles: list[str],
    username: str = "klemens",
    issuer: str = ISSUER,
    expires_in: float = 300.0,
) -> str:
    claims = {
        "iss": issuer,
        "sub": "user-uuid",
        "preferred_username": username,
        "exp": time.time() + expires_in,
        "realm_access": {"roles": ["default-roles-vpath", *roles]},
    }
    return jwt.encode(claims, PRIVATE_KEY, algorithm="RS256")


@pytest.fixture()
def validator() -> OidcValidator:
    return OidcValidator(OidcConfig(issuer=ISSUER), jwk_client=FakeJwks())


def test_valid_token_yields_identity(validator: OidcValidator) -> None:
    identity = validator.identity(f"Bearer {make_token(['app-dev'])}")
    assert identity.actor == "klemens"
    assert identity.role == "app-dev"


def test_highest_platform_role_wins(validator: OidcValidator) -> None:
    token = make_token(["app-dev", "admin", "server-dev"])
    assert validator.identity(f"Bearer {token}").role == "admin"


def test_token_without_platform_role_is_refused(validator: OidcValidator) -> None:
    with pytest.raises(AuthError, match="no platform role"):
        validator.identity(f"Bearer {make_token([])}")


def test_expired_token_is_refused(validator: OidcValidator) -> None:
    token = make_token(["app-dev"], expires_in=-60.0)
    with pytest.raises(AuthError, match="token rejected"):
        validator.identity(f"Bearer {token}")


def test_wrong_issuer_is_refused(validator: OidcValidator) -> None:
    token = make_token(["app-dev"], issuer="https://evil.example/realm")
    with pytest.raises(AuthError, match="token rejected"):
        validator.identity(f"Bearer {token}")


def test_missing_bearer_is_refused(validator: OidcValidator) -> None:
    with pytest.raises(AuthError, match="vpath login"):
        validator.identity(None)


def test_jwks_url_derived_from_issuer() -> None:
    config = OidcConfig(issuer=ISSUER + "/")
    assert config.jwks_url == ISSUER + "/protocol/openid-connect/certs"


def test_oidc_app_accepts_token_and_runs_verbs(validator: OidcValidator) -> None:
    service = OpsService(SimulatedEngine())
    client = TestClient(create_app(service, auth_mode="oidc", oidc_validator=validator))
    bearer = {"Authorization": f"Bearer {make_token(['admin'])}"}
    assert client.get("/api/state", headers=bearer).status_code == 200
    accepted = client.post(
        "/api/jobs",
        json={"verb": "reinstall", "app": "server", "confirm": "REINSTALL"},
        headers=bearer,
    )
    assert accepted.status_code == 202


def test_oidc_app_rejects_dev_headers_and_bad_tokens(
    validator: OidcValidator,
) -> None:
    service = OpsService(SimulatedEngine())
    client = TestClient(create_app(service, auth_mode="oidc", oidc_validator=validator))
    dev_headers = {"X-Dev-Actor": "eve", "X-Dev-Role": "admin"}
    assert client.get("/api/state", headers=dev_headers).status_code == 401
    stale = {"Authorization": f"Bearer {make_token(['admin'], expires_in=-1)}"}
    assert client.get("/api/state", headers=stale).status_code == 401


def test_oidc_mode_with_real_engine_is_allowed(validator: OidcValidator) -> None:
    class RealishEngine(SimulatedEngine):
        name = "local"

    app = create_app(
        OpsService(RealishEngine()), auth_mode="oidc", oidc_validator=validator
    )
    assert app.title
