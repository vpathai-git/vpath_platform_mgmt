"""The selector: does it aim at exactly the box it was told, and refuse otherwise.

The dangerous failure of this tool is not an error message -- it is a command
that runs successfully against the wrong instance.  So most of what is asserted
here is the *shape of the invocation*: which host, which checkout, which
profile.
"""

from __future__ import annotations

import shlex
import sys
from pathlib import Path

import pytest

from vpath_platform_mgmt.instances import selector, transport
from vpath_platform_mgmt.instances.registry import RegistryError, load
from vpath_platform_mgmt.instances.transport import TransportError

from .conftest import recording_runner, runner_returning


def ssh_command_of(push: str) -> list[str]:
    """The ``core.sshCommand`` the push configures, wherever it sits."""
    for part in shlex.split(push):
        if part.startswith("core.sshCommand="):
            return shlex.split(part.split("=", 1)[1])
    raise AssertionError(f"the push configures no transport: {push}")


# --- the invocation is built from the register, not from a default --------


def test_gradle_runs_in_the_boxs_checkout_with_the_boxs_profile(
    register: Path,
) -> None:
    box = load(register).get("boxone")
    assert selector.gradle_command(box, ["deployPipeline"]) == (
        "cd /workspace && ./gradlew -Penv=nuc deployPipeline"
    )


def test_gradle_passes_pipeline_arguments_through_untouched(register: Path) -> None:
    box = load(register).get("boxtwo")
    line = selector.gradle_command(box, ["redeployApp", "-Papp=vpath-web"])
    assert line.endswith("./gradlew -Penv=vm5 redeployApp -Papp=vpath-web")


def test_two_instances_produce_two_different_targets(register: Path) -> None:
    registry = load(register)
    one = transport.ssh_argv(registry.get("boxone"), "true")
    two = transport.ssh_argv(registry.get("boxtwo"), "true")
    assert "boxuser@10.0.0.1" in one and "cloud@203.0.113.7" in two
    assert one != two


def test_the_key_from_the_register_is_the_key_that_is_used(
    register: Path, ssh_key: Path
) -> None:
    argv = transport.ssh_argv(load(register).get("boxone"), "true")
    assert argv[argv.index("-i") + 1] == str(ssh_key)


def test_an_instance_without_a_key_uses_the_ssh_default(register: Path) -> None:
    assert "-i" not in transport.ssh_argv(load(register).get("boxtwo"), "true")


def test_delivery_pushes_then_fast_forwards_and_never_resets(register: Path) -> None:
    push, merge = selector.deliver_commands(load(register).get("boxone"), "abc123", "d")
    assert "push --no-verify boxuser@10.0.0.1:/workspace " in push
    assert push.endswith("abc123:refs/heads/d")
    assert merge == "cd /workspace && git merge --ff-only d"
    assert "reset" not in merge


def test_the_commit_is_read_from_the_register_not_from_the_working_directory(
    register: Path, source_checkout: Path
) -> None:
    """S-220: without ``-C`` git resolves the sha against the process cwd.

    The field form: following the runbook (``cd .../vpath_platform_mgmt && …
    selector deliver …``) died with ``fatal: bad object <sha>`` /
    ``remote unpack failed``, because the sha exists in the server checkout and
    not in the management checkout the shell happened to stand in.
    """
    push, _ = selector.deliver_commands(load(register).get("boxone"), "abc123", "d")
    argv = shlex.split(push)
    assert argv[0] == "git"
    assert "-C" in argv, f"the push names no source repository: {push}"
    assert argv[argv.index("-C") + 1] == str(source_checkout)


def test_the_push_carries_the_registers_key(register: Path, ssh_key: Path) -> None:
    """S-18: git spawns its own ssh -- the register's key must be handed to it.

    Without this the push authenticates as whatever the agent offers, which on
    a cloud box is ``Permission denied (publickey)``: the delivery channel dies
    while every other command against the same box still works.
    """
    push, _ = selector.deliver_commands(load(register).get("boxone"), "abc123", "d")
    ssh_command = ssh_command_of(push)
    assert "-i" in ssh_command, (
        "the push would reach the box without the register's key -- "
        f"Permission denied (publickey) on any box that needs one: {push}"
    )
    assert ssh_command[ssh_command.index("-i") + 1] == str(ssh_key)
    assert "BatchMode=yes" in ssh_command


