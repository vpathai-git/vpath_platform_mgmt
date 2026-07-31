"""Stage bodies for the publish pipeline; ``publish.py`` only sequences them.

Each function here owns exactly one stage's logic and takes its collaborators
as explicit arguments rather than through ``self`` -- this module is state
machinery, not an object, so a stage's inputs are visible at its call site.
"""

from __future__ import annotations

import shutil
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, replace as replaced
from pathlib import Path
from typing import Any

import yaml

from vpath_platform_mgmt.ops.app_preflight import PreflightError
from vpath_platform_mgmt.ops.app_registry import (
    MANIFEST_NAME,
    Generated,
    RegistryError,
)
from vpath_platform_mgmt.ops.bundle import BundleError
from vpath_platform_mgmt.ops.engine import EngineFailure, StepEmitter
from vpath_platform_mgmt.ops.model import Job, Role, Verb
from vpath_platform_mgmt.ops.repo_fetch import FetchError
from vpath_platform_mgmt.ops.source import SourceError, SourceProvenance

PROVENANCE = "vpath-source.yaml"
DONE = "done"
SKIPPED = "skipped"


class PublishError(Exception):
    """A stage refused; the message names the stage and the reason."""


@dataclass(frozen=True)
class PublishRequest:
    """One repository, at one ref, published under one name."""

    url: str
    ref: str
    name: str
    path: str = ""
    generate: Generated | None = None
    replace: bool = False


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


def probe_repo(
    probe: Callable[..., Any], request: PublishRequest, emit: StepEmitter
) -> Any:
    """Resolve the commit and read the manifest files at ``request.path``."""
    emit(f"reading {request.url} at {request.ref}")
    try:
        return probe(request.url, request.ref, path=request.path)
    except FetchError as exc:
        raise PublishError(f"preflight: {exc}") from exc


def _runtime_for(
    request: PublishRequest, tree: Path, runtime_of: Callable[[Path], str]
) -> str:
    if request.generate is not None and request.generate.runtime:
        return request.generate.runtime
    return runtime_of(tree)


def run_preflight(
    materialise: Callable[..., Path],
    inspect: Callable[..., None],
    runtime_of: Callable[[Path], str],
    request: PublishRequest,
    probed: Any,
    emit: StepEmitter,
) -> tuple[str, str]:
    """Refuse a repository that cannot build once it lands on the server.

    Returns the stage state and the resolved runtime, which the register
    stage needs so a generated manifest names something buildable.
    """
    check_name_agreement(request, probed)
    emit(f"preflight: inspecting {request.name} at {probed.commit[:12]}")
    tree = Path(tempfile.mkdtemp(prefix="vpath-preflight-"))
    try:
        materialise(probed, tree)
        runtime = _runtime_for(request, tree, runtime_of)
        inspect(tree, request.name, runtime)
    except (PreflightError, RegistryError) as exc:
        raise PublishError(f"preflight: {exc}") from exc
    finally:
        shutil.rmtree(tree, ignore_errors=True)
    return DONE, runtime


def run_register(
    registry: Any,
    materialise: Callable[..., Path],
    request: PublishRequest,
    probed: Any,
    emit: StepEmitter,
) -> str:
    """Write ``apps/<name>``, or skip when this commit is already recorded."""
    recorded = next(
        (entry for entry in registry.entries() if entry.get("name") == request.name),
        None,
    )
    if recorded is not None and str(recorded.get("commit", "")) == probed.commit:
        emit(f"register: {request.name} already records {probed.commit[:12]}")
        return SKIPPED
    if recorded is not None:
        _require_overwrite_sanctioned("register", request, probed, recorded, "recorded")

    emit(f"register: writing apps/{request.name}")
    tree = Path(tempfile.mkdtemp(prefix="vpath-register-"))
    try:
        materialise(probed, tree)
        result = registry.register(
            repo=probed.repo_url,
            ref=request.ref,
            commit=probed.commit,
            tree=tree,
            path=probed.path,
            generate=request.generate,
            replace=request.replace or recorded is not None,
        )
    except RegistryError as exc:
        raise PublishError(f"register: {exc}") from exc
    finally:
        shutil.rmtree(tree, ignore_errors=True)

    if result.name != request.name:
        raise PublishError(
            f"register: the repository's manifest names '{result.name}', "
            f"not '{request.name}' — publish under the name it declares"
        )
    return DONE


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


def run_send(
    materializer: Any,
    download: Callable[..., Path],
    bundle: Callable[[Path], bytes],
    place: Callable[..., None],
    request: PublishRequest,
    probed: Any,
    workspace: Path,
    emit: StepEmitter,
) -> str:
    """Materialize the app's subtree into the server checkout."""
    try:
        target = materializer.target_for(request.name)
        existing = provenance_of(target)
        if str(existing.get("commit", "")) == probed.commit:
            emit(f"send: the checkout already holds {probed.commit[:12]}")
            return SKIPPED
        if target.exists():
            _require_overwrite_sanctioned(
                "send", request, probed, existing, "in the server checkout"
            )

        emit(f"send: downloading {probed.slug} at {probed.commit[:12]}")
        downloaded = download(probed.slug, probed.commit, workspace)
        payload = subtree(downloaded, probed.path)
        place(request.name, payload)
        archive = bundle(payload)
        summary = materializer.materialize(
            request.name,
            archive,
            SourceProvenance(
                repo=probed.repo_url, ref=request.ref, commit=probed.commit
            ),
            replace=target.exists(),
        )
    except (FetchError, RegistryError, SourceError, BundleError) as exc:
        raise PublishError(f"send: {exc}") from exc
    emit(f"send: placed {summary.get('file_count')} files in the checkout")
    return DONE


def _deploy(
    engine: Any,
    request: PublishRequest,
    actor: str,
    role: Role,
    stage: str,
    emit: StepEmitter,
) -> None:
    job = Job(
        verb=Verb.DEPLOY,
        app=request.name,
        actor=actor,
        role=role,
        engine=engine.name,
    )
    try:
        engine.run(job, emit)
    except EngineFailure as exc:
        raise PublishError(f"{stage}: {exc}") from exc


def run_render(
    engine: Any, request: PublishRequest, actor: str, role: Role, emit: StepEmitter
) -> str:
    """Build and commit into the Deploy-of-Record; never skipped."""
    emit(f"render: building and committing {request.name}")
    _deploy(engine, request, actor, role, "render", emit)
    return DONE


def run_install(
    engine: Any, request: PublishRequest, actor: str, role: Role, emit: StepEmitter
) -> str:
    """Put the app in the InstalledSet and wait for ArgoCD; never skipped."""
    emit(f"install: putting {request.name} in the InstalledSet")
    _deploy(engine, request, actor, role, "install", emit)
    return DONE
