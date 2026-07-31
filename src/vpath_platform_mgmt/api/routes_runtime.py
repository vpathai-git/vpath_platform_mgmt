"""Runtime route: which pods one application is actually running.

Split from ``routes_apps`` along the seam between an app's *description* —
catalog, files, source — and what the cluster is doing with it right now.
Reading pods is the only route here that needs a Kubernetes connection, so
it is also the only one that can be absent, and it refuses at the verb rather
than being missing from the API.
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import FastAPI, HTTPException, Request

from vpath_platform_mgmt.api.auth import Identity
from vpath_platform_mgmt.ops.app_runtime import RuntimeReader
from vpath_platform_mgmt.ops.argocd import ArgoError
from vpath_platform_mgmt.ops.engine import EngineFailure
from vpath_platform_mgmt.ops.service import OpsService

IdentityFn = Callable[[Request], Identity]

NO_CLUSTER = (
    "this console has no cluster connection — pod state requires "
    "VPATH_MGMT_K8S_URL and VPATH_MGMT_K8S_TOKEN"
)


def register(
    app: FastAPI,
    identity: IdentityFn,
    service: OpsService,
    runtime: RuntimeReader | None,
) -> None:
    """Attach the runtime route; absent cluster access refuses at the verb."""

    @app.get("/api/apps/{app_name}/pods")
    def app_pods(request: Request, app_name: str) -> dict[str, object]:
        """Pods of one app, grouped by the namespace they run in.

        Read-only cluster state behind the same identity gate as the rest of
        ``/api/apps``: every role that may list applications may see what
        those applications are running.
        """
        identity(request)
        if runtime is None:
            raise HTTPException(status_code=409, detail=NO_CLUSTER)
        try:
            installed = service.installed_apps()
        except EngineFailure as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        # None means the engine cannot say. The cluster is the authority on
        # what runs, so an unknown install set is not a reason to refuse —
        # only a known one that excludes this app is.
        if installed is not None and app_name not in installed:
            raise HTTPException(
                status_code=404,
                detail=f"'{app_name}' is not installed on this server, so it "
                "has no namespace to read",
            )
        try:
            return runtime.snapshot(app_name)
        except ArgoError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
