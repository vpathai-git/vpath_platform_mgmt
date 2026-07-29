"""Tests for the Gitea and ArgoCD clients behind the GitOps engine."""

from __future__ import annotations

import base64
import itertools
from collections.abc import Callable

import httpx
import pytest

from vpath_platform_mgmt.ops.argocd import APPLICATIONSET, ArgoClient, ArgoError
from vpath_platform_mgmt.ops.gitea import GiteaClient, GiteaError

Handler = Callable[[httpx.Request], httpx.Response]


def gitea(handler: Handler) -> GiteaClient:
    client = httpx.Client(
        base_url="https://gitea.test", transport=httpx.MockTransport(handler)
    )
    return GiteaClient("https://gitea.test", "platform", "k8s", "t", client=client)


def argo(handler: Handler, ticks: list[float] | None = None) -> ArgoClient:
    client = httpx.Client(
        base_url="https://k8s.test", transport=httpx.MockTransport(handler)
    )
    clock = iter(ticks) if ticks else itertools.repeat(0.0)
    return ArgoClient(
        "https://k8s.test",
        "token",
        client=client,
        sleep=lambda _: None,
        now=lambda: next(clock),
    )


def file_body(text: str, sha: str = "blob1") -> dict[str, object]:
    encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
    return {"type": "file", "content": encoded, "sha": sha}


def test_gitea_requires_a_base_url_and_token() -> None:
    with pytest.raises(GiteaError, match="base URL"):
        GiteaClient("", "o", "r", "t")
    with pytest.raises(GiteaError, match="token"):
        GiteaClient("https://gitea.test", "o", "r", "")


