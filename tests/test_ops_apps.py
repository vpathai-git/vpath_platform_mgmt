"""App catalog tests: manifests in, console entries out."""

from __future__ import annotations

from pathlib import Path

from vpath_platform_mgmt.ops.apps import AppCatalog, entry_from_manifest

MANIFEST = """\
apiVersion: vpath/v1
kind: VpathApp
metadata:
  name: vpath-explorer
spec:
  type: web
  basePath: /explorer
  port: 3007
  ui:
    title: Explorer
    description: File system explorer
    icon: folder-open
"""


def write_app(root: Path, folder: str, body: str = MANIFEST) -> Path:
    app_dir = root / folder
    app_dir.mkdir(parents=True)
    (app_dir / "vpath-app.yaml").write_text(body, encoding="utf-8")
    return app_dir


def test_entry_parsed_from_manifest(tmp_path: Path) -> None:
    app = write_app(tmp_path, "vpath-explorer")
    entry = entry_from_manifest(app / "vpath-app.yaml")
    assert entry is not None
    assert entry.title == "Explorer"
    assert entry.description == "File system explorer"
    assert entry.base_path == "/explorer"
    assert entry.port == 3007
    assert entry.app_type == "web"


def test_url_built_only_with_platform_url(tmp_path: Path) -> None:
    app = write_app(tmp_path, "vpath-explorer")
    entry = entry_from_manifest(app / "vpath-app.yaml")
    assert entry is not None
    assert entry.to_dict()["url"] == ""
    assert (
        entry.to_dict("https://10.0.0.4:30600/")["url"]
        == "https://10.0.0.4:30600/explorer"
    )


def test_catalog_lists_sorted_by_title(tmp_path: Path) -> None:
    write_app(tmp_path, "vpath-explorer")
    write_app(
        tmp_path,
        "zzz-app",
        MANIFEST.replace("vpath-explorer", "zzz-app").replace("Explorer", "Alpha"),
    )
    titles = [entry.title for entry in AppCatalog(tmp_path).entries()]
    assert titles == ["Alpha", "Explorer"]


def test_repo_apps_win_over_checkout_on_name_clash(tmp_path: Path) -> None:
    repo, checkout = tmp_path / "repo", tmp_path / "checkout"
    write_app(repo, "vpath-explorer")
    write_app(
        checkout, "vpath-explorer", MANIFEST.replace("Explorer", "Stale Explorer")
    )
    entries = AppCatalog(repo, checkout).entries()
    assert len(entries) == 1
    assert entries[0].title == "Explorer"


def test_missing_and_broken_dirs_are_skipped(tmp_path: Path) -> None:
    write_app(tmp_path, "good")
    broken = tmp_path / "broken"
    broken.mkdir()
    (broken / "vpath-app.yaml").write_text("{[not yaml", encoding="utf-8")
    assert len(AppCatalog(tmp_path, tmp_path / "nope").entries()) == 1


def test_shipped_apps_folder_is_discoverable() -> None:
    """The repo's own apps/ folder must parse — it is what the console shows."""
    apps_dir = Path(__file__).resolve().parents[1] / "apps"
    entries = AppCatalog(apps_dir).entries()
    assert len(entries) >= 5
    names = {entry.name for entry in entries}
    assert "vpath-explorer" in names
    assert all(entry.title for entry in entries)
