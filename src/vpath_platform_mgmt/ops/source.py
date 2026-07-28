"""Materialize app-repo source into the server checkout (decision 16).

The engine only builds apps it discovers at ``apps_infra/apps/<name>/``, so
source authored in an app repo has to land there first. This module does
that write and nothing else — it is deliberately paranoid, because it is the
one place the management plane modifies the stable server checkout.

Guards, all fail-hard: the app name must be a single safe path segment; the
target must resolve inside the checkout; every archive member must resolve
inside the target; only regular files and directories are accepted (no
symlinks, links or devices); the upload must contain a ``vpath-app.yaml``;
and an existing target is only replaced when the caller says so.

Rollback is git: the server checkout is a repository, so a materialization
is visible as a normal diff and undone with
``git checkout -- <path> && git clean -fd <path>``.
"""

from __future__ import annotations

import io
import re
import shutil
import tarfile
from dataclasses import dataclass
from pathlib import Path

APP_NAME = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
APPS_SUBDIR = "apps_infra/apps"
MANIFEST = "vpath-app.yaml"


class SourceError(Exception):
    """Materialization refused; the message says exactly why."""


@dataclass(frozen=True)
class SourceProvenance:
    """Where the uploaded source came from — recorded on the job."""

    repo: str = ""
    ref: str = ""
    commit: str = ""
    dirty: bool = False

    def to_dict(self) -> dict[str, object]:
        """JSON-serializable provenance."""
        return {
            "repo": self.repo,
            "ref": self.ref,
            "commit": self.commit,
            "dirty": self.dirty,
        }


def _safe_members(archive: tarfile.TarFile, target: Path) -> list[tarfile.TarInfo]:
    """Members that are plain files/dirs resolving inside ``target``."""
    members: list[tarfile.TarInfo] = []
    for member in archive.getmembers():
        if not (member.isfile() or member.isdir()):
            raise SourceError(
                f"archive member '{member.name}' is not a regular file or "
                "directory (symlinks, links and devices are refused)"
            )
        resolved = (target / member.name).resolve()
        if resolved != target.resolve() and target.resolve() not in resolved.parents:
            raise SourceError(
                f"archive member '{member.name}' escapes the target directory"
            )
        members.append(member)
    return members


class SourceMaterializer:
    """Writes app source into ``<checkout>/apps_infra/apps/<app>``."""

    def __init__(self, checkout: Path, apps_subdir: str = APPS_SUBDIR) -> None:
        if not checkout.is_dir():
            raise ValueError(f"server checkout not found: {checkout}")
        self._checkout = checkout.resolve()
        self._apps_root = (self._checkout / apps_subdir).resolve()

    @property
    def apps_root(self) -> Path:
        """Directory the engine discovers apps in."""
        return self._apps_root

    def target_for(self, app: str) -> Path:
        """Validated target directory for one app."""
        if not APP_NAME.match(app):
            raise SourceError(
                f"invalid app name '{app}' — expected a single lowercase "
                "path segment"
            )
        target = (self._apps_root / app).resolve()
        if self._apps_root not in target.parents:
            raise SourceError(f"target for '{app}' escapes {self._apps_root}")
        return target

    def materialize(
        self,
        app: str,
        archive_bytes: bytes,
        provenance: SourceProvenance,
        replace: bool = False,
    ) -> dict[str, object]:
        """Place ``archive_bytes`` at the app's discovery path.

        Returns a summary suitable for the job record. Raises ``SourceError``
        on any refusal; the checkout is left untouched in that case.
        """
        target = self.target_for(app)
        existed = target.exists()
        if existed and not replace:
            raise SourceError(
                f"{target} already exists — pass replace to overwrite it "
                "(the checkout is a git repo; review the diff afterwards)"
            )
        with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as archive:
            members = _safe_members(archive, target)
            names = {Path(m.name).as_posix() for m in members}
            if MANIFEST not in names:
                raise SourceError(
                    f"upload has no {MANIFEST} at its root — refusing to "
                    "materialize something the engine cannot discover"
                )
            if existed:
                shutil.rmtree(target)
            target.mkdir(parents=True)
            archive.extractall(target, members=members)
        files = [name for name in sorted(names) if not name.endswith("/")]
        return {
            "app": app,
            "target": str(target),
            "replaced": existed,
            "file_count": len(files),
            "manifest_present": True,
            "source": provenance.to_dict(),
        }
