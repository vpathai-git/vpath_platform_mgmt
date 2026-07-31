"""What an application actually runs, as opposed to what is installed.

The catalog says which apps exist and the InstalledSet says which are
installed; neither can tell an operator that a backend pod is crashlooping.
This module answers that third question by reading pods out of the two kinds
of namespace an app owns:

    <app>            its own workloads (web, api, dapr sidecars)
    kp-<app>-<user>  one project per user, where workflow pods run

Only the second kind is created on demand, by ``spec.workflow.autoProvision``,
which is why an app with no provisioned projects has no workflow pod anywhere.

Nothing here classifies a pod as frontend, backend or workflow: no manifest in
this repository records which label the server's renderer emits for a
component, and a guessed role that renders confidently is worse than an absent
one. Pods are grouped by the namespace they run in, which is a fact.

Shaping is separated from fetching on purpose — every function below the
reader is pure, so the interesting cases are testable from fixtures.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from vpath_platform_mgmt.ops.argocd import ArgoClient, ArgoError

APPLICATION = "application"
PROJECT = "project"


@dataclass(frozen=True)
class PodView:
    """One pod, reduced to what an operator reads at a glance."""

    name: str
    phase: str
    ready: str
    restarts: int
    started_at: str

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "phase": self.phase,
            "ready": self.ready,
            "restarts": self.restarts,
            "started_at": self.started_at,
        }


def _as_dict(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


def pod_view(raw: dict[str, Any]) -> PodView:
    """Shape one Kubernetes pod object.

    The container total comes from ``spec.containers`` rather than from the
    statuses: a Pending pod has declared its containers but reports no status
    for them yet, and ``0/2`` is the truth there where ``0/0`` would read as a
    pod with nothing in it.
    """
    status = _as_dict(raw.get("status"))
    statuses = [_as_dict(item) for item in _as_list(status.get("containerStatuses"))]
    declared = _as_list(_as_dict(raw.get("spec")).get("containers"))
    total = len(declared) or len(statuses)
    return PodView(
        name=str(_as_dict(raw.get("metadata")).get("name") or ""),
        phase=str(status.get("phase") or "Unknown"),
        ready=f"{sum(1 for item in statuses if item.get('ready'))}/{total}",
        restarts=sum(int(item.get("restartCount") or 0) for item in statuses),
        started_at=str(status.get("startTime") or ""),
    )


class RuntimeReader:
    """Reads one app's live pods through the Kubernetes API."""

    def __init__(self, argo: ArgoClient) -> None:
        self._argo = argo

    def snapshot(self, app: str) -> dict[str, object]:
        """Every namespace this app owns, with the pods running in it.

        A failure to census the namespaces fails the whole call: a partial
        list presented as complete is how an operator concludes a workflow
        pod is absent when it was merely never looked for. A failure to read
        one namespace's pods is narrower and is reported per namespace.
        """
        sync, health = ArgoClient.status_of(self._argo.application(app))
        namespaces = [app, *self._argo.app_namespaces(app)]
        return {
            "app": app,
            "sync": sync,
            "health": health,
            "namespaces": [self._namespace(app, name) for name in namespaces],
        }

    def _namespace(self, app: str, name: str) -> dict[str, object]:
        view: dict[str, object] = {
            "name": name,
            "kind": APPLICATION if name == app else PROJECT,
            "pods": None,
            "error": "",
        }
        try:
            view["pods"] = [pod_view(raw).to_dict() for raw in self._argo.pods(name)]
        except ArgoError as exc:
            # pods stays None: an empty list here would claim we looked and
            # found nothing running, which is the opposite of what happened.
            view["error"] = str(exc)
        return view
