"""GitOps engine adapter: publish by commit, converge by ArgoCD.

This is the API-only path to the cluster. It carries no server checkout and
shells out to nothing: a deploy is one InstalledSet mutation committed into
the Deploy-of-Record through Gitea, after which ArgoCD's ``vpath-apps``
ApplicationSet generates the child Application and syncs it.

What it deliberately cannot do is build. The server's own door is explicit —
*"installApp never builds implicitly"* — because the rendered payload and the
digest-pinned ApplicationSet input are produced on the build host. Verbs that
need the engine fail hard here and name the Gradle task that does the work,
rather than pretending over HTTP.
"""

from __future__ import annotations

import json
from typing import Any

from vpath_platform_mgmt.ops import deploy_record as record
from vpath_platform_mgmt.ops.argocd import ArgoClient, ArgoError
from vpath_platform_mgmt.ops.engine import (
    REACH_NO_ROUTE,
    REACH_REFUSED,
    EngineFailure,
    Reach,
    StepEmitter,
)
from vpath_platform_mgmt.ops.gitea import GiteaClient, GiteaError
from vpath_platform_mgmt.ops.model import Job, Verb

# What each probe reason means for the operator, per door. Unknown reasons
# (an unexpected status) fall back to naming the door and the raw reason —
# never to a cheerful default.
REACH_DETAIL: dict[str, str] = {
    REACH_NO_ROUTE: (
        "no route to {door}; the SSH tunnel is probably down "
        "(ALL_PROXY, or connect-vm5.ps1 on a workstation)"
    ),
    REACH_REFUSED: "{door} rejected the configured token; it may have expired",
}


BUILD_HOST_VERBS: dict[Verb, str] = {
    Verb.BUILD: "./gradlew buildApp -Papp={app}",
    Verb.REINSTALL: "./gradlew goReinstall",
    Verb.ERASE: "./gradlew goReinstall -Pfull",
}


