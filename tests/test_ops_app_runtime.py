"""Tests for reading what an application actually runs in the cluster."""

from __future__ import annotations

from collections.abc import Callable

import httpx
import pytest

from vpath_platform_mgmt.ops.app_runtime import RuntimeReader, pod_view
from vpath_platform_mgmt.ops.argocd import ArgoClient, ArgoError

Handler = Callable[[httpx.Request], httpx.Response]

APP = "vpath-workflow-demo"
PROJECT = f"kp-{APP}-klemens"


def argo(handler: Handler) -> ArgoClient:
    client = httpx.Client(
        base_url="https://k8s.test", transport=httpx.MockTransport(handler)
    )
    return ArgoClient("https://k8s.test", "token", client=client)


def pod(
    name: str,
    ready: tuple[bool, ...] = (True,),
    restarts: tuple[int, ...] = (0,),
    phase: str = "Running",
    owner: str = "",
) -> dict[str, object]:
    """One pod as the Kubernetes API returns it, trimmed to what we read.

    ``owner`` is ``"Kind/name"`` as it appears in ownerReferences; empty
    means an unmanaged pod, which is what a provisioned project's helper
    pods look like on the real cluster.
    """
    references = []
    if owner:
        kind, _, owner_name = owner.partition("/")
        references = [{"kind": kind, "name": owner_name}]
    return {
        "metadata": {"name": name, "ownerReferences": references},
        "spec": {"containers": [{"name": f"c{i}"} for i in range(len(ready))]},
        "status": {
            "phase": phase,
            "startTime": "2026-07-27T09:12:44Z",
            "containerStatuses": [
                {"ready": is_ready, "restartCount": count}
                for is_ready, count in zip(ready, restarts)
            ],
        },
    }


