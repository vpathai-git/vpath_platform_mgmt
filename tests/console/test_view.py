"""Axis 1: does one shape really carry every type, and does it stay honest?

Two things are being tested, and the second matters more.  The first is that
the generic view has the same keys for a NUC, a standalone and a customer
cluster.  The second is that it never fills a gap in: an unprobed instance, an
undeclared field and a missing OntoGate view each have to arrive at the shell
labelled as what they are.
"""

from __future__ import annotations

from pathlib import Path

from vpath_platform_mgmt.console import view
from vpath_platform_mgmt.instances import probe, registry

GENERIC_KEYS = {"status", "healthy", "apps", "uptime", "state", "operations"}


def read(path: Path, name: str) -> dict:
    loaded = registry.load(path)
    return view.instance_view(loaded.get(name), None)


# --- one shape over every type --------------------------------------------


def test_every_type_arrives_in_the_same_shape(console_register: Path) -> None:
    payload = view.build(registry.load(console_register))

    assert [i["name"] for i in payload["instances"]] == [
        "mercury8",
        "terra",
        "alpha",
        "juno",
        "bravo",
    ]
    for item in payload["instances"]:
        assert set(item["generic"]) == GENERIC_KEYS
        assert len(item["locations"]) == 4
        assert {p["title"] for p in item["panels"]} >= {"Measured", "Not establishable"}


def test_every_panel_has_the_same_keys_so_a_renderer_can_loop(
    console_register: Path,
) -> None:
    """A panel missing a key breaks any generic renderer, shell or terminal."""
    for item in view.build(registry.load(console_register))["instances"]:
        for panel in item["panels"]:
            assert set(panel) == {"title", "rows", "note"}


def test_each_instance_names_the_template_that_creates_its_kind(
    console_register: Path,
) -> None:
    payload = view.build(registry.load(console_register))
    by_name = {i["name"]: i for i in payload["instances"]}

    assert by_name["mercury8"]["template"] == "nuc"
    assert by_name["terra"]["template"] == "cloud-vm"
    assert by_name["alpha"]["template"] == "standalone"
    assert by_name["juno"]["template"] == "remote"


def test_type_specific_panels_differ_by_type(console_register: Path) -> None:
    assert read(console_register, "mercury8")["panels"][0]["title"] == "Server box"
    assert read(console_register, "alpha")["panels"][0]["title"] == "Standalone shell"
    assert "unproven" in read(console_register, "juno")["panels"][0]["title"]


def test_operations_are_what_the_code_can_actually_drive(
    console_register: Path,
) -> None:
    assert read(console_register, "mercury8")["generic"]["operations"] == [
        "probe",
        "exec",
        "gradle",
        "deliver",
    ]
    assert read(console_register, "alpha")["generic"]["operations"] == ["probe"]
    assert read(console_register, "juno")["generic"]["operations"] == []


# --- the honesty rules -----------------------------------------------------


def test_an_unprobed_instance_says_so_rather_than_looking_down(
    console_register: Path,
) -> None:
    payload = view.build(registry.load(console_register))

    assert payload["probed_at"] is None
    for item in payload["instances"]:
        assert item["generic"]["status"] == view.NOT_PROBED
        assert item["generic"]["healthy"] is False


def test_a_probed_view_is_stamped_with_when_it_was_measured(
    console_register: Path, silent_runner: probe.Runner
) -> None:
    loaded = registry.load(console_register)
    readings = [probe.read_instance(i, 1, silent_runner) for i in loaded.instances]

    payload = view.build(loaded, readings)

    assert payload["probed_at"] is not None
    assert payload["probed_at"].endswith("Z")


def test_a_supplied_stamp_is_not_overwritten(
    console_register: Path, silent_runner: probe.Runner
) -> None:
    loaded = registry.load(console_register)
    readings = [probe.read_instance(loaded.get("juno"), 1, silent_runner)]

    payload = view.build(loaded, readings, probed_at="2026-07-28T09:00:00Z")

    assert payload["probed_at"] == "2026-07-28T09:00:00Z"


def test_an_undeclared_location_answer_is_marked_undeclared(
    console_register: Path,
) -> None:
    answers = {a["field"]: a for a in read(console_register, "mercury8")["locations"]}

    assert answers["LOCATION"]["declared"] is True
    assert answers["LOCATION"]["value"] == "lab rack 2 / /workspace"
    assert answers["BUILD_PROCESS"]["declared"] is False
    assert "not declared" in answers["BUILD_PROCESS"]["detail"]


def test_all_four_location_questions_are_asked_of_every_type(
    console_register: Path,
) -> None:
    for name in ("mercury8", "terra", "alpha", "juno", "bravo"):
        fields = [a["field"] for a in read(console_register, name)["locations"]]
        assert fields == ["LOCATION", "BUILD_PROCESS", "SOURCE_REPOS", "IMAGE_REGISTRY"]
        for answer in read(console_register, name)["locations"]:
            assert answer["question"].endswith("?")


def test_a_declared_ontogate_view_becomes_a_link(console_register: Path) -> None:
    gate = read(console_register, "mercury8")["ontogate"]

    assert gate["available"] is True
    assert gate["url"] == "http://127.0.0.1:8731"


def test_a_missing_ontogate_view_is_shown_as_missing_not_as_a_dead_link(
    console_register: Path,
) -> None:
    gate = read(console_register, "terra")["ontogate"]

    assert gate["available"] is False
    assert gate["url"] == ""
    assert "auto-picked port" in gate["detail"]


def test_apps_report_that_axis_three_has_not_started(console_register: Path) -> None:
    apps = read(console_register, "mercury8")["generic"]["apps"]

    assert "not managed yet" in apps
    assert "explorer-quick-extraction.issue.md" in apps


def test_uptime_is_reported_as_unmeasured_not_as_last_install(
    console_register: Path,
) -> None:
    """Relabelling the install marker as uptime would be plausible and wrong."""
    uptime = read(console_register, "mercury8")["generic"]["uptime"]

    assert uptime.startswith("not measured")
    assert "platform services healthy since" in uptime


def test_a_remote_instance_is_unproven_rather_than_unreachable(
    console_register: Path, silent_runner: probe.Runner
) -> None:
    loaded = registry.load(console_register)
    reading = probe.read_instance(loaded.get("juno"), 1, silent_runner)

    item = view.instance_view(loaded.get("juno"), reading)

    assert item["generic"]["status"] == probe.UNPROVEN
    assert any("access path" in row["label"] for row in item["panels"][2]["rows"])


def test_a_planned_instance_is_planned_not_unproven(
    console_register: Path, silent_runner: probe.Runner
) -> None:
    loaded = registry.load(console_register)
    reading = probe.read_instance(loaded.get("bravo"), 1, silent_runner)

    assert reading.verdict == probe.PLANNED


def test_a_reading_that_established_nothing_says_so(
    console_register: Path, silent_runner: probe.Runner
) -> None:
    loaded = registry.load(console_register)
    reading = probe.read_instance(loaded.get("terra"), 1, silent_runner)

    item = view.instance_view(loaded.get("terra"), reading)
    measured = next(p for p in item["panels"] if p["title"] == "Measured")

    assert measured["note"] == "the probe established nothing"


def test_an_unprobed_instance_names_that_nobody_looked(console_register: Path) -> None:
    measured = next(
        p for p in read(console_register, "terra")["panels"] if p["title"] == "Measured"
    )

    assert "nobody has looked" in measured["note"]
