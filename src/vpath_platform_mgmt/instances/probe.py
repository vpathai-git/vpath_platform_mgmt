"""One run over every declared instance: is it running, since when, which version.

What it reads, and why it reads that
------------------------------------
Nothing here is a new health check.  Every fact already exists on the instance;
what was missing was a way to ask from here.  For a **server** environment the
probe opens one SSH connection and reads five things that the platform itself
produces:

    running       deployments ready, from the cluster
    platform      the platform's own /api/version answering at all
    version       build_id out of that same answer
    last install  mtime of the pipeline's platformReady phase-gate marker
    image sha     the vpath.git.sha label the build stamps onto an image

The port and the target directory are **not** stored in the register.  They are
read from the box's own env profile at probe time, so that each of them keeps
exactly one home -- the server's ``config/dot_env/.env.<profile>``.

It deliberately does **not** execute the pipeline's own
``health-check-platform-ready.sh``: that script is a Gradle-orchestrated gate
that wants the full environment, and it *touches the phase-gate marker*.  A
status tool that mutates the thing it measures is not a status tool.

For a **standalone** environment far less is establishable, and that is the
finding rather than a shortcoming of this code: the Electron shell allocates
every port through ``allocatePort()`` -> ``listen(0)``, so a running instance
has no address anyone can know from the outside.  Process presence, home state
and the vendored kit version are readable; health and the running version are
not.  Those are reported as named gaps, never as a guess and never as "down".

Exit codes
----------
    0   every live instance was measured and is healthy
    1   an instance answered and is not healthy
    2   a fact could not be established -- box unreachable, source missing,
        or a structural gap like the standalone address problem
    3   the register no longer describes reality: a planned instance that
        exists, or a box running something other than its checkout

Precedence when several apply: 2 > 1 > 3 > 0.  "Not establishable" outranks
everything because a run that could not look is not a run that found nothing.
"""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from . import transport
from .registry import Instance, Registry, RegistryError, load
from .transport import Runner, TransportError

EXIT_OK = 0
EXIT_UNHEALTHY = 1
EXIT_UNDETERMINED = 2
EXIT_DRIFT = 3

HEALTHY = "HEALTHY"
UNHEALTHY = "UNHEALTHY"
UNREACHABLE = "UNREACHABLE"
STOPPED = "STOPPED"
PLANNED = "PLANNED"
DRIFT = "DRIFT"

# The one remote payload.  Every line it prints is `key=value`; every value is
# accompanied by the path or command it came from, so the caller can quote a
# source for each fact instead of asserting it.
_SERVER_PAYLOAD = r"""
set -u
CO=__CHECKOUT__
PROF=__PROFILE__
if [ -d "$CO/.git" ]; then
  echo "checkout_sha=$(git -C "$CO" rev-parse HEAD 2>/dev/null)"
  echo "checkout_branch=$(git -C "$CO" rev-parse --abbrev-ref HEAD 2>/dev/null)"
else
  echo "checkout_missing=$CO"
fi
ENVFILE="$CO/config/dot_env/.env.$PROF"
TARGET_DIR=""
VPATH_PORT=""
if [ -r "$ENVFILE" ]; then
  echo "envfile=$ENVFILE"
  TARGET_DIR=$(sed -n 's/^TARGET_DIR=//p' "$ENVFILE" | head -1)
  VPATH_PORT=$(sed -n 's/^VPATH_PORT=//p' "$ENVFILE" | head -1)
  echo "target_dir=$TARGET_DIR"
  echo "vpath_port=$VPATH_PORT"
else
  echo "envfile_missing=$ENVFILE"
fi
if [ -n "$TARGET_DIR" ]; then
  MARK="$CO/$TARGET_DIR/phase-gates/platformReady.marker"
  if [ -f "$MARK" ]; then
    echo "marker=$MARK"
    echo "marker_mtime=$(date -u -r "$MARK" +%Y-%m-%dT%H:%M:%SZ)"
  else
    echo "marker_missing=$MARK"
  fi
fi
if [ -n "$VPATH_PORT" ]; then
  URL="https://127.0.0.1:$VPATH_PORT/api/version"
  echo "api_url=$URL"
  BODY=$(curl -sk -m 10 "$URL" 2>/dev/null | tr -d '\n')
  if [ -n "$BODY" ]; then echo "api_body=$BODY"; else echo "api_silent=$URL"; fi
fi
DEP=$(sudo k3s kubectl get deploy -A --no-headers 2>/dev/null \
  | awk '{n++; split($3,a,"/"); if (a[2]+0>0 && a[1]==a[2]) r++} \
         END {if (n>0) printf "%d/%d", r, n}')
if [ -n "$DEP" ]; then
  echo "deployments=$DEP"
else
  echo "deployments_unavailable=sudo k3s kubectl get deploy -A"
fi
for img in $(sudo docker images --format '{{.Repository}}:{{.Tag}}' 2>/dev/null \
             | grep '^vpath-' | head -30); do
  L=$(sudo docker inspect -f '{{index .Config.Labels "vpath.git.sha"}}' \
      "$img" 2>/dev/null)
  if [ -n "$L" ]; then echo "image=$img"; echo "image_sha=$L"; break; fi
done
"""