def test_gitea_ping_reports_reachability_without_raising() -> None:
    assert gitea(lambda _: httpx.Response(200, json={})).ping() is True
    assert gitea(lambda _: httpx.Response(503)).ping() is False

    def down(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route to host")

    assert gitea(down).ping() is False


def test_argo_ping_reports_reachability_without_raising() -> None:
    assert argo(lambda _: httpx.Response(200, json={})).ping() is True

    def down(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("tunnel is gone")

    assert argo(down).ping() is False


def test_get_file_decodes_content_and_sha() -> None:
    client = gitea(lambda _: httpx.Response(200, json=file_body("hello")))
    found = client.get_file("installed-set.json")
    assert (found.text, found.sha) == ("hello", "blob1")


def test_get_file_names_the_repo_when_absent() -> None:
    client = gitea(lambda _: httpx.Response(404))
    with pytest.raises(GiteaError, match="platform/k8s: installed-set.json not found"):
        client.get_file("installed-set.json")


def test_get_file_fails_hard_on_a_server_error() -> None:
    client = gitea(lambda _: httpx.Response(500))
    with pytest.raises(GiteaError, match="returned 500"):
        client.get_file("installed-set.json")


def test_get_file_rejects_a_directory() -> None:
    client = gitea(lambda _: httpx.Response(200, json=[{"type": "file"}]))
    with pytest.raises(GiteaError, match="is not a file"):
        client.get_file("apps/demo")


def test_get_file_rejects_a_response_without_content() -> None:
    client = gitea(lambda _: httpx.Response(200, json={"type": "file"}))
    with pytest.raises(GiteaError, match="lacks content/sha"):
        client.get_file("installed-set.json")


def test_exists_distinguishes_present_from_absent() -> None:
    assert gitea(lambda _: httpx.Response(200, json=[])).exists("apps/demo")
    assert not gitea(lambda _: httpx.Response(404)).exists("apps/demo")


def test_exists_fails_hard_on_a_server_error() -> None:
    with pytest.raises(GiteaError, match="returned 503"):
        gitea(lambda _: httpx.Response(503)).exists("apps/demo")


def test_update_file_sends_the_branch_and_returns_the_commit() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["body"] = request.read().decode("utf-8")
        return httpx.Response(200, json={"commit": {"sha": "c0ffee00"}})

    assert gitea(handler).update_file("p", "text", "blob1", "msg") == "c0ffee00"
    assert seen["method"] == "PUT"
    assert '"branch":"main"' in str(seen["body"])
    assert base64.b64encode(b"text").decode("ascii") in str(seen["body"])


def test_update_file_fails_hard_on_a_conflict() -> None:
    client = gitea(lambda _: httpx.Response(409, text="sha mismatch"))
    with pytest.raises(GiteaError, match="returned 409"):
        client.update_file("p", "text", "stale", "msg")


def test_update_file_rejects_a_response_without_a_commit() -> None:
    client = gitea(lambda _: httpx.Response(200, json={}))
    with pytest.raises(GiteaError, match="no commit sha"):
        client.update_file("p", "text", "blob1", "msg")


def test_delete_path_resolves_the_blob_sha_first() -> None:
    methods: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        methods.append(request.method)
        if request.method == "GET":
            return httpx.Response(200, json=file_body("{}"))
        return httpx.Response(200, json={"commit": {"sha": "dead00"}})

    assert gitea(handler).delete_path("appset-inputs/demo.json", "msg") == "dead00"
    assert methods == ["GET", "DELETE"]


def test_delete_path_fails_hard_when_the_delete_is_refused() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(200, json=file_body("{}"))
        return httpx.Response(422)

    with pytest.raises(GiteaError, match="returned 422"):
        gitea(handler).delete_path("appset-inputs/demo.json", "msg")


def test_gitea_wraps_transport_errors() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route to host")

    with pytest.raises(GiteaError, match="no route to host"):
        gitea(handler).exists("apps/demo")


def test_argo_requires_a_base_url_and_token() -> None:
    with pytest.raises(ArgoError, match="base URL"):
        ArgoClient("", "t")
    with pytest.raises(ArgoError, match="token"):
        ArgoClient("https://k8s.test", "")


def appset(finalizers: list[str]) -> dict[str, object]:
    return {"spec": {"template": {"metadata": {"finalizers": finalizers}}}}


def test_require_cascade_accepts_the_wired_finalizer() -> None:
    client = argo(
        lambda _: httpx.Response(
            200, json=appset(["resources-finalizer.argocd.argoproj.io"])
        )
    )
    client.require_cascade()


def test_require_cascade_refuses_without_the_finalizer() -> None:
    client = argo(lambda _: httpx.Response(200, json=appset([])))
    with pytest.raises(ArgoError, match="finalizer-missing"):
        client.require_cascade()


def test_require_cascade_refuses_when_the_applicationset_is_absent() -> None:
    client = argo(lambda _: httpx.Response(404))
    with pytest.raises(ArgoError, match=f"ApplicationSet '{APPLICATIONSET}' is absent"):
        client.require_cascade()


def test_require_cascade_fails_hard_when_the_cluster_errors() -> None:
    client = argo(lambda _: httpx.Response(401))
    with pytest.raises(ArgoError, match="cluster-unreachable"):
        client.require_cascade()


def test_status_of_reads_sync_and_health() -> None:
    application = {"status": {"sync": {"status": "Synced"}, "health": {"status": "OK"}}}
    assert ArgoClient.status_of(application) == ("Synced", "OK")
    assert ArgoClient.status_of({}) == ("Unknown", "Unknown")
    assert ArgoClient.status_of(None) == ("absent", "absent")


def synced(status: str, health: str) -> dict[str, object]:
    return {"status": {"sync": {"status": status}, "health": {"status": health}}}


def test_wait_synced_returns_once_the_application_converges() -> None:
    states = iter([synced("OutOfSync", "Progressing"), synced("Synced", "Healthy")])
    client = argo(lambda _: httpx.Response(200, json=next(states)))
    assert client.wait_synced("demo")["sync"] == "Synced"


def test_wait_synced_times_out_loudly() -> None:
    client = argo(
        lambda _: httpx.Response(200, json=synced("OutOfSync", "Degraded")),
        ticks=[0.0, 400.0],
    )
    with pytest.raises(ArgoError, match="did not converge"):
        client.wait_synced("demo")


def test_wait_absent_returns_once_the_application_is_gone() -> None:
    states = iter([httpx.Response(200, json=synced("Synced", "Healthy")), None])
    client = argo(lambda _: next(states) or httpx.Response(404))
    assert client.wait_absent("demo")["sync"] == "absent"


def test_app_namespaces_selects_only_this_apps_projects() -> None:
    body = {
        "items": [
            {"metadata": {"name": "kp-demo-two"}},
            {"metadata": {"name": "kp-demo-one"}},
            {"metadata": {"name": "kp-other-one"}},
            {"metadata": {"name": "vpath-platform"}},
        ]
    }
    client = argo(lambda _: httpx.Response(200, json=body))
    assert client.app_namespaces("demo") == ["kp-demo-one", "kp-demo-two"]


def test_app_namespaces_fails_hard_on_a_malformed_list() -> None:
    client = argo(lambda _: httpx.Response(200, json={"items": "nope"}))
    with pytest.raises(ArgoError, match="namespace list is malformed"):
        client.app_namespaces("demo")