def cluster(
    namespaces: list[str],
    pods: dict[str, list[dict[str, object]]],
    unreadable: str = "",
    sync: str = "Synced",
    health: str = "Healthy",
    destination: str | None = APP,
    application: bool = True,
    tracked: list[tuple[str, str]] | None = None,
) -> ArgoClient:
    """A cluster whose answers depend on the path being asked for.

    ``tracked`` is the ArgoCD Application's ``status.resources`` as
    ``(kind, name)`` pairs — the workloads it manages for this app.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/namespaces"):
            return httpx.Response(
                200, json={"items": [{"metadata": {"name": n}} for n in namespaces]}
            )
        if path.endswith("/pods"):
            namespace = path.split("/namespaces/")[1].removesuffix("/pods")
            if namespace == unreadable:
                return httpx.Response(500)
            return httpx.Response(200, json={"items": pods.get(namespace, [])})
        if "/applications/" in path:
            if not application:
                return httpx.Response(404)
            spec: dict[str, object] = {}
            if destination is not None:
                spec = {"destination": {"namespace": destination}}
            status: dict[str, object] = {
                "sync": {"status": sync},
                "health": {"status": health},
                "resources": [
                    {"kind": kind, "name": name}
                    for kind, name in (tracked or [("Deployment", APP)])
                ],
            }
            return httpx.Response(200, json={"spec": spec, "status": status})
        return httpx.Response(404)

    return argo(handler)


# --- the raw client ---------------------------------------------------------


def test_pods_lists_one_namespace() -> None:
    client = argo(lambda _: httpx.Response(200, json={"items": [pod("a"), pod("b")]}))
    assert [item["metadata"]["name"] for item in client.pods("ns")] == ["a", "b"]


def test_pods_fails_hard_when_the_namespace_endpoint_is_gone() -> None:
    client = argo(lambda _: httpx.Response(404))
    with pytest.raises(ArgoError, match="'ns'"):
        client.pods("ns")


def test_a_namespace_that_does_not_exist_is_not_reported_as_empty() -> None:
    """Verified on vm5: listing pods in an absent namespace returns 200 with
    an empty list, not 404. So emptiness alone cannot be trusted to mean
    'nothing runs here' — existence has to be established separately."""
    reader = RuntimeReader(
        cluster(["other-namespace"], {}, destination="vanished-namespace")
    )
    home = reader.snapshot(APP)["namespaces"][0]

    assert home["name"] == "vanished-namespace"
    assert home["pods"] is None
    assert "does not exist" in home["error"]


def test_pods_fails_hard_on_a_malformed_list() -> None:
    client = argo(lambda _: httpx.Response(200, json={"items": "nope"}))
    with pytest.raises(ArgoError, match="malformed"):
        client.pods("ns")


# --- shaping ----------------------------------------------------------------


def test_a_pod_reports_its_ready_containers_out_of_the_total() -> None:
    view = pod_view(pod("web-1", ready=(True, False), restarts=(0, 0)))
    assert view.name == "web-1"
    assert view.ready == "1/2"
    assert view.phase == "Running"
    assert view.started_at == "2026-07-27T09:12:44Z"


def test_a_pod_with_no_container_statuses_counts_the_containers_it_declares() -> None:
    """A Pending pod has a spec but no statuses; 0/2 is true, 0/0 is not."""
    raw = pod("web-1", ready=(True, True), phase="Pending")
    del raw["status"]["containerStatuses"]  # type: ignore[index]
    assert pod_view(raw).ready == "0/2"


def test_restarts_are_summed_across_every_container() -> None:
    view = pod_view(pod("api-1", ready=(True, True), restarts=(3, 4)))
    assert view.restarts == 7


# --- the snapshot -----------------------------------------------------------


def test_the_apps_own_namespace_and_its_projects_are_told_apart() -> None:
    reader = RuntimeReader(
        cluster(
            [APP, PROJECT, "kp-other-app-klemens"],
            {APP: [pod("web-1")], PROJECT: [pod("runner-1")]},
        )
    )
    snapshot = reader.snapshot(APP)

    assert [(n["name"], n["kind"]) for n in snapshot["namespaces"]] == [
        (APP, "application"),
        (PROJECT, "project"),
    ]


def test_the_snapshot_carries_argocd_sync_and_health() -> None:
    reader = RuntimeReader(
        cluster([APP], {APP: []}, sync="OutOfSync", health="Degraded")
    )
    snapshot = reader.snapshot(APP)

    assert snapshot["sync"] == "OutOfSync"
    assert snapshot["health"] == "Degraded"


def test_an_app_with_no_projects_reports_only_its_own_namespace() -> None:
    reader = RuntimeReader(cluster([APP], {APP: [pod("web-1")]}))
    assert len(reader.snapshot(APP)["namespaces"]) == 1


def test_an_unreadable_namespace_carries_its_error_not_an_empty_pod_list() -> None:
    """'nothing runs here' and 'we could not ask' must never look alike."""
    reader = RuntimeReader(
        cluster([APP, PROJECT], {APP: [pod("web-1")]}, unreadable=PROJECT)
    )
    namespaces = reader.snapshot(APP)["namespaces"]

    broken = next(n for n in namespaces if n["name"] == PROJECT)
    assert broken["error"]
    assert broken["pods"] is None  # not [], which would read as 'none running'


def test_the_namespace_comes_from_argocd_not_from_the_apps_name() -> None:
    """On vm5, 7 of 18 installed apps deploy into a namespace named for
    something else — vpath-web into vpath-apps-v2, every -api app into its
    frontend's namespace. Deriving it from the name reads the wrong pods."""
    reader = RuntimeReader(
        cluster(
            ["vpath-apps-v2"],
            {
                "vpath-apps-v2": [
                    pod(
                        "vpath-web-f8bd7596b-lpcnp",
                        owner="ReplicaSet/vpath-web-f8bd7596b",
                    )
                ]
            },
            destination="vpath-apps-v2",
            tracked=[("Deployment", "vpath-web")],
        )
    )
    namespaces = reader.snapshot("vpath-web")["namespaces"]

    assert namespaces[0]["name"] == "vpath-apps-v2"
    assert namespaces[0]["pods"][0]["name"] == "vpath-web-f8bd7596b-lpcnp"


