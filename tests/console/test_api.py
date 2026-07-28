"""The single entry point: same answers to the shell and to a human.

Every command is exercised through :func:`main`, because that is what the
Electron shell spawns.  The exit codes matter as much as the output -- the
shell decides whether to show an error dialog from them, so a refused edit
(1) must never be confused with a register it could not read (2).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

import pytest

from vpath_platform_mgmt.console import api
from vpath_platform_mgmt.instances import registry
from vpath_platform_mgmt.instances.templates import TemplateError
from vpath_platform_mgmt.instances.transport import CommandResult


def no_runner(argv: Sequence[str], timeout: int) -> CommandResult:
    return CommandResult(argv=tuple(argv), returncode=1, stdout="", stderr="no")


def run(*argv: str) -> int:
    return api.main(list(argv), runner=no_runner)


# --- view ------------------------------------------------------------------


def test_view_prints_every_instance(
    console_register: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert run("--register", str(console_register), "view") == api.EXIT_OK

    out = capsys.readouterr().out
    for name in ("mercury8", "terra", "alpha", "juno", "bravo"):
        assert name in out
    assert "not probed in this run" in out


def test_view_json_is_what_the_shell_consumes(
    console_register: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert run("--register", str(console_register), "--json", "view") == api.EXIT_OK

    payload = json.loads(capsys.readouterr().out)
    assert payload["probed_at"] is None
    assert len(payload["instances"]) == 5
    assert payload["instances"][0]["generic"]["status"] == "NOT PROBED"


def test_view_probe_stamps_the_run(
    console_register: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = run("--register", str(console_register), "--json", "view", "--probe")

    payload = json.loads(capsys.readouterr().out)
    assert code == api.EXIT_OK
    assert payload["probed_at"] is not None


def test_view_shows_the_four_location_questions_and_the_ontogate_line(
    console_register: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    run("--register", str(console_register), "view")

    out = capsys.readouterr().out
    assert "Location questions" in out
    assert "OntoGate  http://127.0.0.1:8731" in out
    assert "Apps      not managed yet" in out


def test_a_register_that_is_not_there_is_undetermined_not_empty(tmp_path: Path) -> None:
    assert (
        run("--register", str(tmp_path / "nope.env"), "view") == api.EXIT_UNDETERMINED
    )


# --- templates -------------------------------------------------------------


def test_templates_lists_every_shipped_type(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert run("templates") == api.EXIT_OK

    out = capsys.readouterr().out
    for name in ("nuc", "cloud-vm", "standalone", "remote"):
        assert name in out
    assert "[UNPROVEN]" in out


def test_templates_json_carries_the_fields_a_form_is_built_from(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert run("--json", "templates") == api.EXIT_OK

    payloads = {t["name"]: t for t in json.loads(capsys.readouterr().out)}
    assert payloads["remote"]["proven"] is False
    nuc_fields = {f["key"]: f for f in payloads["nuc"]["fields"]}
    assert nuc_fields["SSH_HOST"]["required"] is True
    assert nuc_fields["ENV_PROFILE"]["suggestion"] == "nuc"
    assert nuc_fields["NOTES"]["required"] is False


# --- create / update / remove ---------------------------------------------


def test_create_writes_the_instance(tmp_path: Path) -> None:
    path = tmp_path / "instances.local.env"

    code = run(
        "--register",
        str(path),
        "create",
        "mars",
        "--template",
        "nuc",
        "--set",
        "SSH_HOST=10.0.0.5",
        "--set",
        "SSH_USER=boxuser",
        "--set",
        "ENV_PROFILE=nuc",
        "--set",
        "CHECKOUT=/workspace",
    )

    assert code == api.EXIT_OK
    assert registry.load(path).get("mars").ssh_host == "10.0.0.5"


def test_creating_an_unproven_type_says_so(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "instances.local.env"

    code = run(
        "--register",
        str(path),
        "create",
        "juno",
        "--template",
        "remote",
        "--set",
        "CLUSTER_HOST=cluster.example",
    )

    assert code == api.EXIT_OK
    assert "UNPROVEN:" in capsys.readouterr().out


def test_create_without_the_mandatory_fields_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "instances.local.env"

    code = run("--register", str(path), "create", "mars", "--template", "nuc")

    assert code == api.EXIT_REFUSED
    assert not path.exists()


def test_create_with_an_unknown_template_is_refused(tmp_path: Path) -> None:
    code = run(
        "--register", str(tmp_path / "r.env"), "create", "mars", "--template", "ghost"
    )

    assert code == api.EXIT_REFUSED


def test_create_of_a_name_already_taken_is_undetermined(console_register: Path) -> None:
    code = run(
        "--register",
        str(console_register),
        "create",
        "alpha",
        "--template",
        "standalone",
        "--set",
        "APP_ROOT=/a",
        "--set",
        "HOME=/h",
    )

    assert code == api.EXIT_UNDETERMINED


def test_update_sets_a_field(console_register: Path) -> None:
    code = run(
        "--register",
        str(console_register),
        "update",
        "mercury8",
        "--set",
        "BUILD_PROCESS=on the box",
    )

    assert code == api.EXIT_OK
    assert registry.load(console_register).get("mercury8").build_process == "on the box"


def test_update_of_an_unknown_instance_is_undetermined(console_register: Path) -> None:
    code = run(
        "--register", str(console_register), "update", "ghost", "--set", "NOTES=x"
    )

    assert code == api.EXIT_UNDETERMINED


def test_remove_drops_the_instance(console_register: Path) -> None:
    code = run("--register", str(console_register), "remove", "alpha")

    assert code == api.EXIT_OK
    assert "alpha" not in registry.load(console_register).names()


def test_remove_of_an_unknown_instance_is_undetermined(console_register: Path) -> None:
    assert (
        run("--register", str(console_register), "remove", "ghost")
        == api.EXIT_UNDETERMINED
    )


# --- --set parsing ---------------------------------------------------------


def test_settings_are_upper_cased_and_trimmed() -> None:
    assert api.parse_settings(["ssh_host = 10.0.0.5 "]) == {"SSH_HOST": "10.0.0.5"}


def test_a_setting_without_a_value_is_an_error_not_a_dropped_token() -> None:
    with pytest.raises(TemplateError, match="expects KEY=VALUE"):
        api.parse_settings(["SSH_HOST"])


def test_a_setting_without_a_key_is_an_error() -> None:
    with pytest.raises(TemplateError, match="expects KEY=VALUE"):
        api.parse_settings(["=10.0.0.5"])


def test_a_bad_setting_refuses_the_whole_command(tmp_path: Path) -> None:
    code = run(
        "--register",
        str(tmp_path / "r.env"),
        "create",
        "mars",
        "--template",
        "nuc",
        "--set",
        "SSH_HOST",
    )

    assert code == api.EXIT_REFUSED
