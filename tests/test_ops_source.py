"""Materializer tests — the guards matter most: this writes into the
stable server checkout (decision 16)."""

from __future__ import annotations

import io
import tarfile
from pathlib import Path

import pytest

from vpath_platform_mgmt.ops.source import (
    SourceError,
    SourceMaterializer,
    SourceProvenance,
)

PROV = SourceProvenance(repo="git@example:apps.git", ref="port-x", commit="abc123")


def make_archive(files: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for name, content in files.items():
            data = content.encode()
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def make_checkout(tmp_path: Path) -> SourceMaterializer:
    (tmp_path / "apps_infra" / "apps").mkdir(parents=True)
    return SourceMaterializer(tmp_path)


def test_materializes_new_app(tmp_path: Path) -> None:
    mat = make_checkout(tmp_path)
    summary = mat.materialize(
        "vpath-explorer",
        make_archive({"vpath-app.yaml": "kind: VpathApp\n", "src/page.tsx": "x"}),
        PROV,
    )
    target = tmp_path / "apps_infra" / "apps" / "vpath-explorer"
    assert (target / "vpath-app.yaml").is_file()
    assert (target / "src" / "page.tsx").is_file()
    assert summary["file_count"] == 2
    assert summary["replaced"] is False
    assert summary["source"]["commit"] == "abc123"  # type: ignore[index]


def test_existing_target_refused_without_replace(tmp_path: Path) -> None:
    mat = make_checkout(tmp_path)
    archive = make_archive({"vpath-app.yaml": "kind: VpathApp\n"})
    mat.materialize("demo", archive, PROV)
    with pytest.raises(SourceError, match="already exists"):
        mat.materialize("demo", archive, PROV)


def test_replace_swaps_content_and_removes_stale_files(tmp_path: Path) -> None:
    mat = make_checkout(tmp_path)
    mat.materialize(
        "demo", make_archive({"vpath-app.yaml": "v1", "old.txt": "gone"}), PROV
    )
    summary = mat.materialize(
        "demo", make_archive({"vpath-app.yaml": "v2"}), PROV, replace=True
    )
    target = tmp_path / "apps_infra" / "apps" / "demo"
    assert (target / "vpath-app.yaml").read_text(encoding="utf-8") == "v2"
    assert not (target / "old.txt").exists()
    assert summary["replaced"] is True


def test_path_traversal_member_is_refused(tmp_path: Path) -> None:
    mat = make_checkout(tmp_path)
    evil = make_archive({"vpath-app.yaml": "k", "../../../../etc/pwned": "x"})
    with pytest.raises(SourceError, match="escapes the target"):
        mat.materialize("demo", evil, PROV)
    assert not (tmp_path / "apps_infra" / "apps" / "demo").exists()


def test_symlink_member_is_refused(tmp_path: Path) -> None:
    mat = make_checkout(tmp_path)
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        data = b"kind: VpathApp\n"
        info = tarfile.TarInfo("vpath-app.yaml")
        info.size = len(data)
        archive.addfile(info, io.BytesIO(data))
        link = tarfile.TarInfo("sneaky")
        link.type = tarfile.SYMTYPE
        link.linkname = "/etc/passwd"
        archive.addfile(link)
    with pytest.raises(SourceError, match="not a regular file"):
        mat.materialize("demo", buffer.getvalue(), PROV)


def test_upload_without_manifest_is_refused(tmp_path: Path) -> None:
    mat = make_checkout(tmp_path)
    with pytest.raises(SourceError, match="no vpath-app.yaml"):
        mat.materialize("demo", make_archive({"README.md": "hi"}), PROV)


@pytest.mark.parametrize("name", ["../escape", "a/b", "UPPER", "", ".."])
def test_invalid_app_names_are_refused(tmp_path: Path, name: str) -> None:
    mat = make_checkout(tmp_path)
    with pytest.raises(SourceError):
        mat.target_for(name)


def test_missing_checkout_fails_construction(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="server checkout not found"):
        SourceMaterializer(tmp_path / "nope")
