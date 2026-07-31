"""``vpath app`` — register app repositories so they can be sent to a server.

A thin shell over ``ops.app_registry``: fetch a repo, write the entry, report
what happened. Every refusal comes from the registry, so the CLI and the later
console action cannot disagree about what is allowed.
"""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

import httpx
import typer

from vpath_platform_mgmt.ops.bundle import BundleError, bundle
from vpath_platform_mgmt.cli.client import ApiError
from vpath_platform_mgmt.ops import repo_fetch, repo_probe
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
        source = _inspect(url, ref)
    except repo_fetch.FetchError as exc:
        _fail(str(exc))
        return

    try:
        generate = _generate_from(
            source.tree, name, port, base_path, title, description, icon, runtime
        )
        result = AppRegistry(apps_root()).register(
            repo=source.repo,
            ref=ref,
            commit=source.commit,
            tree=source.tree,
            generate=generate,
            replace=replace,
        )
    except RegistryError as exc:
        _fail(str(exc))
        return
    finally:
        shutil.rmtree(source.tree, ignore_errors=True)

    typer.echo(
        f"registered {result.name} ({result.manifest_origin} manifest) "
        f"at {source.commit[:12]} via {source.how} — {result.directory}"
    )


@dataclass(frozen=True)
class Inspected:
    """A directory the registry can read, and where it came from."""

    tree: Path
    repo: str
    commit: str
    how: str


def _inspect(url: str, ref: str) -> Inspected:
    """Read what registration needs: GitHub's API when it can, else a clone.

    Registration only needs a manifest and a runtime hint, so a GitHub repo is
    read through gh — which carries the operator's auth, so INTERNAL repos work
    — and never cloned. Cloning stays for other hosts, where there is no API to
    ask.
    """
    try:
        slug = repo_probe.parse_slug(url)
    except repo_fetch.FetchError:
        fetched = repo_fetch.fetch(url, ref)
        return Inspected(fetched.path, fetched.repo, fetched.commit, "clone")

    probed = repo_probe.probe(url, ref)
    tree = Path(tempfile.mkdtemp(prefix="vpath-probe-"))
    repo_probe.materialise(probed, tree)
    return Inspected(tree, probed.repo_url, probed.commit, f"gh api {slug}")


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
        source = _inspect(
            str(recorded.get("repo", "")), ref or str(recorded.get("ref", "main"))
        )
    except repo_fetch.FetchError as exc:
        _fail(str(exc))
        return
    try:
        result = registry.refresh(name, source.tree, source.commit)
    except RegistryError as exc:
        _fail(str(exc))
        return
    finally:
        shutil.rmtree(source.tree, ignore_errors=True)

    typer.echo(
        f"refreshed {result.name} to {result.commit[:12]} "
        f"({result.manifest_origin} manifest)"
    )


@app.command("send")
def send(
    name: str = typer.Argument(..., help="registered app to send to the server"),
    replace: bool = typer.Option(False, help="overwrite the app's source there"),
) -> None:
    """Send a registered app's source to the server at its recorded commit."""
    entry = _registered(name)
    slug, commit = _sending_facts(name, entry)

    workspace = Path(tempfile.mkdtemp(prefix="vpath-send-"))
    try:
        tree = repo_probe.download_tree(slug, commit, workspace)
        _place_registered_files(name, tree)
        archive = bundle(tree)
    except (repo_fetch.FetchError, BundleError, RegistryError) as exc:
        shutil.rmtree(workspace, ignore_errors=True)
        _fail(str(exc))
        return

    provenance = {
        "repo": str(entry.get("repo", "")),
        "ref": str(entry.get("ref", "")),
        "commit": commit,
        "dirty": "false",  # a fetched commit cannot be dirty
    }
    try:
        summary = _push(name, archive, provenance, replace)
    finally:
        shutil.rmtree(workspace, ignore_errors=True)

    typer.echo(
        f"sent {name} at {commit[:12]}: {summary.get('file_count')} files to "
        f"{summary.get('target')} (replaced={summary.get('replaced')})"
    )


def _registered(name: str) -> dict[str, object]:
    entry = next(
        (e for e in AppRegistry(apps_root()).entries() if e["name"] == name), None
    )
    if entry is None:
        _fail(f"'{name}' is not registered here — run 'vpath app add' first")
        raise typer.Exit(code=EXIT_CONFIG)  # pragma: no cover - _fail exits
    return entry


def _sending_facts(name: str, entry: dict[str, object]) -> tuple[str, str]:
    """The slug and commit to send, refusing when provenance cannot say."""
    commit = str(entry.get("commit", ""))
    if not commit:
        _fail(f"'{name}' has no recorded commit — run 'vpath app refresh {name}'")
    try:
        return repo_probe.parse_slug(str(entry.get("repo", ""))), commit
    except repo_fetch.FetchError as exc:
        _fail(f"{exc} — sending a non-GitHub repository is not supported yet")
        raise typer.Exit(code=EXIT_CONFIG)  # pragma: no cover - _fail exits


REGISTERED_FILES = ("vpath-app.yaml", "vpath-source.yaml")


def _place_registered_files(name: str, tree: Path, apps: Path | None = None) -> None:
    """Put the registered manifest and its provenance in the payload.

    The server refuses an upload without a manifest, and a generated one lives
    only here -- so it has to travel. Provenance travels with it so the
    checkout can say which commit it holds without asking this repository,
    which is what lets a resumed publish skip a send that already happened.
    """
    root = apps if apps is not None else apps_root()
    for filename in REGISTERED_FILES:
        registered = root / name / filename
        if not registered.is_file():
            raise RegistryError(f"'{name}' has no {filename} at {registered}")
        shutil.copyfile(registered, tree / filename)


def _push(
    name: str, archive: bytes, provenance: dict[str, str], replace: bool
) -> dict[str, object]:
    """Hand the payload to the existing source endpoint, or say why not."""
    from vpath_platform_mgmt.cli.main import _client

    try:
        return _client().push_source(name, archive, provenance, replace)
    except ApiError as exc:
        if exc.status == 409 and "checkout" in exc.detail:
            _fail(
                f"{exc.detail} — sending materializes into a server checkout, so "
                "it only works from a console running on the box"
            )
        _fail(f"the server refused the upload ({exc.status}): {exc.detail}")
        raise typer.Exit(code=EXIT_CONFIG)  # pragma: no cover - _fail exits
    except httpx.HTTPError as exc:
        _fail(f"cannot reach the Ops API ({exc})")
        raise typer.Exit(code=EXIT_CONFIG)  # pragma: no cover - _fail exits


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
