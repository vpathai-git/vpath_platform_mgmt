"""The versioned type templates: what they promise, and what they refuse.

The load-bearing test here is :func:`test_every_shipped_template_round_trips`.
A template is only worth having if what it renders is something the register
accepts -- so each one is filled in, rendered, written and read back through
the real loader.  Anything less would let a template drift away from the
schema it is supposed to be the vorlage for.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vpath_platform_mgmt.instances import registry, templates
from vpath_platform_mgmt.instances.instance import ALL_KINDS, required_fields
from vpath_platform_mgmt.instances.templates import PLACEHOLDER, TemplateError

SHIPPED = ("cloud-vm", "nuc", "remote", "standalone")


def fill(template: templates.Template) -> dict[str, str]:
    """A plausible value for every mandatory field of a template."""
    return {key: f"value-for-{key.lower()}" for key in template.required_keys}


def write_template(directory: Path, name: str, body: dict[str, object]) -> None:
    (directory / f"{name}.json").write_text(json.dumps(body), encoding="utf-8")


@pytest.fixture()
def template_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    directory = tmp_path / "templates"
    directory.mkdir()
    monkeypatch.setattr(templates, "TEMPLATE_DIR", directory)
    return directory


# --- what ships ------------------------------------------------------------


def test_available_lists_every_shipped_template() -> None:
    assert templates.available() == SHIPPED


def test_every_shipped_template_declares_a_known_kind() -> None:
    for template in templates.load_all():
        assert template.kind in ALL_KINDS


def test_every_kind_can_be_created_from_exactly_one_template() -> None:
    for kind in ALL_KINDS:
        assert templates.template_for_kind(kind).kind == kind


def test_template_required_fields_match_what_the_register_demands() -> None:
    """A template that omits a mandatory field would render an invalid stanza."""
    for template in templates.load_all():
        for key in required_fields(template.kind):
            assert key in template.required_keys, f"{template.name} is missing {key}"


def test_every_shipped_template_is_proven() -> None:
    """The survey closed remote's structure; nothing shipped is guesswork now."""
    for template in templates.load_all():
        assert template.proven is True, f"{template.name} still claims to be unproven"
        assert template.unproven_reason == ""


def test_remote_survived_the_survey_with_a_version_bump() -> None:
    remote = templates.load_template("remote")

    assert remote.version == "1"
    assert remote.proven is True


def test_what_the_console_may_do_on_a_customer_system_stays_open() -> None:
    """The one field no repository can answer: it is an operator decision.

    Marked open in the template rather than filled with a plausible default,
    which on a customer production system is the expensive kind of guess.
    """
    field = templates.load_template("remote").field("CONSOLE_PERMITTED")

    assert "open" in field.comment.lower()
    assert field.required is False


def test_every_shipped_template_offers_the_four_location_questions() -> None:
    for template in templates.load_all():
        keys = {f.key for f in template.fields}
        assert {"LOCATION", "BUILD_PROCESS", "SOURCE_REPOS", "IMAGE_REGISTRY"} <= keys


def test_every_shipped_template_round_trips_through_the_register(
    tmp_path: Path,
) -> None:
    path = tmp_path / "instances.local.env"
    names = {
        "nuc": "mars",
        "cloud-vm": "terra",
        "standalone": "alpha",
        "remote": "juno",
    }
    blocks = [f"VPATH_INSTANCES={' '.join(names[n] for n in SHIPPED)}"]
    for name in SHIPPED:
        template = templates.load_template(name)
        blocks.append(templates.render_stanza(template, names[name], fill(template)))
    path.write_text("\n".join(blocks), encoding="utf-8")

    loaded = registry.load(path)
    assert set(loaded.names()) == set(names.values())
    for name in SHIPPED:
        assert loaded.get(names[name]).kind == templates.load_template(name).kind


def test_the_shipped_example_register_still_parses() -> None:
    """The file operators copy must stay loadable, and cover every kind."""
    example = Path(__file__).resolve().parents[2] / "instances.example.env"
    loaded = registry.load(example)

    assert {i.kind for i in loaded.instances} == ALL_KINDS


# --- what a template refuses ----------------------------------------------


def test_unknown_template_names_what_is_available() -> None:
    with pytest.raises(TemplateError, match="no type template 'ghost'"):
        templates.load_template("ghost")