def server_payload(instance: Instance) -> str:
    """The read-only script this probe runs on a server instance."""
    return _SERVER_PAYLOAD.replace(
        "__CHECKOUT__", shlex.quote(instance.checkout)
    ).replace("__PROFILE__", shlex.quote(instance.env_profile))


@dataclass
class Fact:
    """One measured statement and the thing that produced it."""

    label: str
    value: str
    source: str


@dataclass
class Reading:
    """Everything the probe established about one instance."""

    name: str
    kind: str
    verdict: str
    facts: list[Fact] = field(default_factory=list)
    gaps: list[Fact] = field(default_factory=list)

    def add(self, label: str, value: str, source: str) -> None:
        self.facts.append(Fact(label, value, source))

    def gap(self, label: str, reason: str, source: str) -> None:
        self.gaps.append(Fact(label, reason, source))


def parse_payload(stdout: str) -> dict[str, str]:
    """Read back the payload's ``key=value`` lines, ignoring anything else."""
    out: dict[str, str] = {}
    for line in stdout.splitlines():
        if "=" in line:
            key, _, value = line.partition("=")
            key = key.strip()
            if key and key.isidentifier():
                out[key] = value.strip()
    return out


def _build_id(api_body: str) -> str:
    try:
        parsed = json.loads(api_body)
    except json.JSONDecodeError:
        return ""
    value = parsed.get("build_id", "")
    return value if isinstance(value, str) else ""


def _note_checkout(reading: Reading, instance: Instance, values: dict[str, str]) -> str:
    """What commit the box's own checkout stands on."""
    checkout_sha = values.get("checkout_sha", "")
    if checkout_sha:
        branch = values.get("checkout_branch", "?")
        reading.add(
            "checkout", f"{checkout_sha[:12]} ({branch})", f"git -C {instance.checkout}"
        )
    else:
        reading.gap(
            "checkout",
            f"no git checkout at {values.get('checkout_missing', instance.checkout)}",
            instance.source,
        )
    if "envfile" in values:
        reading.add("env profile", instance.env_profile, values["envfile"])
    else:
        reading.gap(
            "env profile",
            f"unreadable: {values.get('envfile_missing', '?')}",
            instance.source,
        )
    return checkout_sha


def _note_running(reading: Reading, instance: Instance, values: dict[str, str]) -> str:
    """Whether the platform answers, and with which build."""
    api_body = values.get("api_body", "")
    build_id = _build_id(api_body)
    if build_id:
        reading.add("platform", "answers", values.get("api_url", "/api/version"))
        reading.add("version", build_id[:12], "/api/version build_id")
    elif "api_silent" in values:
        reading.verdict = UNHEALTHY
        reading.add("platform", "silent", values["api_silent"])
    elif api_body:
        reading.verdict = UNHEALTHY
        reading.add("platform", "non-JSON answer", values.get("api_url", "?"))
    else:
        reading.gap(
            "platform", "port not established from the profile", instance.source
        )

    deployments = values.get("deployments", "")
    if deployments:
        ready, _, total = deployments.partition("/")
        reading.add("deployments", deployments, "k3s kubectl get deploy -A")
        if ready != total:
            reading.verdict = UNHEALTHY
    else:
        reading.gap(
            "deployments",
            "cluster did not answer",
            values.get("deployments_unavailable", "k3s kubectl"),
        )
    return build_id


def _note_history(reading: Reading, values: dict[str, str]) -> None:
    """When the pipeline last declared the platform ready, and from which build."""
    if "marker_mtime" in values:
        reading.add("last install", values["marker_mtime"], values.get("marker", "?"))
    else:
        reading.gap(
            "last install",
            f"no phase-gate marker: {values.get('marker_missing', 'path not derived')}",
            "server pipeline phase gate",
        )
    image_sha = values.get("image_sha", "")
    if image_sha:
        reading.add(
            "image sha",
            image_sha[:12] + ("-dirty" if image_sha.endswith("-dirty") else ""),
            f"{values.get('image', 'image')} label vpath.git.sha",
        )
    else:
        reading.gap(
            "image sha",
            "no image carries a vpath.git.sha label (built before labelling)",
            "docker inspect",
        )


def _unreachable(reading: Reading, why: str, source: str) -> Reading:
    reading.verdict = UNREACHABLE
    reading.gap("access", why, source)
    return reading


