"""Tests for the Keycloak relay: forwarding, rewriting, and its config gate."""

from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient

from vpath_platform_mgmt.api.app import create_app
from vpath_platform_mgmt.api.auth import BrowserAuthConfig
from vpath_platform_mgmt.api.kc_proxy import KeycloakProxy
from vpath_platform_mgmt.api.server import build_browser_auth, build_kc_proxy
from vpath_platform_mgmt.ops import OpsService, SimulatedEngine

UPSTREAM = "https://127.0.0.1:18600/keycloak"
PUBLIC = "https://10.0.0.4:30600/keycloak"
DISCOVERY = {
    "issuer": f"{PUBLIC}/realms/vpath",
    "authorization_endpoint": f"{PUBLIC}/realms/vpath/protocol/openid-connect/auth",
    "token_endpoint": f"{PUBLIC}/realms/vpath/protocol/openid-connect/token",
}


def proxy_for(handler) -> KeycloakProxy:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return KeycloakProxy(UPSTREAM, PUBLIC, client=client)


def console(handler) -> TestClient:
    app = create_app(
        OpsService(SimulatedEngine()),
        auth_mode="dev",
        browser_auth=BrowserAuthConfig("dev"),
        kc_proxy=proxy_for(handler),
    )
    return TestClient(app)


def test_relay_requires_both_urls() -> None:
    with pytest.raises(ValueError, match="upstream URL and the public base"):
        KeycloakProxy("", PUBLIC)
    with pytest.raises(ValueError, match="upstream URL and the public base"):
        KeycloakProxy(UPSTREAM, "")


def test_discovery_endpoints_are_rewritten_to_the_console() -> None:
    """The browser must be handed URLs it can actually reach."""
    client = console(lambda _: httpx.Response(200, json=DISCOVERY))
    body = client.get("/keycloak/realms/vpath/.well-known/openid-configuration").json()
    assert body["authorization_endpoint"].startswith("http://testserver/keycloak")
    assert body["token_endpoint"].startswith("http://testserver/keycloak")
    assert "10.0.0.4" not in str(body)


def test_login_page_form_action_is_rewritten() -> None:
    """A pinned hostname in the login form would post to an unreachable host."""
    html = f'<form action="{PUBLIC}/realms/vpath/login-actions/authenticate">'
    client = console(
        lambda _: httpx.Response(200, text=html, headers={"content-type": "text/html"})
    )
    page = client.get("/keycloak/realms/vpath/protocol/openid-connect/auth")
    assert 'action="http://testserver/keycloak/realms/vpath/login-actions' in page.text


def test_redirect_location_is_rewritten() -> None:
    """Keycloak redirects within its own host during the login dance."""
    target = f"{PUBLIC}/realms/vpath/login-actions/required-action"
    client = console(
        lambda _: httpx.Response(302, headers={"location": target}),
    )
    response = client.get(
        "/keycloak/realms/vpath/protocol/openid-connect/auth", follow_redirects=False
    )
    assert response.headers["location"].startswith("http://testserver/keycloak")


def test_upstream_path_and_query_are_preserved() -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["method"] = request.method
        return httpx.Response(200, text="ok", headers={"content-type": "text/plain"})

    client = console(handler)
    client.get("/keycloak/realms/vpath/protocol/openid-connect/auth?client_id=x")
    assert seen["url"].startswith(f"{UPSTREAM}/realms/vpath/protocol")
    assert "client_id=x" in seen["url"]


def test_public_host_is_presented_upstream() -> None:
    """Keycloak derives some URLs from Host; they must come back rewritable."""
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["host"] = request.headers["host"]
        return httpx.Response(200, json={})

    console(handler).get("/keycloak/realms/vpath/token")
    assert seen["host"] == "10.0.0.4:30600"


def test_post_body_is_forwarded() -> None:
    seen: dict[str, bytes] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = request.read()
        return httpx.Response(200, json={})

    console(handler).post("/keycloak/realms/vpath/token", content=b"grant_type=code")
    assert seen["body"] == b"grant_type=code"


def test_binary_responses_are_passed_through_untouched() -> None:
    blob = bytes(range(256))
    client = console(
        lambda _: httpx.Response(
            200, content=blob, headers={"content-type": "image/png"}
        )
    )
    assert client.get("/keycloak/favicon.png").content == blob


def test_console_assets_still_win_over_the_relay() -> None:
    client = console(lambda _: httpx.Response(200, text="upstream"))
    assert client.get("/console.js").status_code == 200
    assert "VpathAuth" in client.get("/console.js").text


def test_secure_cookies_are_storable_over_plain_http() -> None:
    """A Secure cookie is silently dropped on http, so the session never sticks."""
    cookie = "KEYCLOAK_IDENTITY=abc; Version=1; Path=/keycloak/; Secure; HttpOnly"
    client = console(
        lambda _: httpx.Response(200, json={}, headers={"set-cookie": cookie})
    )
    relayed = client.get("/keycloak/realms/vpath/auth").headers["set-cookie"]
    assert "Secure" not in relayed
    assert "HttpOnly" in relayed
    assert "KEYCLOAK_IDENTITY=abc" in relayed


def test_samesite_none_is_downgraded_when_secure_is_dropped() -> None:
    """Browsers reject SameSite=None without Secure; the relay is same-origin."""
    cookie = "AUTH_SESSION_ID=x; Path=/; SameSite=None; Secure"
    client = console(
        lambda _: httpx.Response(200, json={}, headers={"set-cookie": cookie})
    )
    relayed = client.get("/keycloak/realms/vpath/auth").headers["set-cookie"]
    assert "SameSite=Lax" in relayed
    assert "SameSite=None" not in relayed


def test_secure_is_kept_when_the_console_itself_is_https() -> None:
    assert "Secure" in KeycloakProxy.adapt_cookie("a=b; Secure", secure_origin=True)


def test_every_cookie_survives_not_just_the_last() -> None:
    """Keycloak sets several per response; a dict would keep only one."""

    pair = [
        ("set-cookie", "one=1; Path=/"),
        ("set-cookie", "two=2; Path=/"),
    ]
    relayed = console(lambda _: httpx.Response(200, json={}, headers=pair)).get(
        "/keycloak/realms/vpath/auth"
    )
    cookies = [v for k, v in relayed.headers.multi_items() if k == "set-cookie"]
    assert len(cookies) == 2


def test_hsts_is_not_relayed_onto_the_console_origin() -> None:
    """Upstream is TLS; forcing HTTPS on the console's host would break it."""
    client = console(
        lambda _: httpx.Response(
            200,
            json={},
            headers={"strict-transport-security": "max-age=31536000"},
        )
    )
    assert "strict-transport-security" not in client.get("/keycloak/x").headers


def test_relay_is_absent_unless_configured() -> None:
    assert build_kc_proxy({}) is None


def test_relay_config_requires_the_public_base() -> None:
    with pytest.raises(ValueError, match="VPATH_MGMT_KC_PROXY_PUBLIC"):
        build_kc_proxy({"VPATH_MGMT_KC_PROXY_UPSTREAM": UPSTREAM})


def test_browser_issuer_overrides_only_the_browser_facing_url() -> None:
    """The validator must keep matching tokens against the real issuer."""
    real = "https://10.0.0.4:30600/keycloak/realms/vpath"
    local = "http://127.0.0.1:8765/keycloak/realms/vpath"
    config = build_browser_auth(
        {
            "VPATH_MGMT_AUTH": "oidc",
            "VPATH_MGMT_OIDC_ISSUER": real,
            "VPATH_MGMT_OIDC_BROWSER_ISSUER": local,
        }
    )
    assert config.issuer == local
