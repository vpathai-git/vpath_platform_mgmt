"""Tests for the GitOps engine: publish by commit, converge by ArgoCD."""

from __future__ import annotations

import base64
import json

import httpx
import pytest

from vpath_platform_mgmt.ops.argocd import ArgoClient
from vpath_platform_mgmt.ops.engine import EngineFailure
from vpath_platform_mgmt.ops.gitea import GiteaClient
from vpath_platform_mgmt.ops.gitops_engine import GitOpsEngine
from vpath_platform_mgmt.ops.model import Job, Role, Verb

CASCADE = {
    "spec": {
        "template": {
            "metadata": {"finalizers": ["resources-finalizer.argocd.argoproj.io"]}
        }
    }
}
HEALTHY = {"status": {"sync": {"status": "Synced"}, "health": {"status": "Healthy"}}}


class FakeRecord:
    """An in-memory Deploy-of-Record plus the cluster that reconciles it."""

    def __init__(self, apps: list[str], rendered: list[str]) -> None:
        self.files: dict[str, str] = {
            "installed-set.json": json.dumps(
                {"schema_version": 1, "apps": apps, "workflows": []}
            )
        }
        for name in rendered:
            self.files[f"appset-inputs/{name}.json"] = json.dumps({"automated": True})
        self.dirs = {f"apps/{name}" for name in rendered}
        self.applications = {name: HEALTHY for name in apps}
        self.namespaces: list[str] = []
        self.commits: list[str] = []
        self.deleted: list[str] = []

    def gitea(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path.split("/contents/", 1)[1]
        if request.method == "GET":
            if path in self.files:
                content = base64.b64encode(self.files[path].encode()).decode()
                return httpx.Response(
                    200, json={"type": "file", "content": content, "sha": "blob1"}
                )
            if path in self.dirs:
                return httpx.Response(200, json=[])
            return httpx.Response(404)
        body = json.loads(request.read())
        if request.method == "DELETE":
            self.files.pop(path, None)
            self.deleted.append(path)
        else:
            self.files[path] = base64.b64decode(body["content"]).decode()
        self.commits.append(body["message"])
        return httpx.Response(200, json={"commit": {"sha": "c0ffee00"}})

    def cluster(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/applicationsets/vpath-apps"):
            return httpx.Response(200, json=CASCADE)
        if path == "/api/v1/namespaces":
            items = [{"metadata": {"name": n}} for n in self.namespaces]
            return httpx.Response(200, json={"items": items})
        name = path.rsplit("/", 1)[1]
        found = self.applications.get(name)
        return httpx.Response(404) if found is None else httpx.Response(200, json=found)


def engine_for(fake: FakeRecord) -> GitOpsEngine:
    gitea = GiteaClient(
        "https://gitea.test",
        "platform",
        "k8s-manifests",
        "token",
        client=httpx.Client(
            base_url="https://gitea.test", transport=httpx.MockTransport(fake.gitea)
        ),
    )
    argo = ArgoClient(
        "https://k8s.test",
        "token",
        client=httpx.Client(
            base_url="https://k8s.test", transport=httpx.MockTransport(fake.cluster)
        ),
        sleep=lambda _: None,
    )
    return GitOpsEngine(gitea, argo)


def run(fake: FakeRecord, verb: Verb, app: str = "demo") -> dict[str, object]:
    engine = engine_for(fake)
    job = Job(verb=verb, app=app, actor="alice", role=Role.APP_DEV)
    result = engine.run(job, lambda step: None)
    assert result is not None
    return result


def test_engine_is_named_gitops() -> None:
    assert GitOpsEngine.name == "gitops"


@pytest.mark.parametrize(
    ("verb", "task"),
    [
        (Verb.BUILD, "./gradlew buildApp -Papp=demo"),
        (Verb.REINSTALL, "./gradlew goReinstall"),
        (Verb.ERASE, "./gradlew goReinstall -Pfull"),
    ],
)
def test_build_host_verbs_fail_hard_and_name_the_task(verb: Verb, task: str) -> None:
    fake = FakeRecord(apps=[], rendered=[])
    with pytest.raises(EngineFailure, match="has no GitOps path") as caught:
        run(fake, verb)
    assert task in str(caught.value)
    assert fake.commits == []


def test_logs_are_not_served_by_the_deploy_record() -> None:
    with pytest.raises(EngineFailure, match="not served by the GitOps engine"):
        run(FakeRecord(apps=[], rendered=[]), Verb.LOGS)


def test_deploy_commits_the_set_and_waits_for_sync() -> None:
    fake = FakeRecord(apps=[], rendered=["demo"])
    fake.applications["demo"] = HEALTHY
    result = run(fake, Verb.DEPLOY)
    assert result["commit"] == "c0ffee00"
    assert result["sync"] == "Synced"
    assert json.loads(fake.files["installed-set.json"])["apps"] == ["demo"]
    assert fake.commits == ["install app demo (alice)"]


def test_deploy_refuses_an_app_with_no_render_in_the_record() -> None:
    fake = FakeRecord(apps=[], rendered=[])
    with pytest.raises(EngineFailure, match="deploy never builds implicitly"):
        run(fake, Verb.DEPLOY)
    assert fake.commits == []


def test_uninstall_then_deploy_restores_the_app() -> None:
    """The install/uninstall cycle must be repeatable without a rebuild.

    Uninstall used to delete the ApplicationSet input outright, so deploying
    again required a fresh render on the build host — a one-way door.
    """
    fake = FakeRecord(apps=["demo"], rendered=["demo"])
    del fake.applications["demo"]
    run(fake, Verb.UNINSTALL)
    assert "appset-inputs/demo.json" not in fake.files
    assert "uninstalled/demo.json" in fake.files

    fake.applications["demo"] = HEALTHY
    result = run(fake, Verb.DEPLOY)
    assert result["sync"] == "Synced"
    assert "appset-inputs/demo.json" in fake.files
    assert json.loads(fake.files["installed-set.json"])["apps"] == ["demo"]


def test_deploy_without_any_input_still_demands_a_rebuild() -> None:
    """Neither live nor archived input: only a build can supply one."""
    fake = FakeRecord(apps=[], rendered=["demo"])
    del fake.files["appset-inputs/demo.json"]
    with pytest.raises(EngineFailure, match="no ApplicationSet input"):
        run(fake, Verb.DEPLOY)
    assert fake.commits == []


def test_deploy_refuses_an_app_off_the_automated_lane() -> None:
    fake = FakeRecord(apps=[], rendered=["demo"])
    fake.files["appset-inputs/demo.json"] = json.dumps({"automated": False})
    with pytest.raises(EngineFailure, match="not on the automated GitOps lane"):
        run(fake, Verb.DEPLOY)
    assert fake.commits == []


def test_deploy_refuses_a_malformed_appset_input() -> None:
    fake = FakeRecord(apps=[], rendered=["demo"])
    fake.files["appset-inputs/demo.json"] = "{not json"
    with pytest.raises(EngineFailure, match="not valid JSON"):
        run(fake, Verb.DEPLOY)


def test_deploy_of_an_installed_app_verifies_sync_without_committing() -> None:
    fake = FakeRecord(apps=["demo"], rendered=["demo"])
    result = run(fake, Verb.DEPLOY)
    assert result["commit"] == ""
    assert fake.commits == []


def test_uninstall_removes_the_app_and_its_appset_input() -> None:
    fake = FakeRecord(apps=["demo"], rendered=["demo"])
    del fake.applications["demo"]
    result = run(fake, Verb.UNINSTALL)
    assert result["sync"] == "absent"
    assert json.loads(fake.files["installed-set.json"])["apps"] == []
    assert fake.deleted == ["appset-inputs/demo.json"]


def test_uninstall_refuses_while_project_instances_depend_on_the_app() -> None:
    fake = FakeRecord(apps=["demo"], rendered=["demo"])
    fake.namespaces = ["kp-demo-alpha"]
    with pytest.raises(EngineFailure, match="template-in-use") as caught:
        run(fake, Verb.UNINSTALL)
    assert "-Pforce" in str(caught.value)
    assert fake.commits == []


def test_uninstall_refuses_an_app_that_is_not_installed() -> None:
    fake = FakeRecord(apps=[], rendered=["demo"])
    with pytest.raises(EngineFailure, match="nothing to uninstall"):
        run(fake, Verb.UNINSTALL)


def test_status_reports_the_set_and_each_application() -> None:
    fake = FakeRecord(apps=["demo", "other"], rendered=["demo"])
    del fake.applications["other"]
    result = run(fake, Verb.STATUS, app="")
    assert result["installed"] == ["demo", "other"]
    applications = result["applications"]
    assert isinstance(applications, dict)
    assert applications["demo"]["sync"] == "Synced"
    assert applications["other"]["sync"] == "absent"


def test_status_of_one_app_reports_only_that_app() -> None:
    fake = FakeRecord(apps=["demo", "other"], rendered=["demo"])
    applications = run(fake, Verb.STATUS)["applications"]
    assert isinstance(applications, dict)
    assert list(applications) == ["demo"]


def test_health_passes_when_every_installed_app_is_synced() -> None:
    result = run(FakeRecord(apps=["demo"], rendered=["demo"]), Verb.HEALTH)
    assert result["verdict"] == "healthy"
    assert result["gates"] == {"demo": "pass"}


def test_health_is_degraded_when_an_application_is_missing() -> None:
    fake = FakeRecord(apps=["demo"], rendered=["demo"])
    del fake.applications["demo"]
    result = run(fake, Verb.HEALTH)
    assert result["verdict"] == "degraded"
    assert result["gates"] == {"demo": "fail (absent/absent)"}


def test_a_cluster_failure_surfaces_as_an_engine_failure() -> None:
    fake = FakeRecord(apps=[], rendered=["demo"])
    fake.cluster = lambda _: httpx.Response(500)  # type: ignore[assignment]
    with pytest.raises(EngineFailure, match="cluster-unreachable"):
        run(fake, Verb.DEPLOY)
