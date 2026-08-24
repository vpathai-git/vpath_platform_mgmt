"""From a repository URL to an app running under ArgoCD, in one walk.

Five stages, each delegated to the unit that already owns it: preflight
refuses a repository that cannot build, the registry writes the entry, the
materializer places the source in the server checkout, the local engine
renders and commits into the Deploy-of-Record, and the GitOps engine puts the
name in the InstalledSet and waits for ArgoCD.

``PublishPipeline`` sequences and nothing else -- no HTTP, no subprocess, no
git, no writes of its own -- so every failure is attributable to exactly one
owner and these tests need neither a network nor a box. The stage bodies live
in ``publish_stages`` so this module stays the sequencer alone.

Resume is by observation, not by a stored ledger: provenance already records
which commit is registered and which is materialized, so a re-run skips what
genuinely happened. Render and install are never skipped, because both are
already idempotent in the engine -- an unchanged app rebuilds nothing, and an
app already in the InstalledSet only has its sync verified.
"""

from __future__ import annotations

import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from vpath_platform_mgmt.ops.engine import StepEmitter
from vpath_platform_mgmt.ops.model import Role
from vpath_platform_mgmt.ops.publish_guards import PublishError, with_runtime
from vpath_platform_mgmt.ops.publish_stages import (
    PublishRequest,
    probe_repo,
    run_install,
    run_preflight,
    run_register,
    run_render,
    run_send,
)

STAGES: tuple[str, ...] = ("preflight", "register", "send", "render", "install")

__all__ = ["STAGES", "PublishError", "PublishPipeline", "PublishRequest"]


class PublishPipeline:
    """Walks the five stages; every collaborator is injected."""

    def __init__(
        self,
        registry: Any,
        materializer: Any,
        local_engine: Any,
        gitops_engine: Any,
        probe: Callable[..., Any],
        materialise: Callable[..., Path],
        download: Callable[..., Path],
        bundle: Callable[[Path], bytes],
        place: Callable[..., None],
        inspect: Callable[..., None],
        runtime_of: Callable[[Path], str],
    ) -> None:
        self._registry = registry
        self._materializer = materializer
        self._local = local_engine
        self._gitops = gitops_engine
        self._probe = probe
        self._materialise = materialise
        self._download = download
        self._bundle = bundle
        self._place = place
        self._inspect = inspect
        self._runtime_of = runtime_of

    def run(
        self,
        request: PublishRequest,
        actor: str,
        role: Role,
        emit: StepEmitter,
    ) -> dict[str, object]:
        """Walk every stage, or fail hard naming the one that refused."""
        stages: dict[str, str] = {}
        workspace = Path(tempfile.mkdtemp(prefix="vpath-publish-"))
        try:
            probed = probe_repo(self._probe, request, emit)
            stages["preflight"], runtime = run_preflight(
                self._materialise,
                self._inspect,
                self._runtime_of,
                request,
                probed,
                emit,
            )
            request = with_runtime(request, runtime)
            stages["register"] = run_register(
                self._registry, self._materialise, request, probed, emit
            )
            stages["send"] = run_send(
                self._registry,
                self._materializer,
                self._download,
                self._bundle,
                self._place,
                request,
                probed,
                workspace,
                emit,
            )
        finally:
            shutil.rmtree(workspace, ignore_errors=True)
        stages["render"] = run_render(self._local, request, actor, role, emit)
        stages["install"] = run_install(self._gitops, request, actor, role, emit)
        return {"app": request.name, "commit": probed.commit, "stages": stages}
