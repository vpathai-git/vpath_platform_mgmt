"""Reads ArgoCD reconciliation state through the Kubernetes API.

The commit into the Deploy-of-Record is only half a deploy; the other half is
ArgoCD converging the cluster onto it. This client answers the three questions
the lifecycle verbs ask — is the cascade wired, did the Application converge,
and what still runs under this app — mirroring the waits in the server's
``lib/pipeline/cluster-template-lifecycle.sh``.

Timeouts are failures, never soft passes: a verb that stops waiting reports
that the record was committed and convergence was not observed.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import httpx

from vpath_platform_mgmt.ops.engine import (
    PROBE_TIMEOUT_SECONDS,
    REACH_NO_ROUTE,
    REACH_REFUSED,
)

ARGO_NAMESPACE = "argocd"
APPLICATIONSET = "vpath-apps"
CASCADE_FINALIZER = "resources-finalizer.argocd.argoproj.io"
ARGO_API = "/apis/argoproj.io/v1alpha1"
RECONCILE_TIMEOUT_SECONDS = 360.0
POLL_SECONDS = 2.0
TIMEOUT_SECONDS = 30.0


class ArgoError(Exception):
    """The cluster could not be read, or it did not converge in time."""


class ArgoClient:
    """Kubernetes-API view of ArgoCD Applications and app namespaces."""

    def __init__(
        self,
        base_url: str,
        token: str,
        verify_tls: bool = True,
        namespace: str = ARGO_NAMESPACE,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
        now: Callable[[], float] = time.monotonic,
    ) -> None:
        if not base_url:
            raise ArgoError("Kubernetes API base URL is required")
        if not token:
            raise ArgoError("a Kubernetes API token is required to read ArgoCD state")
        self._namespace = namespace
        self._sleep = sleep
        self._now = now
        self._client = client or httpx.Client(
            base_url=base_url.rstrip("/"),
            verify=verify_tls,
            timeout=TIMEOUT_SECONDS,
            headers={"Authorization": f"Bearer {token}"},
        )

    def _get(self, path: str) -> httpx.Response:
        try:
            return self._client.get(path)
        except httpx.HTTPError as exc:
            raise ArgoError(f"Kubernetes GET {path} failed: {exc}") from exc

    def _get_json(self, path: str, what: str) -> dict[str, Any] | None:
        response = self._get(path)
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            raise ArgoError(
                f"cluster-unreachable: reading {what} returned "
                f"{response.status_code}"
            )
        body = response.json()
        if not isinstance(body, dict):
            raise ArgoError(f"cluster-unreachable: {what} response is not an object")
        return body

    def probe(self) -> str:
        """``""`` when the API answers, else why it did not.

        Short timeout: this runs inside the console's state poll, and a down
        box must not stall that poll for the client's full request timeout.
        """
        try:
            response = self._client.get("/version", timeout=PROBE_TIMEOUT_SECONDS)
        except httpx.HTTPError:
            return REACH_NO_ROUTE
        if response.status_code in (401, 403):
            return REACH_REFUSED
        return "" if response.status_code == 200 else f"status-{response.status_code}"

    def _app_path(self, name: str) -> str:
        return f"{ARGO_API}/namespaces/{self._namespace}/applications/{name}"

    def application(self, name: str) -> dict[str, Any] | None:
        """One ArgoCD Application, or None when it does not exist."""
        return self._get_json(self._app_path(name), f"Application '{name}'")

    def require_cascade(self) -> None:
        """Refuse to mutate the record unless the teardown cascade is wired."""
        path = (
            f"{ARGO_API}/namespaces/{self._namespace}"
            f"/applicationsets/{APPLICATIONSET}"
        )
        appset = self._get_json(path, f"ApplicationSet '{APPLICATIONSET}'")
        if appset is None:
            raise ArgoError(
                f"cluster-unreachable: ApplicationSet '{APPLICATIONSET}' is absent. "
                "Remedy: sync the App-of-Apps bootstrap before running lifecycle "
                "verbs; the Deploy-of-Record was not changed."
            )
        template = appset.get("spec", {}).get("template", {})
        finalizers = template.get("metadata", {}).get("finalizers") or []
        if CASCADE_FINALIZER not in finalizers:
            raise ArgoError(
                f"finalizer-missing: ApplicationSet '{APPLICATIONSET}' cannot "
                "guarantee an effective resource cascade. Remedy: run "
                "./gradlew pushManifests and sync the App-of-Apps bootstrap; no "
                "Deploy-of-Record mutation was attempted."
            )

    @staticmethod
    def status_of(application: dict[str, Any] | None) -> tuple[str, str]:
        """``(sync, health)`` for an Application; ``("absent", "absent")``."""
        if application is None:
            return ("absent", "absent")
        status = application.get("status", {})
        sync = status.get("sync", {}).get("status") or "Unknown"
        health = status.get("health", {}).get("status") or "Unknown"
        return (str(sync), str(health))

    def wait_synced(
        self, name: str, timeout: float = RECONCILE_TIMEOUT_SECONDS
    ) -> dict[str, str]:
        """Block until the Application is Synced/Healthy, or fail hard."""
        return self._wait(name, timeout, desired="installed")

    def wait_absent(
        self, name: str, timeout: float = RECONCILE_TIMEOUT_SECONDS
    ) -> dict[str, str]:
        """Block until the Application is gone, or fail hard."""
        return self._wait(name, timeout, desired="absent")

    def _wait(self, name: str, timeout: float, desired: str) -> dict[str, str]:
        started = self._now()
        while True:
            sync, health = self.status_of(self.application(name))
            if desired == "absent" and sync == "absent":
                return {"application": name, "sync": sync, "health": health}
            if desired != "absent" and (sync, health) == ("Synced", "Healthy"):
                return {"application": name, "sync": sync, "health": health}
            if self._now() - started >= timeout:
                raise ArgoError(
                    f"ArgoCD did not converge Application '{name}' to '{desired}' "
                    f"within {timeout:.0f}s (sync={sync}, health={health}). The "
                    "Deploy-of-Record commit remains authoritative."
                )
            self._sleep(POLL_SECONDS)

    def pods(self, namespace: str) -> list[dict[str, Any]]:
        """Every pod in one namespace, exactly as the API returns them.

        A namespace that is absent raises rather than returning nothing:
        "no pods run here" and "this namespace is gone" are the same empty
        list and not the same fact.
        """
        body = self._get_json(
            f"/api/v1/namespaces/{namespace}/pods", f"pods in '{namespace}'"
        )
        if body is None:
            raise ArgoError(
                f"cluster-unreachable: namespace '{namespace}' does not exist"
            )
        items = body.get("items")
        if not isinstance(items, list):
            raise ArgoError(
                f"cluster-unreachable: the pod list for '{namespace}' is malformed"
            )
        return [item for item in items if isinstance(item, dict)]

    def app_namespaces(self, app: str) -> list[str]:
        """Project namespaces (``kp-<app>-*``) that depend on this app."""
        body = self._get_json("/api/v1/namespaces", "namespaces")
        if body is None:
            raise ArgoError("cluster-unreachable: namespace census returned 404")
        prefix = f"kp-{app}-"
        items = body.get("items")
        if not isinstance(items, list):
            raise ArgoError("cluster-unreachable: namespace list is malformed")
        names = [item.get("metadata", {}).get("name", "") for item in items]
        return sorted(name for name in names if name.startswith(prefix))
