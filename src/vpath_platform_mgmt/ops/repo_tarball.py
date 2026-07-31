"""Download a repository's whole tree at one commit, without git or a token.

Split out of ``repo_probe`` along the seam between "the few files
registration needs" (the contents API, in ``repo_probe``) and "the whole
tree sending needs" (the tarball API, here), to keep each module under the
project's line limit.

``gh api .../tarball/<sha>`` gives the whole tree and gh authenticates
itself — so an INTERNAL repository works and no token ever appears in an
argv, where a process list would expose it. This is still the right tool
only for *sending* an app, where the whole tree genuinely is the payload;
registration reads the few files it needs through ``repo_probe`` instead.
"""

from __future__ import annotations

import subprocess
import tarfile
from pathlib import Path

from vpath_platform_mgmt.ops.repo_fetch import FetchError

TARBALL_TIMEOUT_SECONDS = 300


def download_tree(slug: str, commit: str, into: Path) -> Path:
    """Extract the repository at one commit, without git and without a token.

    Sending an app needs the whole tree, which the contents API cannot give.
    ``gh api .../tarball/<sha>`` can, and gh authenticates itself — so an
    INTERNAL repository works and no token ever appears in an argv, where a
    process list would expose it.

    GitHub wraps everything in one ``owner-repo-sha/`` directory; that prefix
    is stripped, because the materializer expects the manifest at the root.
    """
    target = Path(into)
    target.mkdir(parents=True, exist_ok=True)
    archive = target / "_tree.tar.gz"
    with archive.open("wb") as sink:
        completed = subprocess.run(  # noqa: S603 - fixed argv, no shell
            ["gh", "api", f"repos/{slug}/tarball/{commit}"],
            stdout=sink,
            stderr=subprocess.PIPE,
            text=False,
            timeout=TARBALL_TIMEOUT_SECONDS,
        )
    if completed.returncode != 0 or archive.stat().st_size == 0:
        stderr = (completed.stderr or b"").decode("utf-8", "replace").strip()
        archive.unlink(missing_ok=True)
        raise FetchError(
            f"cannot download {slug} at {commit[:12]}: "
            f"{stderr.splitlines()[-1] if stderr else 'empty archive'}"
        )

    extracted = target / "tree"
    extracted.mkdir(exist_ok=True)
    with tarfile.open(archive, "r:gz") as tar:
        for member in tar.getmembers():
            _extract_stripped(tar, member, extracted)
    archive.unlink(missing_ok=True)
    return extracted


def _extract_stripped(
    tar: tarfile.TarFile, member: tarfile.TarInfo, root: Path
) -> None:
    """Extract one member without its top directory, refusing anything odd."""
    if not (member.isfile() or member.isdir()):
        return  # symlinks, devices and hard links are never part of a tree we ship
    parts = Path(member.name).parts[1:]  # drop GitHub's owner-repo-sha/ prefix
    if not parts:
        return
    destination = root.joinpath(*parts).resolve()
    if root.resolve() not in destination.parents:
        raise FetchError(f"{member.name} would escape the extraction directory")
    if member.isdir():
        destination.mkdir(parents=True, exist_ok=True)
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    source = tar.extractfile(member)
    if source is None:
        return
    destination.write_bytes(source.read())