def test_unparsable_template_is_rejected(template_dir: Path) -> None:
    (template_dir / "broken.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(TemplateError, match="not readable as JSON"):
        templates.load_template("broken")


def test_non_object_template_is_rejected(template_dir: Path) -> None:
    (template_dir / "listy.json").write_text("[]", encoding="utf-8")
    with pytest.raises(TemplateError, match="must be a JSON object"):
        templates.load_template("listy")


def test_unknown_kind_is_rejected(template_dir: Path) -> None:
    write_template(template_dir, "odd", {"kind": "toaster", "fields": []})
    with pytest.raises(TemplateError, match="not one of"):
        templates.load_template("odd")


def test_template_without_fields_is_rejected(template_dir: Path) -> None:
    write_template(template_dir, "empty", {"kind": "standalone", "fields": []})
    with pytest.raises(TemplateError, match="declares no fields"):
        templates.load_template("empty")


def test_field_without_a_key_is_rejected(template_dir: Path) -> None:
    write_template(template_dir, "nokey", {"kind": "standalone", "fields": [{}]})
    with pytest.raises(TemplateError, match="has no key"):
        templates.load_template("nokey")


def test_non_object_field_is_rejected(template_dir: Path) -> None:
    write_template(template_dir, "flat", {"kind": "standalone", "fields": ["APP_ROOT"]})
    with pytest.raises(TemplateError, match="non-object field"):
        templates.load_template("flat")


def test_unproven_without_a_reason_is_rejected(template_dir: Path) -> None:
    write_template(
        template_dir,
        "vague",
        {"kind": "remote", "proven": False, "fields": [{"key": "CLUSTER_HOST"}]},
    )
    with pytest.raises(TemplateError, match="unproven without a reason"):
        templates.load_template("vague")


def test_kind_claimed_by_two_templates_is_ambiguous(template_dir: Path) -> None:
    for name in ("one", "two"):
        write_template(
            template_dir, name, {"kind": "standalone", "fields": [{"key": "HOME"}]}
        )
    with pytest.raises(TemplateError, match="claimed by several templates"):
        templates.template_for_kind("standalone")


def test_kind_no_template_creates_is_named(template_dir: Path) -> None:
    write_template(
        template_dir, "only", {"kind": "standalone", "fields": [{"key": "X"}]}
    )
    with pytest.raises(TemplateError, match="no type template creates kind 'remote'"):
        templates.template_for_kind("remote")


# --- filling one in --------------------------------------------------------


def test_field_lookup_names_an_unknown_field() -> None:
    template = templates.load_template("nuc")
    assert template.field("SSH_HOST").required is True
    with pytest.raises(TemplateError, match="declares no field 'NOPE'"):
        template.field("NOPE")


def test_suggestion_prefers_default_then_example_then_placeholder() -> None:
    nuc = templates.load_template("nuc")
    assert nuc.field("ENV_PROFILE").suggestion == "nuc"
    assert nuc.field("SSH_HOST").suggestion == "<lan-address-of-the-box>"
    assert templates.TemplateField(key="X", comment="").suggestion == PLACEHOLDER


def test_a_left_in_placeholder_counts_as_missing() -> None:
    template = templates.load_template("standalone")
    values = fill(template)
    values["HOME"] = PLACEHOLDER
    assert templates.missing_required(template, values) == ("HOME",)


def test_validate_rejects_a_blank_mandatory_field() -> None:
    template = templates.load_template("standalone")
    with pytest.raises(TemplateError, match="still needs APP_ROOT, HOME"):
        templates.validate(template, {})


def test_validate_rejects_a_field_the_template_does_not_declare() -> None:
    template = templates.load_template("standalone")
    values = fill(template)
    values["SSH_HOST"] = "10.0.0.9"
    with pytest.raises(TemplateError, match="declares no field\\(s\\): SSH_HOST"):
        templates.validate(template, values)


def test_validate_accepts_a_fully_filled_template() -> None:
    template = templates.load_template("nuc")
    templates.validate(template, fill(template))


# --- what a stanza looks like ---------------------------------------------


def test_stanza_writes_required_fields_and_comments_out_optional_ones() -> None:
    template = templates.load_template("standalone")
    stanza = templates.render_stanza(template, "alpha", fill(template))
    assert "ALPHA_KIND=standalone" in stanza
    assert "ALPHA_APP_ROOT=value-for-app_root" in stanza
    assert "# ALPHA_NOTES=" in stanza
    assert "\nALPHA_NOTES=" not in stanza


def test_stanza_of_an_unproven_template_carries_the_warning(
    template_dir: Path,
) -> None:
    """Nothing shipped is unproven since the survey, so this uses a stand-in.

    The machinery still has to work: the next type declared before it is
    established must carry the warning into the register the operator reads.
    """
    write_template(
        template_dir,
        "hearsay",
        {
            "kind": "remote",
            "proven": False,
            "unproven_reason": "nobody has looked yet",
            "fields": [{"key": "CLUSTER_HOST", "required": True}],
        },
    )
    template = templates.load_template("hearsay")

    stanza = templates.render_stanza(template, "juno", fill(template))

    assert "# UNPROVEN: nobody has looked yet" in stanza
    assert "JUNO_CLUSTER_HOST=value-for-cluster_host" in stanza


def test_stanza_of_the_surveyed_remote_carries_no_warning() -> None:
    stanza = templates.render_stanza(
        templates.load_template("remote"), "juno", {"CLUSTER_HOST": "cluster.example"}
    )

    assert "# UNPROVEN:" not in stanza
    assert "JUNO_CLUSTER_HOST=cluster.example" in stanza
    # The open field is still offered, commented out, so it is visible to fill.
    assert "# JUNO_CONSOLE_PERMITTED=<OPEN" in stanza


def test_stanza_falls_back_to_the_suggestion_for_a_missing_required_field() -> None:
    template = templates.load_template("nuc")
    stanza = templates.render_stanza(template, "mars", {})
    assert "MARS_SSH_HOST=<lan-address-of-the-box>" in stanza
    assert "MARS_ENV_PROFILE=nuc" in stanza
