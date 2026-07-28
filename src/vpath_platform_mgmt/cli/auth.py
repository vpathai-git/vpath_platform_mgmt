"""Device-flow login for the CLI (docs/USER_ACCESS.md, docs/ACCESS_MECHANISM.md).

``vpath login`` runs the OAuth device-code grant against the platform
Keycloak: the CLI prints a verification URL and code, the user approves in
a browser, and the CLI polls the token endpoint. Tokens are stored in the
user's home, never in the repo.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from pathlib import Path

import httpx

DEVICE_GRANT = "urn:ietf:params:oauth:grant-type:device_code"
DEFAULT_CLIENT_ID = "vpath-cli"
EXPIRY_MARGIN_SECONDS = 30


class AuthFlowError(Exception):
    """The device flow could not complete; message says why."""


def token_path() -> Path:
    """Where the CLI stores its tokens (per-user, outside any repo)."""
    return Path.home() / ".vpath" / "cli-token.json"


def discovery(http: httpx.Client, issuer: str) -> dict[str, str]:
    """Fetch the realm's OIDC discovery document."""
    response = http.get(issuer.rstrip("/") + "/.well-known/openid-configuration")
    response.raise_for_status()
    return dict(response.json())


def _poll_token(
    http: httpx.Client,
    token_endpoint: str,
    device_code: str,
    client_id: str,
    interval: float,
    timeout_seconds: float,
) -> dict[str, object]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        response = http.post(
            token_endpoint,
            data={
                "grant_type": DEVICE_GRANT,
                "device_code": device_code,
                "client_id": client_id,
            },
        )
        if response.status_code == 200:
            return dict(response.json())
        error = str(response.json().get("error", ""))
        if error == "authorization_pending":
            time.sleep(interval)
            continue
        if error == "slow_down":
            interval += 5
            continue
        raise AuthFlowError(f"login refused: {error or response.text}")
    raise AuthFlowError("login timed out — approval not completed in time")


def device_login(
    http: httpx.Client,
    issuer: str,
    client_id: str,
    echo: Callable[[str], None],
    poll_interval: float | None = None,
    timeout_seconds: float = 300.0,
) -> dict[str, object]:
    """Run the device flow; returns the token response."""
    meta = discovery(http, issuer)
    start = http.post(
        meta["device_authorization_endpoint"], data={"client_id": client_id}
    )
    if start.status_code != 200:
        raise AuthFlowError(
            f"device authorization refused ({start.status_code}): {start.text} — "
            f"is the '{client_id}' client configured in the realm?"
        )
    grant = start.json()
    target = grant.get("verification_uri_complete") or grant["verification_uri"]
    echo(f"Open {target}")
    echo(f"and confirm code: {grant['user_code']}")
    interval = (
        poll_interval if poll_interval is not None else float(grant.get("interval", 5))
    )
    return _poll_token(
        http,
        meta["token_endpoint"],
        str(grant["device_code"]),
        client_id,
        interval,
        timeout_seconds,
    )


def save_tokens(tokens: dict[str, object], path: Path | None = None) -> Path:
    """Persist the token response with an absolute expiry stamp."""
    destination = path or token_path()
    destination.parent.mkdir(parents=True, exist_ok=True)
    expires_in = float(str(tokens.get("expires_in", 300)))
    record = {
        "access_token": tokens["access_token"],
        "expires_at": time.time() + expires_in - EXPIRY_MARGIN_SECONDS,
    }
    destination.write_text(json.dumps(record), encoding="utf-8")
    return destination


def load_access_token(path: Path | None = None) -> str | None:
    """Return a still-valid stored access token, or None."""
    source = path or token_path()
    if not source.is_file():
        return None
    try:
        record = json.loads(source.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
    if float(record.get("expires_at", 0)) < time.time():
        return None
    token = record.get("access_token")
    return str(token) if token else None