def test_the_pushs_transport_is_the_same_one_every_command_uses(
    register: Path,
) -> None:
    """One idea of the transport, not two: same options as ``ssh_argv``."""
    box = load(register).get("boxone")
    push, _ = selector.deliver_commands(box, "abc123", "d")
    from_ssh = transport.ssh_argv(box, "true")[:-2]
    assert ssh_command_of(push) == from_ssh


def test_a_box_without_a_key_still_pushes_in_batch_mode(register: Path) -> None:
    """No key in the register means the ssh default -- never an interactive
    prompt that would hang the delivery."""
    push, _ = selector.deliver_commands(load(register).get("boxtwo"), "abc123", "d")
    ssh_command = ssh_command_of(push)
    assert "-i" not in ssh_command
    assert "BatchMode=yes" in ssh_command


def test_an_overriding_environment_aborts_instead_of_pushing_with_a_stray_key(
    register: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``GIT_SSH_COMMAND`` outranks ``core.sshCommand`` -- refuse, never guess."""
    monkeypatch.setenv("GIT_SSH_COMMAND", "ssh -i /tmp/somebody-elses-key")
    with pytest.raises(TransportError, match="GIT_SSH_COMMAND is set"):
        selector.deliver_commands(load(register).get("boxone"), "abc123", "d")


def test_exec_reaches_the_box_and_reports_its_exit(
    register: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    runner, seen = recording_runner("up 9 hours\n")
    code = selector.main(
        ["--register", str(register), "exec", "boxone", "--", "uptime"], runner=runner
    )
    assert code == selector.EXIT_OK
    assert seen[0][-2:] == ("boxuser@10.0.0.1", "uptime")
    assert "up 9 hours" in capsys.readouterr().out


def test_print_runs_nothing(register: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner, seen = recording_runner()
    code = selector.main(
        ["--register", str(register), "--print", "gradle", "boxone", "--", "tasks"],
        runner=runner,
    )
    assert code == selector.EXIT_OK
    assert seen == []
    assert "./gradlew -Penv=nuc tasks" in capsys.readouterr().out


def test_masking_hides_hosts_and_paths(
    register: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    selector.main(["--register", str(register), "--mask", "show", "boxone"])
    out = capsys.readouterr().out
    assert "10.0.0.1" not in out and "/workspace" not in out
    assert "boxone" in out and "nuc" in out


def test_list_shows_every_instance(
    register: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert selector.main(["--register", str(register), "list"]) == selector.EXIT_OK
    out = capsys.readouterr().out
    for name in ("boxone", "boxtwo", "standalone1", "later"):
        assert name in out
    assert "[planned]" in out


# --- red drills -----------------------------------------------------------


def test_an_unknown_instance_aborts_rather_than_picking_one(
    register: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    runner, seen = recording_runner()
    code = selector.main(
        ["--register", str(register), "exec", "mars", "--", "uptime"], runner=runner
    )
    assert code == selector.EXIT_UNDETERMINED
    assert seen == [], "nothing may run when the target could not be resolved"
    assert "unknown instance 'mars'" in capsys.readouterr().err


def test_a_missing_register_aborts(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = selector.main(["--register", str(tmp_path / "no.env"), "list"])
    assert code == selector.EXIT_UNDETERMINED
    assert "no instance register" in capsys.readouterr().err


def test_a_standalone_has_no_gradle_pipeline(register: Path) -> None:
    with pytest.raises(TransportError, match="no Gradle pipeline"):
        selector.gradle_command(load(register).get("standalone1"), ["tasks"])


def test_a_standalone_is_not_an_ssh_target(register: Path) -> None:
    with pytest.raises(TransportError, match="no SSH access"):
        transport.ssh_argv(load(register).get("standalone1"), "true")


def test_a_planned_server_refuses_to_be_addressed(tmp_path: Path) -> None:
    path = tmp_path / "r.env"
    path.write_text(
        "VPATH_INSTANCES=mars\nMARS_KIND=server-nuc\nMARS_LIFECYCLE=planned\n",
        encoding="utf-8",
    )
    with pytest.raises(TransportError, match="does not exist yet"):
        transport.require_ssh(load(path).get("mars"))


def test_a_missing_key_names_where_to_get_it(tmp_path: Path) -> None:
    path = tmp_path / "r.env"
    path.write_text(
        "VPATH_INSTANCES=box\n"
        "BOX_KIND=server-cloud-vm\n"
        "BOX_SSH_HOST=1.2.3.4\n"
        "BOX_SSH_USER=u\n"
        f"BOX_SSH_KEY={tmp_path}/absent.pem\n"
        "BOX_SSH_KEY_SOURCE=bundle.zip::key.pem\n"
        "BOX_ENV_PROFILE=vm5\n"
        "BOX_CHECKOUT=/workspace\n",
        encoding="utf-8",
    )
    with pytest.raises(TransportError, match="extract it from bundle.zip::key.pem"):
        transport.require_ssh(load(path).get("box"))


def test_a_failing_remote_command_is_reported_as_failed(register: Path) -> None:
    code = selector.main(
        ["--register", str(register), "exec", "boxone", "--", "false"],
        runner=runner_returning("", returncode=7, stderr="boom"),
    )
    assert code == selector.EXIT_FAILED


def test_a_failed_push_never_leaves_the_merge_to_run(
    register: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[tuple[str, ...]] = []

    def runner(argv, timeout):  # type: ignore[no-untyped-def]
        calls.append(tuple(argv))
        return transport.CommandResult(tuple(argv), 1, "", "remote rejected")

    code = selector.main(
        ["--register", str(register), "deliver", "boxone", "--sha", "abc123"],
        runner=runner,
    )
    assert code == selector.EXIT_FAILED
    assert len(calls) == 1, "the merge must not run after a failed push"
    assert "delivery aborted" in capsys.readouterr().err


def _register_without_a_source_checkout(tmp_path: Path, source: str = "") -> Path:
    path = tmp_path / "r.env"
    path.write_text(
        "VPATH_INSTANCES=box\n"
        "BOX_KIND=server-nuc\n"
        "BOX_SSH_HOST=10.0.0.9\n"
        "BOX_SSH_USER=u\n"
        "BOX_ENV_PROFILE=nuc\n"
        "BOX_CHECKOUT=/workspace\n" + source,
        encoding="utf-8",
    )
    return path


def test_a_register_without_a_source_checkout_aborts_instead_of_using_the_cwd(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The defect this replaced was a silent one: git fell back to the cwd.

    So the absence of the field must stop the delivery, name the field and name
    the file to write it in -- never push whatever the shell's directory holds.
    """
    path = _register_without_a_source_checkout(tmp_path)
    runner, seen = recording_runner()
    code = selector.main(
        ["--register", str(path), "deliver", "box", "--sha", "abc123"], runner=runner
    )
    assert code == selector.EXIT_UNDETERMINED
    assert seen == [], "nothing may be pushed when the source repository is unknown"
    err = capsys.readouterr().err
    assert "BOX_SOURCE_CHECKOUT" in err and str(path) in err


def test_a_source_checkout_that_does_not_exist_is_named(tmp_path: Path) -> None:
    path = _register_without_a_source_checkout(
        tmp_path, f"BOX_SOURCE_CHECKOUT={tmp_path}/absent\n"
    )
    with pytest.raises(RegistryError, match="which is not a directory"):
        selector.deliver_commands(load(path).get("box"), "abc123", "d")


def test_exec_without_a_command_aborts(register: Path) -> None:
    runner, seen = recording_runner()
    code = selector.main(["--register", str(register), "exec", "boxone"], runner=runner)
    assert code == selector.EXIT_UNDETERMINED
    assert seen == []


def test_gradle_without_a_task_aborts(register: Path) -> None:
    runner, seen = recording_runner()
    code = selector.main(
        ["--register", str(register), "gradle", "boxone"], runner=runner
    )
    assert code == selector.EXIT_UNDETERMINED
    assert seen == []


def test_a_missing_ssh_binary_is_an_error_not_a_silence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(TransportError, match="not found on this machine"):
        transport.run(["definitely-not-a-command-4711"])


def test_a_timeout_is_its_own_outcome() -> None:
    # sys.executable instead of `sleep`: the binary does not exist on Windows,
    # and this test is about the timeout contract, not about coreutils.
    sleeper = [sys.executable, "-c", "import time; time.sleep(5)"]
    result = transport.run(sleeper, timeout=1)
    assert result.returncode == 124 and "timed out" in result.stderr
