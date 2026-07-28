"""Engine adapters: how verbs actually execute.

``SimulatedEngine`` is for development and tests — no side effects.
``LocalEngine`` runs the real engine as subprocesses inside the server
checkout on the host it runs on (the shared server: build host == deploy
host, per docs/ops_isolation_plan/06_mvp.md). There is deliberately no
SSH-from-elsewhere adapter: the Ops API runs beside the engine.
"""

from __future__ import annotations

import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from vpath_platform_mgmt.ops.model import Job, Verb

StepEmitter = Callable[[str], None]

HEALTH_GATES = ("infra", "platform", "apps", "data", "workflow-ready")

OUTPUT_TAIL_LINES = 40


class EngineFailure(RuntimeError):
    """A verb failed in the engine; message carries the reason/output tail."""


class EngineAdapter(Protocol):
    """Executes one job's verb, emitting progress steps as it goes."""

    name: str

    def run(self, job: Job, emit: StepEmitter) -> dict[str, object] | None:
        """Execute the job; return an optional structured result."""
        ...  # pragma: no cover - protocol signature


SIMULATED_STEPS: dict[Verb, list[str]] = {
    Verb.BUILD: [
        "resolving app contract",
        "gradlew buildApp",
        "pushing image to platform registry",
    ],
    Verb.DEPLOY: [
        "digest check in platform registry",
        "gradlew redeployApp",
        "waiting for rollout",
        "health gate",
    ],
    Verb.HEALTH: ["running health-check-* gates", "probing HTTPS paths"],
    Verb.STATUS: ["collecting status"],
    Verb.LOGS: ["fetching logs"],
    Verb.UNINSTALL: ["bin/vpath uninstall", "verifying removal"],
    Verb.REINSTALL: ["gradlew goReinstall", "provisioning", "full health gate"],
    Verb.ERASE: ["eraseInstallation", "verifying clean state"],
}


class SimulatedEngine:
    """Side-effect-free engine: walks realistic steps, returns canned results."""

    name = "simulated"

    def __init__(self, step_delay: float = 0.0) -> None:
        self._step_delay = step_delay

    def run(self, job: Job, emit: StepEmitter) -> dict[str, object] | None:
        """Walk the verb's steps; health-like verbs return an all-pass verdict."""
        for step in SIMULATED_STEPS[job.verb]:
            emit(step)
            if self._step_delay:
                time.sleep(self._step_delay)
        if job.verb in (Verb.HEALTH, Verb.REINSTALL):
            return {
                "verdict": "healthy",
                "gates": {gate: "pass" for gate in HEALTH_GATES},
            }
        if job.verb == Verb.BUILD:
            return {"digest": f"sha256:simulated-{job.app}"}
        return None


ENGINE_COMMANDS: dict[Verb, list[str]] = {
    Verb.BUILD: ["./gradlew", "buildApp", "-Papp={app}"],
    Verb.DEPLOY: ["./gradlew", "redeployApp", "-Papp={app}"],
    Verb.HEALTH: ["bin/vpath", "status"],
    Verb.STATUS: ["bin/vpath", "status"],
    Verb.LOGS: ["bin/vpath", "logs", "{app}"],
    Verb.UNINSTALL: ["bin/vpath", "uninstall", "{app}"],
    Verb.REINSTALL: ["./gradlew", "goReinstall"],
    Verb.ERASE: ["./gradlew", "goReinstall", "-Pfull"],
}


class LocalEngine:
    """Runs verbs as subprocesses in the server checkout on this host.

    This is the temporary Gradle adapter from the plan (decision 2): valid
    only where the checkout lives — the shared server itself. Fails hard at
    construction if the checkout is absent; no silent fallback to simulation.
    """

    name = "local"

    def __init__(self, server_checkout: Path) -> None:
        if not server_checkout.is_dir():
            raise ValueError(
                f"server checkout not found: {server_checkout} — LocalEngine "
                "must run on the host that holds the engine (see 06_mvp.md)"
            )
        self._checkout = server_checkout

    def command(self, verb: Verb, app: str) -> list[str]:
        """Argv for a verb, with the app name substituted."""
        return [part.format(app=app) for part in ENGINE_COMMANDS[verb]]

    def run(self, job: Job, emit: StepEmitter) -> dict[str, object] | None:
        """Execute the verb's command in the checkout; fail loud on non-zero."""
        argv = self.command(job.verb, job.app)
        emit(" ".join(argv))
        completed = subprocess.run(
            argv,
            cwd=self._checkout,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        tail_lines = (completed.stdout + completed.stderr).splitlines()
        tail = "\n".join(tail_lines[-OUTPUT_TAIL_LINES:])
        if completed.returncode != 0:
            raise EngineFailure(f"{argv[0]} exited {completed.returncode}:\n{tail}")
        emit("engine call completed")
        return {"output_tail": tail}