def _read_server(instance: Instance, timeout: int, runner: Runner) -> Reading:
    reading = Reading(instance.name, instance.kind, HEALTHY)
    try:
        result = transport.ssh(
            instance, server_payload(instance), timeout=timeout, runner=runner
        )
    except TransportError as exc:
        return _unreachable(reading, str(exc), instance.source)
    if not result.ok:
        why = (result.stderr.strip() or f"exit {result.returncode}").splitlines()[-1]
        return _unreachable(reading, why, result.command)

    values = parse_payload(result.stdout)
    checkout_sha = _note_checkout(reading, instance, values)
    build_id = _note_running(reading, instance, values)
    _note_history(reading, values)

    # Does the box run what its own checkout says it should?
    if build_id and checkout_sha and not build_id.startswith(checkout_sha[:12]):
        if reading.verdict == HEALTHY:
            reading.verdict = DRIFT
        reading.add(
            "drift",
            f"running {build_id[:12]}, checkout {checkout_sha[:12]}",
            "/api/version vs git rev-parse HEAD",
        )
    return reading


def _read_standalone(instance: Instance, timeout: int, runner: Runner) -> Reading:
    reading = Reading(instance.name, instance.kind, STOPPED)

    kit_version = Path(instance.app_root) / "kit" / "VERSION"
    if kit_version.is_file():
        sha = ""
        for line in kit_version.read_text(encoding="utf-8").splitlines():
            if line.startswith("source_sha:"):
                sha = line.split(":", 1)[1].strip()
        if sha:
            reading.add("kit version", sha[:12], str(kit_version))
        else:
            reading.gap("kit version", "no source_sha line", str(kit_version))
    else:
        reading.gap("kit version", f"missing: {kit_version}", instance.source)

    state_db = Path(instance.home) / "runtime" / "state.db"
    if state_db.is_file():
        when = datetime.fromtimestamp(state_db.stat().st_mtime, tz=timezone.utc)
        reading.add("last activity", when.strftime("%Y-%m-%dT%H:%M:%SZ"), str(state_db))
    else:
        reading.gap("last activity", f"no runtime state at {state_db}", instance.source)

    processes = runner(["ps", "-Ao", "pid=,command="], timeout)
    if processes.ok:
        needles = [n for n in (instance.home, instance.app_root) if n]
        hits = [
            line
            for line in processes.stdout.splitlines()
            if any(needle in line for needle in needles)
        ]
        if hits:
            reading.verdict = HEALTHY
            reading.add("running", f"{len(hits)} process(es)", processes.command)
        else:
            reading.add("running", "no process found", processes.command)
    else:
        reading.gap("running", "process table unreadable", processes.command)

    # The structural gap.  Named, not guessed and not conflated with "down".
    reading.gap(
        "health / running version",
        "a standalone allocates every port through listen(0); a running "
        "instance has no address that can be known from outside",
        "vpath_server/standalone/src/main/supervisor.ts allocatePort()",
    )
    return reading


def read_instance(instance: Instance, timeout: int, runner: Runner) -> Reading:
    if instance.is_planned:
        reading = Reading(instance.name, instance.kind, PLANNED)
        existing = Path(instance.home) if instance.home else None
        if existing is not None and existing.exists():
            reading.verdict = DRIFT
            reading.add(
                "drift", f"declared planned but {existing} exists", instance.source
            )
        else:
            reading.add("state", "declared, not built yet", instance.source)
        return reading
    if instance.is_server:
        return _read_server(instance, timeout, runner)
    return _read_standalone(instance, timeout, runner)


def exit_code(readings: Sequence[Reading]) -> int:
    """Precedence 2 > 1 > 3 > 0 -- the same ladder the pin tool uses."""
    if any(r.gaps for r in readings) or any(r.verdict == UNREACHABLE for r in readings):
        return EXIT_UNDETERMINED
    if any(r.verdict == UNHEALTHY for r in readings):
        return EXIT_UNHEALTHY
    if any(r.verdict == DRIFT for r in readings):
        return EXIT_DRIFT
    return EXIT_OK


def render(registry: Registry, readings: Sequence[Reading]) -> str:
    lines = [f"register: {registry.path}", ""]
    for reading in readings:
        lines.append(f"{reading.name}  [{reading.kind}]  {reading.verdict}")
        for fact in reading.facts:
            lines.append(f"    {fact.label:<14} {fact.value:<30} {fact.source}")
        for gap in reading.gaps:
            lines.append(f"    ! {gap.label:<12} not establishable: {gap.value}")
            lines.append(f"      {'':<12}   source: {gap.source}")
        lines.append("")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None, runner: Runner = transport.run) -> int:
    parser = argparse.ArgumentParser(
        prog="vpath-instance-status",
        description="Read every declared instance: running, last install, version.",
    )
    parser.add_argument("--register", type=Path, default=None)
    parser.add_argument("--instance", default=None, help="probe only this one")
    parser.add_argument("--timeout", type=int, default=90, help="seconds per instance")
    parsed = parser.parse_args(argv)

    try:
        registry = load(parsed.register)
        targets = (
            [registry.get(parsed.instance)]
            if parsed.instance
            else list(registry.instances)
        )
    except RegistryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_UNDETERMINED

    readings = [read_instance(i, parsed.timeout, runner) for i in targets]
    print(render(registry, readings))
    return exit_code(readings)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
