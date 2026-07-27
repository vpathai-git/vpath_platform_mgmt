"""Pick an environment, then drive the server pipeline against it.

The problem it solves
---------------------
Switching an install between boxes used to mean editing
``config/dot_env/.env.<profile>`` by hand and hoping the edit was undone
afterwards.  The register already knows every box; this is the door that turns
that knowledge into an invocation.

What it does **not** do
-----------------------
It does not install, build or deploy anything itself.  Every action is the
server project's own pipeline, invoked where that pipeline expects to be
invoked: in the checkout on the box, with the box's env profile.  This module
contributes exactly one thing -- resolving a name to *which box, which
checkout, which profile*.  If it ever grows a second way to do what the
pipeline already does, that is a defect, not a feature.

Commands
--------
    list                        every declared instance
    show    <name>              resolved coordinates of one
    exec    <name> -- <cmd>     run a command on the box
    gradle  <name> -- <args>    cd <checkout> && ./gradlew -Penv=<profile> <args>
    deliver <name> --sha <sha>  push a commit to the box and fast-forward it

Exit codes
----------
    0   the action ran and succeeded
    1   the action ran on the instance and failed there
    2   the truth could not be established: no register, unknown instance,
        missing key, unreachable box, an action the instance's kind cannot do

Nothing is skipped silently and there is no default instance: an unknown name
aborts.  A deploy to the wrong box is the most expensive mistake this tool
could make, so it is the one thing it is built to make impossible.
"""

from __future__ import annotations

import argparse
import shlex
import sys
from pathlib import Path
from typing import Sequence

from . import transport
from .registry import Instance, Registry, RegistryError, load
from .transport import Runner, TransportError

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_UNDETERMINED = 2

MASK = "<masked>"


def _masked(value: str, mask: bool) -> str:
    return MASK if (mask and value) else value


def gradle_command(instance: Instance, args: Sequence[str]) -> str:
    """The exact line the server pipeline is started with, on the box.

    ``-Penv`` is the pipeline's own switch; the register supplies its value and
    the working directory, nothing else.
    """
    if not instance.is_server:
        raise TransportError(
            f"{instance.name}: kind {instance.kind!r} has no Gradle pipeline"
        )
    quoted = " ".join(shlex.quote(arg) for arg in args)
    return (
        f"cd {shlex.quote(instance.checkout)} && "
        f"./gradlew -Penv={shlex.quote(instance.env_profile)} {quoted}"
    )


def deliver_commands(instance: Instance, sha: str, branch: str) -> tuple[str, str]:
    """The two halves of the sanctioned delivery channel.

    Verbatim the procedure in the server's README (use case 4b): push the exact
    commit into the box's checkout over SSH, then fast-forward **only** there.
    Never ``reset --hard`` -- the checkout carries box-local state.
    """
    if not instance.is_server:
        raise TransportError(
            f"{instance.name}: kind {instance.kind!r} is not a delivery target"
        )
    push = (
        f"git push --no-verify "
        f"{shlex.quote(instance.ssh_target + ':' + instance.checkout)} "
        f"{shlex.quote(sha)}:refs/heads/{branch}"
    )
    merge = (
        f"cd {shlex.quote(instance.checkout)} && "
        f"git merge --ff-only {shlex.quote(branch)}"
    )
    return push, merge


# --- commands --------------------------------------------------------------


def cmd_list(registry: Registry, mask: bool) -> int:
    width = max((len(i.name) for i in registry.instances), default=4)
    print(f"register: {registry.path}")
    for instance in registry.instances:
        if instance.is_server:
            where = _masked(instance.ssh_target, mask)
            detail = f"{where}  -Penv={instance.env_profile}"
        else:
            detail = _masked(instance.app_root, mask)
        planned = "  [planned]" if instance.is_planned else ""
        print(f"  {instance.name:<{width}}  {instance.kind:<16}  {detail}{planned}")
    return EXIT_OK


def cmd_show(instance: Instance, mask: bool) -> int:
    print(f"name       {instance.name}")
    print(f"kind       {instance.kind}")
    print(f"lifecycle  {instance.lifecycle}")
    if instance.is_server:
        print(f"ssh        {_masked(instance.ssh_target, mask)}")
        print(f"ssh key    {_masked(instance.ssh_key, mask) or '<ssh default>'}")
        print(f"profile    {instance.env_profile}")
        print(f"checkout   {_masked(instance.checkout, mask)}")
    else:
        print(f"app root   {_masked(instance.app_root, mask)}")
        print(f"home       {_masked(instance.home, mask)}")
    if instance.notes:
        print(f"notes      {instance.notes}")
    print(f"declared   {instance.source}")
    return EXIT_OK


