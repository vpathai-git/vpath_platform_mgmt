"""Tests for turning a fetched app repository into a registered app."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from vpath_platform_mgmt.ops.app_registry import (
    GENERATED,
    MANIFEST_NAME,
    PROVENANCE_NAME,
    UPSTREAM,
    AppRegistry,
    Generated,
    RegistryError,
    detect_runtime,
)

COMMIT = "08f7f9e8c753a2ad2f71ecea43dabbc5ac58b0eb"
REPO = "https://github.com/vpathai-git/example.git"

UPSTREAM_MANIFEST = """
apiVersion: vpath/v1
kind: VpathApp
metadata:
  name: vpath-authored
spec:
  type: web
  basePath: /authored
  port: 3099
  ui:
    title: Authored Upstream
"""


def tree(tmp_path: Path, manifest: str = "", runtime_file: str = "") -> Path:
    source = tmp_path / "clone"
    source.mkdir(exist_ok=True)
    if manifest:
        (source / MANIFEST_NAME).write_text(manifest, encoding="utf-8")
    if runtime_file:
        (source / runtime_file).write_text("{}", encoding="utf-8")
    return source


def registry(tmp_path: Path) -> AppRegistry:
    apps = tmp_path / "apps"
    apps.mkdir()
    return AppRegistry(apps)


def spec(**over: object) -> Generated:
    fields: dict[str, object] = {
        "name": "vpath-knowledge-publish",
        "port": 3040,
        "base_path": "/knowledge-publish",
        "title": "Knowledge Publish",
        "runtime": "node",
    }
    fields.update(over)
    return Generated(**fields)  # type: ignore[arg-type]


def test_an_upstream_manifest_is_taken_as_authored(tmp_path: Path) -> None:
    """The app repo owns its identity; we copy, never merge."""
    result = registry(tmp_path).register(
        REPO, "main", COMMIT, tree(tmp_path, UPSTREAM_MANIFEST)
    )
    assert result.name == "vpath-authored"  # from metadata.name, not a flag
    assert result.manifest_origin == UPSTREAM
    written = (result.directory / MANIFEST_NAME).read_text(encoding="utf-8")
    assert written == UPSTREAM_MANIFEST  # byte for byte


def test_flags_are_refused_when_the_repo_already_declares_itself(
    tmp_path: Path,
) -> None:
    with pytest.raises(RegistryError, match="taken as .*authored|do not apply"):
        registry(tmp_path).register(
            REPO, "main", COMMIT, tree(tmp_path, UPSTREAM_MANIFEST), generate=spec()
        )


def test_a_repo_without_a_manifest_gets_one_generated(tmp_path: Path) -> None:
    result = registry(tmp_path).register(
        REPO, "main", COMMIT, tree(tmp_path), generate=spec()
    )
    assert result.manifest_origin == GENERATED
    manifest = yaml.safe_load(
        (result.directory / MANIFEST_NAME).read_text(encoding="utf-8")
    )
    assert manifest["metadata"]["name"] == "vpath-knowledge-publish"
    assert manifest["spec"]["port"] == 3040
    # Derived, never asked for:
    assert manifest["spec"]["image"] == "vpath-knowledge-publish"
    assert manifest["spec"]["auth"]["oidcClient"] == "vpath-knowledge-publish"
    assert manifest["spec"]["health"]["readiness"] == "/knowledge-publish/api/healthz"
    assert manifest["spec"]["build"]["hash"]["dirs"] == [
        "apps_infra/apps/vpath-knowledge-publish"
    ]


def test_registering_without_a_manifest_or_flags_is_refused(tmp_path: Path) -> None:
    """The ADK case that started this: a repo that is not an app."""
    with pytest.raises(RegistryError, match="must be generated"):
        registry(tmp_path).register(REPO, "main", COMMIT, tree(tmp_path))


def test_provenance_records_where_it_came_from(tmp_path: Path) -> None:
    result = registry(tmp_path).register(
        REPO, "main", COMMIT, tree(tmp_path), generate=spec()
    )
    recorded = yaml.safe_load(
        (result.directory / PROVENANCE_NAME).read_text(encoding="utf-8")
    )
    assert recorded["repo"] == REPO
    assert recorded["commit"] == COMMIT
    assert recorded["manifest_origin"] == GENERATED
    assert recorded["added_at"].endswith("Z")


def test_a_second_registration_needs_replace(tmp_path: Path) -> None:
    store = registry(tmp_path)
    store.register(REPO, "main", COMMIT, tree(tmp_path), generate=spec())
    with pytest.raises(RegistryError, match="already registered"):
        store.register(REPO, "main", COMMIT, tree(tmp_path), generate=spec())
    store.register(REPO, "main", COMMIT, tree(tmp_path), generate=spec(), replace=True)


def test_a_port_another_app_holds_is_refused_by_name(tmp_path: Path) -> None:
    """Ports are never auto-assigned, so a collision must be loud."""
    store = registry(tmp_path)
    store.register(REPO, "main", COMMIT, tree(tmp_path), generate=spec())
    with pytest.raises(RegistryError, match="already used by 'vpath-knowledge"):
        store.register(
            REPO,
            "main",
            COMMIT,
            tree(tmp_path),
            generate=spec(name="vpath-other", base_path="/other"),
        )


def test_an_unusable_name_is_refused(tmp_path: Path) -> None:
    with pytest.raises(RegistryError, match="not a usable app name"):
        registry(tmp_path).register(
            REPO, "main", COMMIT, tree(tmp_path), generate=spec(name="Bad Name")
        )


def test_refresh_adopts_an_upstream_manifest_that_appeared(tmp_path: Path) -> None:
    """A generated manifest is provisional; upstream takes over silently."""
    store = registry(tmp_path)
    store.register(REPO, "main", COMMIT, tree(tmp_path), generate=spec())

    later = tmp_path / "clone2"
    later.mkdir()
    (later / MANIFEST_NAME).write_text(
        UPSTREAM_MANIFEST.replace("vpath-authored", "vpath-knowledge-publish"),
        encoding="utf-8",
    )
    refreshed = store.refresh("vpath-knowledge-publish", later, "beef1234")

    assert refreshed.manifest_origin == UPSTREAM
    recorded = yaml.safe_load(
        (refreshed.directory / PROVENANCE_NAME).read_text(encoding="utf-8")
    )
    assert recorded["commit"] == "beef1234"
    assert recorded["repo"] == REPO  # carried over, not lost


def test_refreshing_something_unregistered_is_refused(tmp_path: Path) -> None:
    with pytest.raises(RegistryError, match="not registered here"):
        registry(tmp_path).refresh("vpath-absent", tmp_path, COMMIT)


def test_entries_lists_registered_apps_with_provenance(tmp_path: Path) -> None:
    store = registry(tmp_path)
    store.register(REPO, "main", COMMIT, tree(tmp_path), generate=spec())
    listed = store.entries()
    assert listed[0]["name"] == "vpath-knowledge-publish"
    assert listed[0]["manifest_origin"] == GENERATED


def test_provenance_records_which_directory_of_the_repo_is_the_app(
    tmp_path: Path,
) -> None:
    """A later refresh has to look in the same place, and only this says where."""
    result = registry(tmp_path).register(
        REPO,
        "main",
        COMMIT,
        tree(tmp_path, UPSTREAM_MANIFEST),
        path="examples/vpath-knowledge-builder",
    )

    recorded = yaml.safe_load(
        (result.directory / PROVENANCE_NAME).read_text(encoding="utf-8")
    )
    assert recorded["path"] == "examples/vpath-knowledge-builder"


def test_a_repository_that_is_itself_the_app_records_an_empty_path(
    tmp_path: Path,
) -> None:
    result = registry(tmp_path).register(
        REPO, "main", COMMIT, tree(tmp_path, UPSTREAM_MANIFEST)
    )

    recorded = yaml.safe_load(
        (result.directory / PROVENANCE_NAME).read_text(encoding="utf-8")
    )
    assert recorded["path"] == ""


def test_refresh_keeps_the_directory_the_app_was_registered_from(
    tmp_path: Path,
) -> None:
    store = registry(tmp_path)
    result = store.register(
        REPO,
        "main",
        COMMIT,
        tree(tmp_path, UPSTREAM_MANIFEST),
        path="examples/vpath-knowledge-builder",
    )

    later = tmp_path / "clone2"
    later.mkdir()
    store.refresh(result.name, later, "d" * 40)

    recorded = yaml.safe_load(
        (result.directory / PROVENANCE_NAME).read_text(encoding="utf-8")
    )
    assert recorded["path"] == "examples/vpath-knowledge-builder"
    assert recorded["commit"] == "d" * 40


def test_refresh_of_a_pre_task_3_entry_reads_no_path_as_the_repository_root(
    tmp_path: Path,
) -> None:
    """Every app registered before this feature has no ``path`` key at all.

    Writes a ``vpath-source.yaml`` exactly as it looked before this task --
    with no ``path`` key -- directly into the app's directory, then refreshes
    it. ``previous.get("path", "")`` must keep reading that as the repository
    root; a future ``previous["path"]`` would raise ``KeyError`` here.
    """
    apps = tmp_path / "apps"
    apps.mkdir()
    store = AppRegistry(apps)
    legacy_manifest = UPSTREAM_MANIFEST.replace("vpath-authored", "vpath-legacy")

    target = apps / "vpath-legacy"
    target.mkdir()
    (target / MANIFEST_NAME).write_text(legacy_manifest, encoding="utf-8")
    (target / PROVENANCE_NAME).write_text(
        yaml.safe_dump(
            {
                "repo": REPO,
                "ref": "main",
                "commit": COMMIT,
                "manifest_origin": UPSTREAM,
                "added_at": "2026-01-01T00:00:00Z",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    store.refresh("vpath-legacy", tree(tmp_path, legacy_manifest), "d" * 40)

    recorded = yaml.safe_load((target / PROVENANCE_NAME).read_text(encoding="utf-8"))
    assert recorded["path"] == ""


def test_runtime_detection_refuses_to_guess(tmp_path: Path) -> None:
    assert detect_runtime(tree(tmp_path, runtime_file="package.json")) == "node"

    python_only = tmp_path / "py"
    python_only.mkdir()
    (python_only / "pyproject.toml").write_text("", encoding="utf-8")
    assert detect_runtime(python_only) == "python"

    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(RegistryError, match="neither"):
        detect_runtime(empty)

    both = tmp_path / "both"
    both.mkdir()
    (both / "package.json").write_text("{}", encoding="utf-8")
    (both / "pyproject.toml").write_text("", encoding="utf-8")
    with pytest.raises(RegistryError, match="both"):
        detect_runtime(both)
