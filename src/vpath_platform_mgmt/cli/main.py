"""``vpath`` — the CLI surface of the platform (docs/USER_ACCESS.md).

Exit codes are a contract for CI (docs/PLATFORM_FUNCTIONS.md, Surfaces):
0 success · 1 job failed · 2 config/connection/validation · 3 refused by
RBAC · 4 lock held · 5 not authenticated.
"""

from __future__ import annotations

import os
from typing import cast

import httpx
import typer

from vpath_platform_mgmt.cli.auth import (
    DEFAULT_CLIENT_ID,
    AuthFlowError,
    device_login,
    load_access_token,
    save_tokens,
)
from vpath_platform_mgmt.cli.client import ApiError, Caller, OpsClient

EXIT_FAILED = 1
EXIT_CONFIG = 2
EXIT_REFUSED = 3
EXIT_LOCKED = 4
EXIT_AUTH = 5

_STATUS_EXIT = {401: EXIT_AUTH, 403: EXIT_REFUSED, 409: EXIT_LOCKED}

DEFAULT_URL = "http://127.0.0.1:8765"

app = typer.Typer(
    name="vpath",
    help=__doc__,
    add_completion=False,
    no_args_is_help=True,
)


def make_http_client(url: str) -> httpx.Client:
    """Build the HTTP client; tests monkeypatch this to go in-process."""
    return httpx.Client(base_url=url, timeout=10.0)


def _client() -> OpsClient:
    url = os.environ.get("VPATH_MGMT_URL", DEFAULT_URL)
    caller = Caller(
        actor=os.environ.get("VPATH_MGMT_ACTOR", "you"),
        role=os.environ.get("VPATH_MGMT_ROLE", "app-dev"),
    )
    return OpsClient(make_http_client(url), caller, bearer=load_access_token())


@app.command()
def login(
    issuer: str = typer.Option(
        "", envvar="VPATH_MGMT_OIDC_ISSUER", help="Keycloak realm issuer URL."
    ),
    client_id: str = typer.Option(
        DEFAULT_CLIENT_ID, envvar="VPATH_MGMT_OIDC_CLIENT_ID"
    ),
    insecure_tls: bool = typer.Option(
        False,
        "--insecure-tls",
        envvar="VPATH_MGMT_OIDC_INSECURE_TLS",
        help="Accept the dev platform's self-signed certificate.",
    ),
) -> None:
    """Log in via the OIDC device flow and store the token locally."""
    if not issuer:
        typer.echo("error: set VPATH_MGMT_OIDC_ISSUER or pass --issuer", err=True)
        raise typer.Exit(code=EXIT_CONFIG)
    http = make_login_client(verify=not insecure_tls)
    try:
        tokens = device_login(http, issuer, client_id, echo=typer.echo)
    except (AuthFlowError, httpx.HTTPError) as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=EXIT_AUTH) from exc
    destination = save_tokens(tokens)
    typer.echo(f"logged in — token stored at {destination}")


def make_login_client(verify: bool) -> httpx.Client:
    """HTTP client for the login flow; tests monkeypatch this."""
    return httpx.Client(timeout=15.0, verify=verify)


def _fail(exc: ApiError) -> None:
    typer.echo(f"error: {exc.detail}", err=True)
    raise typer.Exit(code=_STATUS_EXIT.get(exc.status, EXIT_CONFIG))


def _run_verb(verb: str, target: str, confirm: str = "") -> None:
    client = _client()
    try:
        job_id = client.submit(verb, target, confirm=confirm)
        typer.echo(f"job {job_id} accepted")
        job = client.wait(job_id, on_step=typer.echo)
    except ApiError as exc:
        _fail(exc)
        return
    except httpx.HTTPError as exc:
        typer.echo(f"error: cannot reach the Ops API ({exc})", err=True)
        raise typer.Exit(code=EXIT_CONFIG) from exc
    engine = str(job.get("engine", "?"))
    outcome = str(job["state"])
    if engine == "simulated":
        typer.echo(f"{outcome} — SIMULATED, nothing was deployed to a real server")
    else:
        typer.echo(f"{outcome} (engine: {engine})")
    if outcome != "succeeded":
        raise typer.Exit(code=EXIT_FAILED)


