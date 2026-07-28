"""Explorer browsing tests — read-only, and strictly inside the app folder."""

from __future__ import annotations

from pathlib import Path

import pytest

from vpath_platform_mgmt.ops.apps import AppCatalog
from vpath_platform_mgmt.ops.browse import MAX_BYTES, AppBrowser, BrowseError

MANIFEST = """\
apiVersion: vpath/v1
kind: VpathApp
metadata:
  name: demo-app
spec:
  type: web
  basePath: /demo
  ui:
    title: Demo
"""


@pytest.fixture()
def browser(tmp_path: Path) -> AppBrowser:
    app = tmp_path / "demo-app"
    (app / "src").mkdir(parents=True)
    (app / "vpath-app.yaml").write_text(MANIFEST, encoding="utf-8")
    (app / "src" / "page.tsx").write_text("export default 1;\n", encoding="utf-8")
    (app / "node_modules").mkdir()
    (app / "node_modules" / "junk.js").write_text("x", encoding="utf-8")
    return AppBrowser(AppCatalog(tmp_path))


def test_tree_lists_files_and_skips_build_noise(browser: AppBrowser) -> None:
    paths = {node.path for node in browser.tree("demo-app")}
    assert "vpath-app.yaml" in paths
    assert "src/page.tsx" in paths
    assert not any("node_modules" in path for path in paths)


def test_read_returns_text(browser: AppBrowser) -> None:
    result = browser.read("demo-app", "src/page.tsx")
    # Newline-agnostic: the browser returns bytes as written on this platform.
    assert str(result["content"]).strip() == "export default 1;"
    assert result["truncated"] is False


def test_path_traversal_is_refused(browser: AppBrowser) -> None:
    with pytest.raises(BrowseError, match="escapes"):
        browser.read("demo-app", "../../../etc/passwd")


def test_unknown_app_is_refused(browser: AppBrowser) -> None:
    with pytest.raises(BrowseError, match="unknown application"):
        browser.tree("nope")


def test_binary_is_refused(tmp_path: Path) -> None:
    app = tmp_path / "demo-app"
    app.mkdir()
    (app / "vpath-app.yaml").write_text(MANIFEST, encoding="utf-8")
    (app / "logo.png").write_bytes(b"\x89PNG\x00binary")
    browser = AppBrowser(AppCatalog(tmp_path))
    with pytest.raises(BrowseError, match="binary"):
        browser.read("demo-app", "logo.png")


def test_large_file_is_truncated_not_refused(tmp_path: Path) -> None:
    app = tmp_path / "demo-app"
    app.mkdir()
    (app / "vpath-app.yaml").write_text(MANIFEST, encoding="utf-8")
    (app / "big.txt").write_text("a" * (MAX_BYTES + 500), encoding="utf-8")
    result = AppBrowser(AppCatalog(tmp_path)).read("demo-app", "big.txt")
    assert result["truncated"] is True
    assert len(str(result["content"])) == MAX_BYTES


def test_directory_read_is_refused(browser: AppBrowser) -> None:
    with pytest.raises(BrowseError, match="not a file"):
        browser.read("demo-app", "src")
