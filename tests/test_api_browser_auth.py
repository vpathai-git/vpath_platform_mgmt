"""Tests for browser sign-in: discovery config, /api/me, and the assets."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from vpath_platform_mgmt.api.app import create_app
from vpath_platform_mgmt.api.auth import (
    BrowserAuthConfig,
    Identity,
    validate_browser_auth,
)
from vpath_platform_mgmt.api.oidc import OidcValidator
from vpath_platform_mgmt.ops import OpsService, SimulatedEngine

DEV = {"X-Dev-Actor": "alice", "X-Dev-Role": "admin"}
ISSUER = "https://10.0.0.4:30600/keycloak/realms/vpath"


def dev_client() -> TestClient:
    return TestClient(create_app(OpsService(SimulatedEngine())))


class StubValidator(OidcValidator):
    """Validator that accepts one fixed bearer and rejects everything else."""

    def __init__(self) -> None:  # noqa: D107 - stub, no config needed
        pass

    def identity(self, authorization: str | None) -> Identity:
        if authorization == "Bearer good":
            return Identity(actor="admin_alain", role="admin")
        from vpath_platform_mgmt.api.auth import AuthError

        raise AuthError("token rejected: stub")


def oidc_client() -> TestClient:
    app = create_app(
        OpsService(SimulatedEngine()),
        auth_mode="oidc",
        oidc_validator=StubValidator(),
        browser_auth=BrowserAuthConfig("oidc", ISSUER, "vpath-console"),
    )
    return TestClient(app)


def test_dev_auth_config_advertises_only_the_mode() -> None:
    assert dev_client().get("/api/auth-config").json() == {"mode": "dev"}


def test_auth_config_is_reachable_without_credentials() -> None:
    """A client that cannot authenticate yet must still learn how."""
    assert oidc_client().get("/api/auth-config").status_code == 200


def test_oidc_auth_config_carries_issuer_and_client_id() -> None:
    body = oidc_client().get("/api/auth-config").json()
    assert body == {
        "mode": "oidc",
        "issuer": ISSUER,
        "client_id": "vpath-console",
    }


def test_auth_config_never_carries_a_secret() -> None:
    body = oidc_client().get("/api/auth-config").json()
    assert not any("secret" in key.lower() for key in body)


def test_me_reports_the_dev_identity() -> None:
    assert dev_client().get("/api/me", headers=DEV).json() == {
        "actor": "alice",
        "role": "admin",
    }


def test_me_refuses_an_unauthenticated_caller() -> None:
    assert dev_client().get("/api/me").status_code == 401


def test_me_reports_the_role_the_token_grants_not_a_requested_one() -> None:
    client = oidc_client()
    headers = {"Authorization": "Bearer good", "X-Dev-Role": "server-dev"}
    assert client.get("/api/me", headers=headers).json() == {
        "actor": "admin_alain",
        "role": "admin",
    }


def test_oidc_console_ignores_dev_headers_entirely() -> None:
    assert oidc_client().get("/api/state", headers=DEV).status_code == 401


def test_auth_js_is_served_as_javascript() -> None:
    response = dev_client().get("/auth.js")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/javascript")
    assert "code_challenge_method" in response.text


def test_hidden_attribute_wins_over_author_styles() -> None:
    """The console swaps identity panels with the ``hidden`` attribute.

    An author rule such as ``.role { display: flex }`` outranks the user
    agent's ``[hidden] { display: none }``, so without an explicit override
    the dev role dropdown stays on screen in oidc mode — visibly offering a
    role picker that the server ignores.
    """
    css = dev_client().get("/console.css").text
    assert "[hidden]" in css
    assert "display: none !important" in css


def test_job_form_picks_an_app_rather_than_accepting_free_text() -> None:
    """Free text let a typo reach the engine as an unknown app name."""
    page = dev_client().get("/").text
    assert '<select id="app"' in page
    assert '<input id="app"' not in page
    assert "fillAppPicker" in dev_client().get("/store.js").text


def test_install_and_uninstall_are_offered_on_the_selected_application() -> None:
    """The store moves apps both ways: onto the server and off it."""
    page = dev_client().get("/").text
    assert "Install on server" in page
    assert "Uninstall from server" in page
    assert 'id="a-state"' in page


def test_every_uninstall_path_asks_first() -> None:
    """One click must not take a live app off the platform unannounced."""
    store = dev_client().get("/store.js").text
    console = dev_client().get("/console.js").text
    assert store.count("confirmUninstall(") == 2  # definition + selected-app path
    assert "confirmUninstall(" in console  # the verb-list path asks too
    assert "ArgoCD tears down" in store


def test_store_asset_is_served_and_loaded() -> None:
    response = dev_client().get("/store.js")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/javascript")
    assert "/store.js" in dev_client().get("/").text


def test_console_page_loads_the_auth_module_before_the_console() -> None:
    page = dev_client().get("/").text
    assert page.index("/auth.js") < page.index("/console.js")


def test_validate_browser_auth_accepts_dev_without_oidc_settings() -> None:
    validate_browser_auth(BrowserAuthConfig("dev"))


@pytest.mark.parametrize(
    ("issuer", "client_id", "missing"),
    [
        ("", "vpath-console", "VPATH_MGMT_OIDC_ISSUER"),
        (ISSUER, "", "VPATH_MGMT_OIDC_CLIENT_ID"),
    ],
)
def test_validate_browser_auth_refuses_an_unusable_login(
    issuer: str, client_id: str, missing: str
) -> None:
    with pytest.raises(ValueError, match=missing):
        validate_browser_auth(BrowserAuthConfig("oidc", issuer, client_id))


def test_create_app_refuses_an_oidc_console_no_browser_could_sign_into() -> None:
    with pytest.raises(ValueError, match="VPATH_MGMT_OIDC_CLIENT_ID"):
        create_app(
            OpsService(SimulatedEngine()),
            auth_mode="oidc",
            oidc_validator=StubValidator(),
            browser_auth=BrowserAuthConfig("oidc", ISSUER, ""),
        )


def test_build_browser_auth_defaults_the_client_id() -> None:
    from vpath_platform_mgmt.api.server import build_browser_auth

    config = build_browser_auth(
        {"VPATH_MGMT_AUTH": "oidc", "VPATH_MGMT_OIDC_ISSUER": ISSUER}
    )
    assert (config.mode, config.issuer, config.client_id) == (
        "oidc",
        ISSUER,
        "vpath-console",
    )


def test_build_browser_auth_honours_an_explicit_client_id() -> None:
    from vpath_platform_mgmt.api.server import build_browser_auth

    config = build_browser_auth({"VPATH_MGMT_OIDC_CLIENT_ID": "other"})
    assert config.client_id == "other"
