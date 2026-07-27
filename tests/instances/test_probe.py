"""The probe: does it judge hard, and does it keep "unknown" apart from "broken".

The distinction the whole tool turns on is the one between *unhealthy* and *not
establishable*.  Every red drill below drives one source into failure and
asserts which of the two the probe chose -- and the exit code that follows.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from vpath_platform_mgmt.instances import probe
from vpath_platform_mgmt.instances.registry import load

from .conftest import PAYLOAD_HEALTHY, runner_returning


def _read(
    register: Path, name: str, payload: str, returncode: int = 0
) -> probe.Reading:
    instance = load(register).get(name)
    return probe.read_instance(
        instance, 30, runner_returning(payload, returncode=returncode)
    )


def _facts(reading: probe.Reading) -> dict[str, str]:
    return {f.label: f.value for f in reading.facts}


def _gaps(reading: probe.Reading) -> dict[str, str]:
    return {g.label: g.value for g in reading.gaps}


# --- the payload the probe sends -----------------------------------------


def test_the_payload_carries_the_boxs_own_checkout_and_profile(
    register: Path,
) -> None:
    payload = probe.server_payload(load(register).get("boxone"))
    assert "CO=/workspace" in payload
    assert "PROF=nuc" in payload


def test_the_payload_reads_the_port_from_the_profile_not_from_the_register(
    register: Path,
) -> None:
    payload = probe.server_payload(load(register).get("boxone"))
    assert "sed -n 's/^VPATH_PORT=//p'" in payload
    assert "30600" not in payload, "a port literal here would be a second home for it"


def test_the_payload_never_touches_the_phase_gate_marker(register: Path) -> None:
    payload = probe.server_payload(load(register).get("boxone"))
    assert "touch" not in payload
    assert "health-check-platform-ready.sh" not in payload


# --- a healthy server ----------------------------------------------------


def test_a_healthy_box_reports_all_five_facts(register: Path) -> None:
    reading = _read(register, "boxone", PAYLOAD_HEALTHY)
    facts = _facts(reading)
    assert reading.verdict == probe.HEALTHY
    assert facts["version"] == "1a2c51dc7891"
    assert facts["deployments"] == "53/53"
    assert facts["last install"] == "2026-07-26T04:52:25Z"
    assert facts["image sha"] == "1a2c51dc7891-dirty"
    assert facts["checkout"] == "1a2c51dc7891 (main)"
    assert reading.gaps == []


def test_every_fact_names_the_source_it_came_from(register: Path) -> None:
    reading = _read(register, "boxone", PAYLOAD_HEALTHY)
    for fact in reading.facts:
        assert fact.source, f"{fact.label} was reported without a source"


def test_a_healthy_fleet_exits_zero(register: Path) -> None:
    assert (
        probe.exit_code([_read(register, "boxone", PAYLOAD_HEALTHY)]) == probe.EXIT_OK
    )


# --- red drills: unhealthy ------------------------------------------------


def test_a_silent_platform_is_unhealthy_not_unknown(register: Path) -> None:
    payload = PAYLOAD_HEALTHY.replace(
        'api_body={"version":"2.0.0","build_id":'
        '"1a2c51dc78910a4c2fc9d8c93ab5492c6a8d3c54"}',
        "api_silent=https://127.0.0.1:30600/api/version",
    )
    reading = _read(register, "boxone", payload)
    assert reading.verdict == probe.UNHEALTHY
    assert _facts(reading)["platform"] == "silent"
    # A platform that is provably not answering is a *determined* verdict.  It
    # is not softened into "could not establish" just because the version it
    # would have reported is now unknowable -- that is the consequence of the
    # defect, not a second, independent failure to look.
    assert probe.exit_code([reading]) == probe.EXIT_UNHEALTHY


def test_deployments_not_all_ready_is_unhealthy(register: Path) -> None:
    reading = _read(register, "boxone", PAYLOAD_HEALTHY.replace("53/53", "51/53"))
    assert reading.verdict == probe.UNHEALTHY
    assert probe.exit_code([reading]) == probe.EXIT_UNHEALTHY


# --- red drills: not establishable ---------------------------------------


def test_an_unreachable_box_is_unknown_never_unhealthy(register: Path) -> None:
    reading = _read(register, "boxone", "", returncode=255)
    assert reading.verdict == probe.UNREACHABLE
    assert probe.exit_code([reading]) == probe.EXIT_UNDETERMINED


def test_a_missing_image_label_is_unknown_not_a_defect(register: Path) -> None:
    payload = "\n".join(
        line
        for line in PAYLOAD_HEALTHY.splitlines()
        if not line.startswith(("image=", "image_sha="))
    )
    reading = _read(register, "boxone", payload)
    assert reading.verdict == probe.HEALTHY
    assert "vpath.git.sha" in _gaps(reading)["image sha"]
    assert probe.exit_code([reading]) == probe.EXIT_UNDETERMINED


def test_a_missing_marker_is_a_named_gap(register: Path) -> None:
    payload = PAYLOAD_HEALTHY.replace(
        "marker_mtime=2026-07-26T04:52:25Z", "marker_missing=/workspace/no/such"
    )
    reading = _read(register, "boxone", payload)
    assert "/workspace/no/such" in _gaps(reading)["last install"]


def test_an_unreadable_env_profile_is_a_named_gap(register: Path) -> None:
    payload = "checkout_sha=abc\ncheckout_branch=main\nenvfile_missing=/nope\n"
    reading = _read(register, "boxone", payload)
    assert "/nope" in _gaps(reading)["env profile"]


def test_a_cluster_that_does_not_answer_is_a_gap_not_zero_deployments(
    register: Path,
) -> None:
    payload = PAYLOAD_HEALTHY.replace(
        "deployments=53/53", "deployments_unavailable=sudo k3s kubectl get deploy -A"
    )
    reading = _read(register, "boxone", payload)
    assert "deployments" in _gaps(reading)
    assert "deployments" not in _facts(reading)


# --- red drill: register drift -------------------------------------------


def test_a_box_running_something_other_than_its_checkout_is_drift(
    register: Path,
) -> None:
    payload = PAYLOAD_HEALTHY.replace(
        "checkout_sha=1a2c51dc78910a4c2fc9d8c93ab5492c6a8d3c54",
        "checkout_sha=ffffffffffffffffffffffffffffffffffffffff",
    )
    reading = _read(register, "boxone", payload)
    assert reading.verdict == probe.DRIFT
    assert probe.exit_code([reading]) == probe.EXIT_DRIFT


def test_a_planned_instance_is_not_a_failure(register: Path) -> None:
    reading = _read(register, "later", "")
    assert reading.verdict == probe.PLANNED
    assert probe.exit_code([reading]) == probe.EXIT_OK


def test_a_planned_instance_that_exists_is_drift(tmp_path: Path) -> None:
    home = tmp_path / "exists"
    home.mkdir()
    path = tmp_path / "r.env"
    path.write_text(
        "VPATH_INSTANCES=later\n"
        "LATER_KIND=standalone\n"
        "LATER_LIFECYCLE=planned\n"
        f"LATER_HOME={home}\n",
        encoding="utf-8",
    )
    reading = probe.read_instance(load(path).get("later"), 30, runner_returning(""))
    assert reading.verdict == probe.DRIFT
    assert probe.exit_code([reading]) == probe.EXIT_DRIFT


# --- the standalone gap ---------------------------------------------------


def test_a_standalone_reports_its_kit_version_and_last_activity(
    register: Path,
) -> None:
    reading = _read(register, "standalone1", "")
    facts = _facts(reading)
    assert facts["kit version"] == "09ede4b209e4"
    assert facts["last activity"].endswith("Z")


def test_a_standalone_with_no_process_is_stopped_not_unhealthy(
    register: Path,
) -> None:
    reading = _read(register, "standalone1", "some unrelated process\n")
    assert reading.verdict == probe.STOPPED
    assert _facts(reading)["running"] == "no process found"


def test_a_standalone_with_a_process_referencing_its_home_is_running(
    register: Path,
) -> None:
    home = load(register).get("standalone1").home
    reading = _read(register, "standalone1", f"123 electron --user-data-dir={home}/p\n")
    assert reading.verdict == probe.HEALTHY
    assert "1 process" in _facts(reading)["running"]


def test_the_standalone_address_gap_is_always_named(register: Path) -> None:
    reading = _read(register, "standalone1", "")
    gap = _gaps(reading)["health / running version"]
    assert "listen(0)" in gap
    assert probe.exit_code([reading]) == probe.EXIT_UNDETERMINED


# --- exit-code ladder -----------------------------------------------------


def test_not_establishable_outranks_unhealthy(register: Path) -> None:
    unknown = _read(register, "boxone", "", returncode=255)
    unhealthy = _read(register, "boxone", PAYLOAD_HEALTHY.replace("53/53", "0/53"))
    assert probe.exit_code([unhealthy, unknown]) == probe.EXIT_UNDETERMINED


def test_unhealthy_outranks_drift(register: Path) -> None:
    drift = _read(
        register,
        "boxone",
        PAYLOAD_HEALTHY.replace(
            "checkout_sha=1a2c51dc78910a4c2fc9d8c93ab5492c6a8d3c54",
            "checkout_sha=ffffffffffffffffffffffffffffffffffffffff",
        ),
    )
    unhealthy = _read(register, "boxone", PAYLOAD_HEALTHY.replace("53/53", "0/53"))
    assert probe.exit_code([unhealthy, drift]) == probe.EXIT_UNHEALTHY


# --- the CLI --------------------------------------------------------------


def test_the_cli_renders_every_instance_and_returns_the_ladder(
    register: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = probe.main(
        ["--register", str(register)], runner=runner_returning(PAYLOAD_HEALTHY)
    )
    out = capsys.readouterr().out
    for name in ("boxone", "boxtwo", "standalone1", "later"):
        assert name in out
    assert "not establishable" in out
    assert code == probe.EXIT_UNDETERMINED


def test_the_cli_can_probe_one_instance(
    register: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = probe.main(
        ["--register", str(register), "--instance", "boxone"],
        runner=runner_returning(PAYLOAD_HEALTHY),
    )
    out = capsys.readouterr().out
    assert "boxone" in out and "boxtwo" not in out
    assert code == probe.EXIT_OK


def test_the_cli_without_a_register_is_undetermined(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = probe.main(["--register", str(tmp_path / "no.env")])
    assert code == probe.EXIT_UNDETERMINED
    assert "no instance register" in capsys.readouterr().err


def test_the_payload_parser_ignores_noise() -> None:
    parsed = probe.parse_payload("noise\nkey=value\n= nothing\nother=a=b\n")
    assert parsed == {"key": "value", "other": "a=b"}