def _run_remote(
    instance: Instance,
    remote: str,
    *,
    print_only: bool,
    timeout: int,
    runner: Runner,
) -> int:
    if print_only:
        print(" ".join(transport.ssh_argv(instance, remote)))
        return EXIT_OK
    result = transport.ssh(instance, remote, timeout=timeout, runner=runner)
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return EXIT_OK if result.ok else EXIT_FAILED


def cmd_deliver(
    instance: Instance,
    sha: str,
    branch: str,
    *,
    print_only: bool,
    timeout: int,
    runner: Runner,
) -> int:
    """Push a commit to the box, then fast-forward it -- as one chain.

    The push and the merge are a guard and the action it guards: if the push
    does not land, the merge must not run.  They are chained, never issued as
    two independent commands whose first failure leaves the second to proceed.
    """
    transport.require_ssh(instance)
    push, merge = deliver_commands(instance, sha, branch)
    if print_only:
        print(push)
        print(" ".join(transport.ssh_argv(instance, merge)))
        return EXIT_OK
    push_result = runner(shlex.split(push), timeout)
    sys.stdout.write(push_result.stdout)
    sys.stderr.write(push_result.stderr)
    if not push_result.ok:
        print(f"delivery aborted: push failed ({push_result.command})", file=sys.stderr)
        return EXIT_FAILED
    return _run_remote(
        instance, merge, print_only=False, timeout=timeout, runner=runner
    )


# --- entry point -----------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vpath-instance",
        description="Select a platform environment and drive the server "
        "pipeline against it.",
    )
    parser.add_argument(
        "--register", type=Path, default=None, help="path to the instance register"
    )
    parser.add_argument(
        "--mask",
        action="store_true",
        help="mask hosts, users and paths (for pasting into a report)",
    )
    parser.add_argument(
        "--timeout", type=int, default=transport.DEFAULT_TIMEOUT, help="seconds"
    )
    parser.add_argument(
        "--print",
        dest="print_only",
        action="store_true",
        help="print the exact command instead of running it",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="every declared instance")

    show = sub.add_parser("show", help="resolved coordinates of one instance")
    show.add_argument("name")

    execute = sub.add_parser("exec", help="run a command on the instance")
    execute.add_argument("name")
    execute.add_argument("args", nargs=argparse.REMAINDER)

    gradle = sub.add_parser("gradle", help="run the server pipeline on the instance")
    gradle.add_argument("name")
    gradle.add_argument("args", nargs=argparse.REMAINDER)

    deliver = sub.add_parser("deliver", help="deliver a commit to the instance")
    deliver.add_argument("name")
    deliver.add_argument("--sha", required=True)
    deliver.add_argument("--branch", default=None, help="delivery branch name")

    return parser


def _strip_separator(args: list[str]) -> list[str]:
    return args[1:] if args and args[0] == "--" else args


def main(argv: Sequence[str] | None = None, runner: Runner = transport.run) -> int:
    parsed = build_parser().parse_args(argv)
    try:
        registry = load(parsed.register)
        if parsed.command == "list":
            return cmd_list(registry, parsed.mask)

        instance = registry.get(parsed.name)
        if parsed.command == "show":
            return cmd_show(instance, parsed.mask)

        if parsed.command == "exec":
            args = _strip_separator(parsed.args)
            if not args:
                print("exec needs a command", file=sys.stderr)
                return EXIT_UNDETERMINED
            return _run_remote(
                instance,
                " ".join(args),
                print_only=parsed.print_only,
                timeout=parsed.timeout,
                runner=runner,
            )

        if parsed.command == "gradle":
            args = _strip_separator(parsed.args)
            if not args:
                print("gradle needs at least one task", file=sys.stderr)
                return EXIT_UNDETERMINED
            return _run_remote(
                instance,
                gradle_command(instance, args),
                print_only=parsed.print_only,
                timeout=parsed.timeout,
                runner=runner,
            )

        branch = parsed.branch or f"delivery-{parsed.sha[:12]}"
        return cmd_deliver(
            instance,
            parsed.sha,
            branch,
            print_only=parsed.print_only,
            timeout=parsed.timeout,
            runner=runner,
        )
    except (RegistryError, TransportError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_UNDETERMINED


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