@app.command()
def deploy(app_name: str = typer.Argument(..., metavar="APP")) -> None:
    """Deploy an app whose digest exists in the platform registry."""
    _run_verb("deploy", app_name)


@app.command()
def build(app_name: str = typer.Argument(..., metavar="APP")) -> None:
    """Build an app and push its image to the platform registry."""
    _run_verb("build", app_name)


@app.command()
def uninstall(app_name: str = typer.Argument(..., metavar="APP")) -> None:
    """Uninstall an app and verify it is gone."""
    _run_verb("uninstall", app_name)


@app.command()
def health() -> None:
    """Run the platform health gates and print the verdict."""
    _run_verb("health", "")


@app.command()
def reinstall(
    confirm: str = typer.Option(
        "", help="Type REINSTALL to confirm this destructive action."
    ),
) -> None:
    """Reinstall the server (Admin only; exclusive cluster lock)."""
    _run_verb("reinstall", "server", confirm=confirm)


@app.command()
def status() -> None:
    """Engine, recent jobs, held locks — the console front page in text."""
    try:
        state = _client().state()
    except ApiError as exc:
        _fail(exc)
        return
    except httpx.HTTPError as exc:
        typer.echo(f"error: cannot reach the Ops API ({exc})", err=True)
        raise typer.Exit(code=EXIT_CONFIG) from exc
    typer.echo(f"engine: {state['engine']}")
    jobs = cast("list[dict[str, object]]", state["jobs"])
    for job in jobs[:10]:
        typer.echo(
            f"  {job['id']}  {job['verb']:<10} {job['app']:<16} "
            f"[{job.get('engine', '?')}] {job['state']:<10} {job['step']}"
        )
    locks = cast("list[dict[str, object]]", state["locks"])
    for lock in locks:
        typer.echo(f"lock: {lock['scope']} held by {lock['holder']}")
    if not locks:
        typer.echo("locks: none held")


@app.command()
def logs(job_id: str = typer.Argument(..., metavar="JOB_ID")) -> None:
    """Print the full log of one job."""
    try:
        job = _client().job(job_id)
    except ApiError as exc:
        _fail(exc)
        return
    for line in cast("list[object]", job["log"]):
        typer.echo(str(line))


@app.command()
def doctor() -> None:
    """Layered reachability check; prints the exact fix for the first failure.

    Order per docs/USER_ACCESS.md: overlay → API reachable → auth valid →
    engine mode. The overlay layer reports 'pending' until M0 wires NetBird.
    """
    typer.echo("overlay: skipped — not configured yet (lands with milestone M0)")
    client = _client()
    try:
        state = client.state()
    except ApiError as exc:
        if exc.status == 401:
            typer.echo("api: reachable")
            typer.echo(
                f"auth: FAILED ({client.auth_source}) — run 'vpath login' "
                "(oidc) or set VPATH_MGMT_ACTOR/VPATH_MGMT_ROLE (dev mode)"
            )
            raise typer.Exit(code=EXIT_AUTH) from exc
        typer.echo(f"api: FAILED — {exc.detail}")
        raise typer.Exit(code=EXIT_CONFIG) from exc
    except httpx.HTTPError as exc:
        url = os.environ.get("VPATH_MGMT_URL", DEFAULT_URL)
        typer.echo(f"api: FAILED — cannot reach {url} ({exc})")
        typer.echo("fix: start the console (vpath-console) or set VPATH_MGMT_URL")
        raise typer.Exit(code=EXIT_CONFIG) from exc
    typer.echo("api: reachable")
    typer.echo(f"auth: valid ({client.auth_source})")
    typer.echo(f"engine: {state['engine']}")


def run() -> None:  # pragma: no cover - console-script shim
    """Console-script entry point."""
    app()
