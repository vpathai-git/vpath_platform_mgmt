"""Guards for the publish pipeline: refuse before a stage does something unsafe.

Split out of ``publish_stages`` along the seam between "is this safe to do"
(this module) and "how each stage actually walks its work" (the stage bodies
that remain in ``publish_stages``), to keep each module under the project's
line limit. ``PublishRequest`` must be imported under ``TYPE_CHECKING`` because
``publish_stages`` imports this module at runtime.
"""

from __future__ import annotations

from dataclasses import replace as replaced
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from vpath_platform_mgmt.ops.app_registry import MANIFEST_NAME

if TYPE_CHECKING:
    from vpath_platform_mgmt.ops.publish_stages import PublishRequest

PROVENANCE = "vpath-source.yaml"


class PublishError(Exception):
    """A stage refused; the message names the stage and the reason."""


def provenance_of(directory: Path) -> dict[str, object]:
    """What a directory's ``vpath-source.yaml`` records, or nothing."""
    provenance = directory / PROVENANCE
    if not provenance.is_file():
        return {}
    data = yaml.safe_load(provenance.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def same_source(recorded: dict[str, object], probed: Any, path: str) -> bool:
    """Whether what is already there came from the repository being published.

    This is what separates a re-publish of the same app from an accidental
    collision on its name. Only the former may overwrite without being asked.
    """
    return (
        str(recorded.get("repo", "")) == probed.repo_url
        and str(recorded.get("path", "")) == path
    )


def _describes(repo: str, path: str) -> str:
    return f"{repo} at '{path}'" if path else repo


def _require_overwrite_sanctioned(
    stage: str,
    request: PublishRequest,
    probed: Any,
    recorded: dict[str, object],
    where: str,
) -> None:
    """Refuse to destroy an app that is not the one being published.

    The registry and the materializer each refuse a silent overwrite; the
    orchestrator must not be the thing that bypasses both. Re-publishing the
    same repository and path is the one overwrite that needs no asking, and
    it is what makes a failed publish resumable.
    """
    if request.replace or same_source(recorded, probed, probed.path):
        return
    held = _describes(
        str(recorded.get("repo", "")) or "an unrecorded source",
        str(recorded.get("path", "")),
    )
    asked = _describes(probed.repo_url, probed.path)
    raise PublishError(
        f"{stage}: '{request.name}' is already {where} from {held}, and this "
        f"publish comes from {asked} — overwriting would destroy that app; "
        "pass replace to do it deliberately"
    )


def _declared_name(request: PublishRequest, probed: Any) -> str:
    """The name the repository itself gives this app, or empty if it gives none."""
    manifest = probed.files.get(MANIFEST_NAME) if probed.files else None
    if manifest is None:
        return request.generate.name if request.generate is not None else ""
    parsed = yaml.safe_load(manifest) or {}
    metadata = parsed.get("metadata") if isinstance(parsed, dict) else None
    name = metadata.get("name") if isinstance(metadata, dict) else None
    return name if isinstance(name, str) else ""


def check_name_agreement(request: PublishRequest, probed: Any) -> None:
    """Refuse a name the repository disagrees with, before anything uses it.

    Every preflight path is computed against the requested name, so a
    disagreement discovered later reads as a broken manifest when the broken
    thing is the form field.
    """
    declared = _declared_name(request, probed)
    if declared and declared != request.name:
        raise PublishError(
            f"preflight: this repository declares the app name '{declared}', "
            f"but publish was asked for '{request.name}' — publish it under "
            "the name it declares"
        )


def with_runtime(request: PublishRequest, runtime: str) -> PublishRequest:
    """The same request, with the generated manifest's runtime resolved.

    ``Generated.runtime`` is what the registry writes into
    ``spec.build.runtime``. The console's Add-app form has no runtime field,
    so leaving it unresolved writes a manifest that cannot be built.
    """
    if request.generate is None or request.generate.runtime == runtime:
        return request
    return replaced(request, generate=replaced(request.generate, runtime=runtime))


def subtree(downloaded: Path, path: str) -> Path:
    """The directory inside the repository that is the app.

    A repository is often a workspace whose root holds several apps; sending
    the root would put all of them in one app's directory. The path is
    operator input, so it is resolved and checked to stay inside the
    download rather than trusted.
    """
    if not path:
        return downloaded
    root = downloaded.resolve()
    target = (downloaded / path).resolve()
    if not target.is_dir() or root not in target.parents:
        raise PublishError(f"send: '{path}' is not a directory in this repository")
    return target
