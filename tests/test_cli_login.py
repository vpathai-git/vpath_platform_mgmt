"""Device-flow login tests: mocked Keycloak endpoints, real flow logic."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from typer.testing import CliRunner

from vpath_platform_mgmt.cli import auth, main

ISSUER = "https://10.0.0.4:30600/keycloak/realms/vpath"
runner = CliRunner()


def keycloak_mock(pending_polls: int) -> httpx.MockTransport:
    state = {"polls": 0}

    def handle(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("openid-configuration"):
            return httpx.Response(
                200,
                json={
                    "device_authorization_endpoint": f"{ISSUER}/device",
                    "token_endpoint": f"{ISSUER}/token",
                },
            )
        if path.endswith("/device"):
            return httpx.Response(
                200,
                json={
                    "device_code": "dev-code",
                    "user_code": "ABCD-EFGH",
                    "verification_uri": f"{ISSUER}/device-verify",
                    "interval": 0,
                },
            )
        if path.endswith("/token"):
            state["polls"] += 1
            if state["polls"] <= pending_polls:
                return httpx.Response(400, json={"error": "authorization_pending"})
            return httpx.Response(
                200, json={"access_token": "jwt-here", "expires_in": 300}
            )
        raise AssertionError(f"unexpected path {path}")

    return httpx.MockTransport(handle)


def mock_client(pending_polls: int = 1) -> httpx.Client:
    return httpx.Client(transport=keycloak_mock(pending_polls))


def test_device_login_polls_until_token() -> None:
    lines: list[str] = []
    tokens = auth.device_login(
        mock_client(pending_polls=2),
        ISSUER,
        "vpath-cli",
        echo=lines.append,
        poll_interval=0,
    )
    assert tokens["access_token"] == "jwt-here"
    assert any("ABCD-EFGH" in line for line in lines)


def test_device_login_surfaces_refusal() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("openid-configuration"):
            return httpx.Response(
                200,
                json={
                    "device_authorization_endpoint": f"{ISSUER}/device",
                    "token_endpoint": f"{ISSUER}/token",
                },
            )
        return httpx.Response(400, json={"error": "unauthorized_client"})

    with pytest.raises(auth.AuthFlowError, match="vpath-cli"):
        auth.device_login(
            httpx.Client(transport=httpx.MockTransport(refuse)),
            ISSUER,
            "vpath-cli",
            echo=lambda _: None,
        )


def test_token_store_roundtrip_and_expiry(tmp_path: Path) -> None:
    stored = auth.save_tokens(
        {"access_token": "abc", "expires_in": 300}, path=tmp_path / "t.json"
    )
    assert auth.load_access_token(stored) == "abc"
    expired = tmp_path / "expired.json"
    expired.write_text(
        json.dumps({"access_token": "old", "expires_at": 1.0}), encoding="utf-8"
    )
    assert auth.load_access_token(expired) is None
    assert auth.load_access_token(tmp_path / "missing.json") is None


def test_login_command_stores_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(main, "make_login_client", lambda verify: mock_client())
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    result = runner.invoke(main.app, ["login", "--issuer", ISSUER])
    assert result.exit_code == 0, result.output
    assert "logged in" in result.output
    assert auth.load_access_token() == "jwt-here"


def test_login_without_issuer_exits_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("VPATH_MGMT_OIDC_ISSUER", raising=False)
    result = runner.invoke(main.app, ["login"])
    assert result.exit_code == main.EXIT_CONFIG


def test_client_prefers_bearer_when_token_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    auth.save_tokens({"access_token": "abc", "expires_in": 300})
    captured: dict[str, str] = {}

    def capture(request: httpx.Request) -> httpx.Response:
        captured.update(dict(request.headers))
        return httpx.Response(
            200, json={"engine": "simulated", "jobs": [], "locks": []}
        )

    monkeypatch.setattr(
        main,
        "make_http_client",
        lambda url: httpx.Client(
            base_url="http://t", transport=httpx.MockTransport(capture)
        ),
    )
    result = runner.invoke(main.app, ["status"])
    assert result.exit_code == 0, result.output
    assert captured.get("authorization") == "Bearer abc"
    assert "x-dev-actor" not in captured
