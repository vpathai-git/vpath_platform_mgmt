"""``vpath app`` — register app repositories so they can be sent to a server.

A thin shell over ``ops.app_registry``: fetch a repo, write the entry, report
what happened. Every refusal comes from the registry, so the CLI and the later
console action cannot disagree about what is allowed.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import typer

from vpath_platform_mgmt.ops import repo_fetch
from vpath_platform_mgmt.ops.app_registry import (
    AppRegistry,
    Generated,
    RegistryError,
    detect_runtime,
)

EXIT_CONFIG = 2

app = typer.Typer(name="app", help=__doc__, no_args_is_help=True)


def apps_root() -> Path:
    """This repository's ``apps/`` folder."""
    return Path(__file__).resolve().parents[3] / "apps"


def _fail(message: str) -> None:
    typer.echo(f"error: {message}", err=True)
    raise typer.Exit(code=EXIT_CONFIG)


@app.command("add")
def add(
    url: str = typer.Argument(..., help="repository URL, e.g. github.com/org/repo"),
    ref: str = typer.Option("main", help="branch or tag to register"),
    name: str = typer.Option("", help="app name (only when generating a manifest)"),
    port: int = typer.Option(0, help="service port; never assigned automatically"),
    base_path: str = typer.Option("", help="URL prefix the app is served under"),
    title: str = typer.Option("", help="sidebar title"),
    description: str = typer.Option("", help="sidebar description"),
    icon: str = typer.Option("", help="sidebar icon name"),
    runtime: str = typer.Option("", help="node or python; detected when omitted"),
    replace: bool = typer.Option(False, help="overwrite an existing entry"),
) -> None:
    """Register one repository as an app in ``apps/``."""
    try:
        fetched = repo_fetch.fetch(url, ref)
    except repo_fetch.FetchError as exc:
        _fail(str(exc))
        return

    try:
        generate = _generate_from(
            fetched.path, name, port, base_path, title, description, icon, runtime
        )
        result = AppRegistry(apps_root()).register(
            repo=fetched.repo,
            ref=fetched.ref,
            commit=fetched.commit,
            tree=fetched.path,
            generate=generate,
            replace=replace,
        )
    except RegistryError as exc:
        _fail(str(exc))
        return
    finally:
        shutil.rmtree(fetched.path, ignore_errors=True)

    typer.echo(
        f"registered {result.name} ({result.manifest_origin} manifest) "
        f"at {fetched.commit[:12]} — {result.directory}"
    )


def _generate_from(
    tree: Path,
    name: str,
    port: int,
    base_path: str,
    title: str,
    description: str,
    icon: str,
    runtime: str,
) -> Generated | None:
    """Build the generation spec, or None when the repo describes itself.

    A repo that ships a manifest needs nothing from the flags; the registry
    refuses them, so returning None here keeps that one decision in one place.
    """
    if (tree / "vpath-app.yaml").is_file():
        return None
    missing = [
        flag
        for flag, value in (
            ("--name", name),
            ("--port", port),
            ("--base-path", base_path),
            ("--title", title),
        )
        if not value
    ]
    if missing:
        raise RegistryError(
            "this repository ships no vpath-app.yaml, so one must be generated "
            "— missing " + ", ".join(missing)
        )
    return Generated(
        name=name,
        port=port,
        base_path=base_path,
        title=title,
        description=description,
        icon=icon,
        runtime=runtime or detect_runtime(tree),
    )


@app.command("refresh")
def refresh(
    name: str = typer.Argument(..., help="registered app to re-fetch"),
    ref: str = typer.Option("", help="ref to fetch; the recorded one by default"),
) -> None:
    """Re-fetch a registered app, adopting an upstream manifest if it appeared."""
    registry = AppRegistry(apps_root())
    recorded = next((e for e in registry.entries() if e["name"] == name), None)
    if recorded is None:
        _fail(f"'{name}' is not registered here")
        return

    try:
        fetched = repo_fetch.fetch(
            str(recorded.get("repo", "")), ref or str(recorded.get("ref", "main"))
        )
    except repo_fetch.FetchError as exc:
        _fail(str(exc))
        return
    try:
        result = registry.refresh(name, fetched.path, fetched.commit)
    except RegistryError as exc:
        _fail(str(exc))
        return
    finally:
        shutil.rmtree(fetched.path, ignore_errors=True)

    typer.echo(
        f"refreshed {result.name} to {result.commit[:12]} "
        f"({result.manifest_origin} manifest)"
    )


@app.command("list")
def list_apps() -> None:
    """Show every registered app and where it came from."""
    entries = AppRegistry(apps_root()).entries()
    if not entries:
        typer.echo("no repositories registered")
        return
    for entry in entries:
        typer.echo(
            f"{entry['name']:<34} {str(entry.get('manifest_origin', '?')):<10} "
            f"{str(entry.get('commit', '?'))[:12]:<14} {entry.get('repo', '?')}"
        )
