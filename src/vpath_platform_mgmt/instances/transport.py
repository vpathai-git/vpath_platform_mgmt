"""The one place a command is spawned -- locally or on an instance.

Everything that talks to a box goes through :func:`run`, and every command that
is built for a box goes through :func:`ssh_argv`.  Keeping that in one module
buys two things: the selector and the probe cannot drift into two different
ideas of how an instance is reached, and a test can substitute the runner
without any process ever being started.

Preconditions fail hard.  A key path that does not exist, a kind that has no
SSH access -- these raise :class:`TransportError` naming the missing thing.
They are never worked around, and there is no default target.
"""

from __future__ import annotations

import os
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from .registry import Instance

DEFAULT_TIMEOUT = 60
DEFAULT_CONNECT_TIMEOUT = 12


class TransportError(Exception):
    """A precondition for reaching an instance is not met."""


@dataclass(frozen=True)
class CommandResult:
    """What a command did, kept whole so callers can quote it as evidence."""

    argv: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    @property
    def command(self) -> str:
        return " ".join(shlex.quote(part) for part in self.argv)


Runner = Callable[[Sequence[str], int], CommandResult]


def run(argv: Sequence[str], timeout: int = DEFAULT_TIMEOUT) -> CommandResult:
    """Run a command and capture it whole.

    A timeout is reported as its own outcome (returncode 124, the shell
    convention) rather than raising: a box that does not answer in time is a
    fact the caller must report, not an exception that aborts the run over the
    remaining instances.
    """
    try:
        completed = subprocess.run(
            list(argv),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return CommandResult(
            argv=tuple(argv),
            returncode=124,
            stdout="",
            stderr=f"timed out after {timeout}s",
        )
    except FileNotFoundError as exc:
        raise TransportError(f"{argv[0]}: not found on this machine") from exc
    return CommandResult(
        argv=tuple(argv),
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def require_live_ops(instance: Instance) -> None:
    """Raise unless this instance may be driven (exec/gradle/deliver)."""
    if instance.is_planned:
        raise TransportError(
            f"{instance.name}: declared as planned in {instance.source}; "
            f"it does not exist yet"
        )
    if not instance.allows_live_ops:
        raise TransportError(
            f"{instance.name}: kind {instance.kind!r} is declared, unproven -- "
            f"live ops refused until its template ops is live"
        )


def require_ssh(instance: Instance) -> None:
    """Raise unless this instance can be reached over SSH right now."""
    require_live_ops(instance)
    if not instance.is_server:
        raise TransportError(
            f"{instance.name}: kind {instance.kind!r} has no SSH access -- "
            f"a standalone is a local process, not a box"
        )
    if instance.ssh_key and not Path(instance.ssh_key).is_file():
        hint = (
            f" -- extract it from {instance.ssh_key_source}"
            if instance.ssh_key_source
            else ""
        )
        raise TransportError(
            f"{instance.name}: SSH key {instance.ssh_key} does not exist{hint}"
        )


def ssh_options(
    instance: Instance,
    *,
    connect_timeout: int = DEFAULT_CONNECT_TIMEOUT,
) -> list[str]:
    """The ssh invocation up to -- but not including -- the target.

    The single place that decides *how* a box is reached: batch mode, connect
    timeout, and the register's key.  Both callers that spawn ssh build on this,
    so there is only one idea of the transport, not two.
    """
    require_ssh(instance)
    argv = [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        f"ConnectTimeout={connect_timeout}",
    ]
    if instance.ssh_key:
        argv += ["-i", instance.ssh_key]
    return argv


def ssh_argv(
    instance: Instance,
    remote_command: str,
    *,
    connect_timeout: int = DEFAULT_CONNECT_TIMEOUT,
) -> list[str]:
    """Build the ssh invocation for one instance.  Never guesses a target."""
    return ssh_options(instance, connect_timeout=connect_timeout) + [
        instance.ssh_target,
        remote_command,
    ]


def git_ssh_command(
    instance: Instance,
    *,
    connect_timeout: int = DEFAULT_CONNECT_TIMEOUT,
) -> str:
    """The ssh transport a ``git push`` to this instance must use.

    ``git push`` does not go through :func:`ssh_argv` -- git spawns its own ssh.
    Without being told, that ssh never sees ``SSH_KEY`` from the register and
    offers whatever the agent happens to hold: on a cloud box that is
    ``Permission denied (publickey)`` and the delivery channel is dead.  The
    string returned here is what ``core.sshCommand`` is set to, built from the
    same options as every other call, so the two cannot drift apart.
    """
    if os.environ.get("GIT_SSH_COMMAND"):
        raise TransportError(
            "GIT_SSH_COMMAND is set in this environment and overrides "
            "core.sshCommand, so the register's key would be ignored -- "
            "unset it before delivering"
        )
    return " ".join(
        shlex.quote(part)
        for part in ssh_options(instance, connect_timeout=connect_timeout)
    )


def ssh(
    instance: Instance,
    remote_command: str,
    *,
    timeout: int = DEFAULT_TIMEOUT,
    runner: Runner = run,
) -> CommandResult:
    """Run one command on one instance."""
    return runner(ssh_argv(instance, remote_command), timeout)
