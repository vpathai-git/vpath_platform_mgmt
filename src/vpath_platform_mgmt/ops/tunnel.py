"""The SSH tunnel a workstation needs before it can reach an instance.

Nothing about the platform is exposed to the internet, so from a workstation
every engine call goes through an SSH SOCKS proxy. When that proxy is down the
console cannot tell the difference between "the box is gone" and "you have no
route to it" — the probe reasons in ``engine.py`` name it, and this module is
how the operator fixes it without leaving the console.

The boundary this module defends
--------------------------------
The console spawns exactly one command, built here from configuration only.
No part of an HTTP request reaches the argv, there is no shell, and the
coordinates come from the instance profile — never from the caller. Bringing
up a tunnel is the *only* process this application ever starts.

``BatchMode=yes`` matters: without it a missing or passphrase-protected key
turns into an ssh prompt against a stdin nobody is attached to, and the call
hangs instead of failing.
"""

from __future__ import annotations

import socket
import subprocess
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

DEFAULT_SOCKS_PORT = 1085
WAIT_SECONDS = 20.0
POLL_SECONDS = 0.25
CONNECT_TIMEOUT = 0.5

STARTED = "started"
ALREADY_UP = "already-up"

Spawn = Callable[[list[str]], "subprocess.Popen[str]"]


class TunnelError(Exception):
    """The tunnel is not configured, or would not come up."""


def _parse_port(env: Mapping[str, str], name: str, default: int) -> int:
    """Parse and validate a port number from environment, or refuse with TunnelError.

    Uses int() for validation so all non-numeric values (including Unicode
    digits that isdigit() would accept but int() rejects) are caught uniformly.
    """
    raw = env.get(name, "") or str(default)
    try:
        port = int(raw)
    except ValueError:
        raise TunnelError(f"{name} is not a port number: {raw!r}")
    return port


@dataclass(frozen=True)
class TunnelConfig:
    """Where the tunnel goes, and which local port it opens."""

    host: str
    user: str
    key: str
    port: int = DEFAULT_SOCKS_PORT
    ops_port: int = 0

    @property
    def target(self) -> str:
        return f"{self.user}@{self.host}"

    def argv(self) -> list[str]:
        """The one command this application spawns; no caller input in it."""
        forward = (
            ["-L", f"127.0.0.1:{self.ops_port}:127.0.0.1:{self.ops_port}"]
            if self.ops_port
            else []
        )
        return [
            "ssh",
            "-N",
            "-D",
            f"127.0.0.1:{self.port}",
            *forward,
            "-i",
            self.key,
            "-o",
            "BatchMode=yes",
            "-o",
            "ExitOnForwardFailure=yes",
            "-o",
            "ServerAliveInterval=30",
            self.target,
        ]


def from_env(env: Mapping[str, str]) -> TunnelConfig:
    """Read the tunnel's coordinates, or say exactly which one is missing."""
    missing = [
        key
        for key in ("VPATH_MGMT_SSH_HOST", "VPATH_MGMT_SSH_USER", "VPATH_MGMT_SSH_KEY")
        if not env.get(key)
    ]
    if missing:
        raise TunnelError(
            "this instance has no tunnel configured (missing "
            + ", ".join(missing)
            + ") — add them to its .env profile, or start the tunnel yourself"
        )
    return TunnelConfig(
        host=env["VPATH_MGMT_SSH_HOST"],
        user=env["VPATH_MGMT_SSH_USER"],
        key=env["VPATH_MGMT_SSH_KEY"],
        port=_parse_port(env, "VPATH_MGMT_TUNNEL_PORT", DEFAULT_SOCKS_PORT),
        ops_port=_parse_port(env, "VPATH_MGMT_TUNNEL_OPS_PORT", 0),
    )


def is_up(port: int) -> bool:
    """Whether something is already listening on the local SOCKS port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(CONNECT_TIMEOUT)
        return probe.connect_ex(("127.0.0.1", port)) == 0


def _spawn(argv: list[str]) -> "subprocess.Popen[str]":
    return subprocess.Popen(  # noqa: S603 - fixed argv, no shell, no caller input
        argv,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )


def start(
    config: TunnelConfig,
    spawn: Spawn = _spawn,
    listening: Callable[[int], bool] = is_up,
    sleep: Callable[[float], None] = time.sleep,
) -> str:
    """Bring the tunnel up and wait for the port; raise if it will not come.

    Starting a second tunnel on a port that already carries one would fail on
    the bind and leave the working one looking broken, so an existing tunnel
    is reported, never replaced.
    """
    if listening(config.port):
        return ALREADY_UP
    if not Path(config.key).is_file():
        raise TunnelError(f"SSH key not found: {config.key}")

    process = spawn(config.argv())
    waited = 0.0
    while waited < WAIT_SECONDS:
        if listening(config.port):
            return STARTED
        if process.poll() is not None:
            raise TunnelError(_why_it_died(process))
        sleep(POLL_SECONDS)
        waited += POLL_SECONDS

    process.terminate()
    raise TunnelError(
        f"the tunnel did not open 127.0.0.1:{config.port} within "
        f"{WAIT_SECONDS:.0f}s; ssh is still running or the host refused it"
    )


def _why_it_died(process: "subprocess.Popen[str]") -> str:
    """ssh's own last line beats a generic exit code."""
    stderr = process.stderr.read() if process.stderr is not None else ""
    last = (stderr or "").strip().splitlines()
    detail = last[-1] if last else f"exit {process.returncode}"
    return f"ssh exited before the tunnel opened: {detail}"