class GitOpsEngine:
    """Executes verbs against the Deploy-of-Record and ArgoCD, over HTTP only."""

    name = "gitops"

    def __init__(self, gitea: GiteaClient, argo: ArgoClient) -> None:
        self._gitea = gitea
        self._argo = argo

    def probe(self) -> Reach:
        """Both doors must answer: the record (Gitea) and the cluster (k8s).

        The door is named because the two fail for different reasons and are
        fixed in different places — a Gitea token expiring and the cluster
        being unroutable are the same red badge but not the same problem.
        """
        for door, client in (
            ("the Deploy-of-Record (Gitea)", self._gitea),
            ("the cluster (Kubernetes API)", self._argo),
        ):
            reason = client.probe()
            if reason:
                template = REACH_DETAIL.get(reason, "{door} answered unexpectedly")
                return Reach(False, reason, template.format(door=door))
        return Reach(True)

    def run(self, job: Job, emit: StepEmitter) -> dict[str, object] | None:
        """Dispatch one verb; every failure is an ``EngineFailure``."""
        handlers = {
            Verb.DEPLOY: self._deploy,
            Verb.UNINSTALL: self._uninstall,
            Verb.STATUS: self._status,
            Verb.HEALTH: self._health,
        }
        handler = handlers.get(job.verb)
        if handler is None:
            raise EngineFailure(self._unsupported(job))
        try:
            return handler(job, emit)
        except (GiteaError, ArgoError, record.InstalledSetError) as exc:
            raise EngineFailure(str(exc)) from exc

    def _unsupported(self, job: Job) -> str:
        task = BUILD_HOST_VERBS.get(job.verb)
        if task is not None:
            return (
                f"'{job.verb.value}' has no GitOps path: it produces or destroys "
                "build output, which only exists on the build host. Remedy: run "
                f"{task.format(app=job.app or '<app>')} there, then deploy."
            )
        return (
            f"'{job.verb.value}' is not served by the GitOps engine; the "
            "Deploy-of-Record carries desired state, not run output."
        )

    def _read_set(self, emit: StepEmitter) -> tuple[dict[str, Any], str]:
        emit(f"reading {record.INSTALLED_SET_PATH} from {self._gitea.repo_slug}")
        current = self._gitea.get_file(record.INSTALLED_SET_PATH)
        return record.parse(current.text), current.sha

    def _require_render(self, app: str, emit: StepEmitter) -> None:
        """The record must already hold this app's digest-pinned render."""
        emit("checking the rendered payload in the deploy record")
        payload = record.payload_path("app", app)
        if not self._gitea.exists(payload):
            raise EngineFailure(
                f"no render for app '{app}' in the Deploy-of-Record ({payload} is "
                "absent); deploy never builds implicitly. Remedy: run "
                f"./gradlew redeployApp -Papp={app} on the build host first."
            )
        input_path = record.appset_input_path(app)
        if not self._gitea.exists(input_path):
            # Uninstall parks the input rather than deleting it, so install can
            # restore exactly what was running. Only a record with neither copy
            # genuinely needs a rebuild.
            archived = record.archived_input_path(app)
            if not self._gitea.exists(archived):
                raise EngineFailure(
                    f"app '{app}' has no ApplicationSet input in the "
                    f"Deploy-of-Record ({input_path} and {archived} are both "
                    "absent), so ArgoCD has nothing to generate from. Remedy: "
                    f"run ./gradlew redeployApp -Papp={app} on the build host "
                    "to render it afresh, then install."
                )
            restored = self._gitea.get_file(archived)
            self._gitea.write_file(
                input_path,
                restored.text,
                f"restore {app} from the uninstalled archive",
            )
            # Consume the archive: it means "currently uninstalled", and a
            # leftover copy makes the next uninstall collide with itself.
            self._gitea.delete_path(archived, f"clear uninstalled archive {app}")
            emit(f"restored {input_path} from {archived}")
        raw = self._gitea.get_file(input_path).text
        try:
            appset_input = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise EngineFailure(f"{input_path} is not valid JSON: {exc}") from exc
        if appset_input.get("automated") is not True:
            raise EngineFailure(
                f"app '{app}' is not on the automated GitOps lane "
                f"({input_path} has automated != true); install cannot promise "
                "render+commit+sync. Remedy: complete the app's GitOps cutover."
            )

    def _deploy(self, job: Job, emit: StepEmitter) -> dict[str, object]:
        self._argo.require_cascade()
        emit("ApplicationSet cascade verified")
        self._require_render(job.app, emit)
        data, sha = self._read_set(emit)
        commit = ""
        if record.contains(data, "app", job.app):
            emit(f"'{job.app}' is already in the InstalledSet — verifying sync only")
        else:
            updated = record.add(data, "app", job.app)
            commit = self._gitea.update_file(
                record.INSTALLED_SET_PATH,
                record.dump(updated),
                sha,
                f"install app {job.app} ({job.actor})",
            )
            emit(f"committed InstalledSet mutation {commit[:8]}")
        emit("waiting for ArgoCD reconciliation")
        converged = self._argo.wait_synced(job.app)
        emit("ArgoCD reports Synced/Healthy")
        return {"commit": commit, **converged}

    def _uninstall(self, job: Job, emit: StepEmitter) -> dict[str, object]:
        self._argo.require_cascade()
        emit("ApplicationSet cascade verified")
        emit("census: looking for dependent project namespaces")
        dependents = self._argo.app_namespaces(job.app)
        if dependents:
            raise EngineFailure(
                f"template-in-use: app '{job.app}' has dependent project "
                f"instances ({', '.join(dependents)}). The GitOps engine does "
                "not force-stop workloads. Remedy: run ./gradlew uninstallApp "
                f"-Papp={job.app} -Pforce on the server, which cancels runs "
                "through platform-api first. The Deploy-of-Record was not changed."
            )
        data, sha = self._read_set(emit)
        if not record.contains(data, "app", job.app):
            raise EngineFailure(
                f"app '{job.app}' is not in the InstalledSet; nothing to uninstall."
            )
        updated = record.remove(data, "app", job.app)
        commit = self._gitea.update_file(
            record.INSTALLED_SET_PATH,
            record.dump(updated),
            sha,
            f"uninstall app {job.app} ({job.actor})",
        )
        emit(f"committed InstalledSet mutation {commit[:8]}")
        # ponytail: the rendered payload under apps/<name>/ is left for the next
        # pushManifests refresh to prune; moving the ApplicationSet input out of
        # the generator's view is what stops the child Application being
        # generated. Upgrade trigger: a record whose stale payloads outgrow the
        # refresh cadence.
        input_path = record.appset_input_path(job.app)
        archived = record.archived_input_path(job.app)
        parked = self._gitea.get_file(input_path).text
        self._gitea.write_file(archived, parked, f"park appset input {job.app}")
        self._gitea.delete_path(input_path, f"uninstall {job.app}")
        emit(f"moved {input_path} to {archived}")
        emit("waiting for the ArgoCD cascade")
        gone = self._argo.wait_absent(job.app)
        emit("ArgoCD reports the Application is absent")
        return {"commit": commit, **gone}

    def _installed_apps(self, emit: StepEmitter) -> list[str]:
        data, _ = self._read_set(emit)
        return [str(name) for name in data[record.array_for("app")]]

    def installed_apps(self) -> list[str]:
        """Apps the server currently has installed, for the app-store view.

        The catalog lists what *exists*; this says what is *installed*, so a
        store surface can tell the two apart instead of offering to install
        something that already runs.
        """
        return self._installed_apps(lambda _step: None)

    def _status(self, job: Job, emit: StepEmitter) -> dict[str, object]:
        apps = self._installed_apps(emit)
        wanted = [job.app] if job.app else apps
        emit(f"reading ArgoCD status for {len(wanted)} application(s)")
        applications = {}
        for app in wanted:
            sync, health = ArgoClient.status_of(self._argo.application(app))
            applications[app] = {"sync": sync, "health": health}
        return {"installed": apps, "applications": applications}

    def _health(self, job: Job, emit: StepEmitter) -> dict[str, object]:
        apps = self._installed_apps(emit)
        emit(f"probing {len(apps)} installed application(s)")
        gates = {}
        for app in apps:
            sync, health = ArgoClient.status_of(self._argo.application(app))
            passed = (sync, health) == ("Synced", "Healthy")
            gates[app] = "pass" if passed else f"fail ({sync}/{health})"
        verdict = "healthy" if all(v == "pass" for v in gates.values()) else "degraded"
        return {"verdict": verdict, "gates": gates}