def test_an_app_argocd_has_no_application_for_says_so() -> None:
    """Guessing <app> as the namespace here is how you report another app's
    pods, or an absent namespace, as this one's."""
    reader = RuntimeReader(cluster([APP], {APP: [pod("web-1")]}, application=False))
    snapshot = reader.snapshot(APP)

    home = snapshot["namespaces"][0]
    assert home["pods"] is None
    assert "no ArgoCD Application" in home["error"]
    assert snapshot["sync"] == "absent"


def test_an_application_without_a_destination_namespace_is_not_guessed() -> None:
    reader = RuntimeReader(cluster([APP], {APP: [pod("web-1")]}, destination=None))

    assert reader.snapshot(APP)["namespaces"][0]["pods"] is None


# --- ownership --------------------------------------------------------------

# The real collision on vm5: two apps share the namespace vpath-agent-chat,
# and one's pod name is a prefix of the other's. Name matching cannot tell
# them apart; ownerReferences can.
CHAT = "vpath-agent-chat"
CHAT_PODS = [
    pod(
        "vpath-agent-chat-5ddbcd86c7-dsq9r",
        owner="ReplicaSet/vpath-agent-chat-5ddbcd86c7",
    ),
    pod(
        "vpath-agent-chat-api-784f59cb48-v6nbk",
        owner="ReplicaSet/vpath-agent-chat-api-784f59cb48",
    ),
    pod(
        "vpath-agent-chat-api-gateway-mint-hmqcc",
        phase="Succeeded",
        owner="Job/vpath-agent-chat-api-gateway-mint",
    ),
]


def chat_cluster(app: str, tracked: list[tuple[str, str]]) -> ArgoClient:
    return cluster([CHAT], {CHAT: CHAT_PODS}, destination=CHAT, tracked=tracked)


def test_a_neighbours_pod_is_not_reported_as_this_apps() -> None:
    """vpath-agent-chat-api's pod name starts with 'vpath-agent-chat-', so a
    name-prefix test would claim it. Its ReplicaSet resolves to a different
    Deployment, so ownership does not."""
    reader = RuntimeReader(chat_cluster(CHAT, [("Deployment", CHAT)]))
    home = reader.snapshot(CHAT)["namespaces"][0]

    assert [p["name"] for p in home["pods"]] == ["vpath-agent-chat-5ddbcd86c7-dsq9r"]


def test_a_job_pod_belongs_to_the_app_that_tracks_the_job() -> None:
    reader = RuntimeReader(
        chat_cluster(
            "vpath-agent-chat-api",
            [
                ("Deployment", "vpath-agent-chat-api"),
                ("Job", "vpath-agent-chat-api-gateway-mint"),
            ],
        )
    )
    home = reader.snapshot("vpath-agent-chat-api")["namespaces"][0]

    assert [p["name"] for p in home["pods"]] == [
        "vpath-agent-chat-api-784f59cb48-v6nbk",
        "vpath-agent-chat-api-gateway-mint-hmqcc",
    ]


def test_pods_left_out_are_counted_never_silently_dropped() -> None:
    """Filtering that hides its own effect is how a missing pod goes unnoticed."""
    reader = RuntimeReader(chat_cluster(CHAT, [("Deployment", CHAT)]))

    assert reader.snapshot(CHAT)["namespaces"][0]["others"] == 2


def test_a_project_namespace_is_never_filtered_by_ownership() -> None:
    """ArgoCD does not manage provisioned projects: on vm5 the only pod in
    one is unmanaged and untracked, so ownership filtering would empty it."""
    reader = RuntimeReader(
        cluster(
            [APP, PROJECT],
            {APP: [], PROJECT: [pod("kp-inputs-helper", phase="Succeeded")]},
        )
    )
    project = reader.snapshot(APP)["namespaces"][1]

    assert [p["name"] for p in project["pods"]] == ["kp-inputs-helper"]
    assert project["others"] == 0


def test_an_unreadable_namespace_census_fails_the_whole_snapshot() -> None:
    """A partial namespace list presented as complete hides a whole project."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/namespaces"):
            return httpx.Response(500)
        return httpx.Response(200, json={"status": {}})

    with pytest.raises(ArgoError, match="namespaces"):
        RuntimeReader(argo(handler)).snapshot(APP)
