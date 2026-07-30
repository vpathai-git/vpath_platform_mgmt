"""Tests for sending a registered app's source to the server."""

from __future__ import annotations

import io
import tarfile
from pathlib import Path

import pytest
import typer

from vpath_platform_mgmt.cli import app_cmds
from vpath_platform_mgmt.ops.app_registry import RegistryError

MANIFEST = "apiVersion: vpath/v1\nmetadata:\n  name: vpath-thing\n"


@pytest.fixture()
def registered(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """An apps/ root holding one registered app."""
    apps = tmp_path / "apps"
    (apps / "vpath-thing").mkdir(parents=True)
    (apps / "vpath-thing" / "vpath-app.yaml").write_text(MANIFEST, encoding="utf-8")
    (apps / "vpath-thing" / "vpath-source.yaml").write_text(
        "repo: https://github.com/org/thing.git\n"
        "ref: main\ncommit: abc123def456\nmanifest_origin: generated\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(app_cmds, "apps_root", lambda: apps)
    return apps


def test_the_registered_manifest_travels_with_the_source(
    registered: Path, tmp_path: Path
) -> None:
    """A generated manifest lives only here, and the server demands one."""
    tree = tmp_path / "tree"
    tree.mkdir()
    (tree / "index.js").write_text("//", encoding="utf-8")

    app_cmds._place_manifest("vpath-thing", tree, "generated")

    assert (tree / "vpath-app.yaml").read_text(encoding="utf-8") == MANIFEST


def test_placing_a_manifest_that_is_not_there_is_refused(
    registered: Path, tmp_path: Path
) -> None:
    (registered / "vpath-thing" / "vpath-app.yaml").unlink()
    with pytest.raises(RegistryError, match="has no manifest"):
        app_cmds._place_manifest("vpath-thing", tmp_path, "generated")


def test_an_upstream_manifest_in_the_repo_is_overwritten_by_the_registered_one(
    registered: Path, tmp_path: Path
) -> None:
    """The server must materialize the manifest this console showed."""
    tree = tmp_path / "tree"
    tree.mkdir()
    (tree / "vpath-app.yaml").write_text("stale: yes\n", encoding="utf-8")

    app_cmds._place_manifest("vpath-thing", tree, "upstream")

    assert (tree / "vpath-app.yaml").read_text(encoding="utf-8") == MANIFEST


def test_sending_facts_come_from_provenance(registered: Path) -> None:
    entry = app_cmds._registered("vpath-thing")
    slug, commit = app_cmds._sending_facts("vpath-thing", entry)
    assert slug == "org/thing"
    assert commit == "abc123def456"


def test_a_non_github_repo_is_refused_with_a_reason(
    registered: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (registered / "vpath-thing" / "vpath-source.yaml").write_text(
        "repo: https://gitea.internal/org/thing.git\nref: main\ncommit: abc123\n",
        encoding="utf-8",
    )
    entry = app_cmds._registered("vpath-thing")
    with pytest.raises(typer.Exit):
        app_cmds._sending_facts("vpath-thing", entry)


def test_an_unregistered_app_cannot_be_sent(registered: Path) -> None:
    with pytest.raises(typer.Exit):
        app_cmds._registered("vpath-absent")


def test_sending_from_a_workstation_console_explains_itself(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A 409 about the checkout is the on-box constraint, not a mystery."""
    from vpath_platform_mgmt.cli import main as cli_main
    from vpath_platform_mgmt.cli.client import ApiError

    class Refusing:
        def push_source(self, *args: object, **kwargs: object) -> dict[str, object]:
            raise ApiError(409, "no server checkout configured — cannot materialize")

    monkeypatch.setattr(cli_main, "_client", lambda: Refusing())
    with pytest.raises(typer.Exit):
        app_cmds._push("vpath-thing", b"tar", {}, False)


def test_bundle_of_the_prepared_tree_carries_the_manifest(
    registered: Path, tmp_path: Path
) -> None:
    """End of the chain: what would actually be uploaded."""
    from vpath_platform_mgmt.cli.bundle import bundle

    tree = tmp_path / "tree"
    tree.mkdir()
    (tree / "index.js").write_text("//", encoding="utf-8")
    (tree / ".git").mkdir()
    (tree / ".git" / "config").write_text("x", encoding="utf-8")
    app_cmds._place_manifest("vpath-thing", tree, "generated")

    with tarfile.open(fileobj=io.BytesIO(bundle(tree))) as packed:
        names = packed.getnames()

    assert "vpath-app.yaml" in names
    assert "index.js" in names
    assert not any(name.startswith(".git") for name in names)  # never ship .git
