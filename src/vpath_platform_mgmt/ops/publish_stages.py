"""Stage bodies for the publish pipeline; ``publish.py`` only sequences them.

Each function here owns exactly one stage's logic and takes its collaborators
as explicit arguments rather than through ``self`` -- this module is state
machinery, not an object, so a stage's inputs are visible at its call site.
"""

from __future__ import annotations

import shutil
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from vpath_platform_mgmt.ops.app_preflight import PreflightError
from vpath_platform_mgmt.ops.app_registry import Generated, RegistryError
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


def recorded_commit(directory: Path) -> str:
    """The commit a provenance file records, or empty when there is none."""
    provenance = directory / PROVENANCE
    if not provenance.is_file():
        return ""
    data = yaml.safe_load(provenance.read_text(encoding="utf-8")) or {}
    return str(data.get("commit", "")) if isinstance(data, dict) else ""


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
) -> str:
    """Refuse a repository that cannot build once it lands on the server."""
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
    return DONE


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

    emit(f"register: writing apps/{request.name}")
    tree = Path(tempfile.mkdtemp(prefix="vpath-register-"))
    try:
        materialise(probed, tree)
        result = registry.register(
            repo=probed.repo_url,
            ref=request.ref,
            commit=probed.commit,
            tree=tree,
            path=request.path,
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
    target = materializer.target_for(request.name)
    if recorded_commit(target) == probed.commit:
        emit(f"send: the checkout already holds {probed.commit[:12]}")
        return SKIPPED

    emit(f"send: downloading {probed.slug} at {probed.commit[:12]}")
    try:
        downloaded = download(probed.slug, probed.commit, workspace)
        payload = subtree(downloaded, request.path)
        place(request.name, payload)
        archive = bundle(payload)
        summary = materializer.materialize(
            request.name,
            archive,
            SourceProvenance(
                repo=probed.repo_url, ref=request.ref, commit=probed.commit
            ),
            replace=True,
        )
    except (FetchError, RegistryError, SourceError) as exc:
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
