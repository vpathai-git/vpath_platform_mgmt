"""Writing the register: what lands, what is refused, and what is put back.

The rule these tests hold to is that a refused edit leaves *no trace*.  A
half-written register is worse than one that declined the change, because the
next command reads it as if the operator meant it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from vpath_platform_mgmt.instances import crud, registry
from vpath_platform_mgmt.instances.registry import RegistryError
from vpath_platform_mgmt.instances.templates import TemplateError

NUC_VALUES = {
    "SSH_HOST": "10.0.0.5",
    "SSH_USER": "boxuser",
    "ENV_PROFILE": "nuc",
    "CHECKOUT": "/workspace",
}


@pytest.fixture()
def fresh(tmp_path: Path) -> Path:
    """A register path that does not exist yet."""
    return tmp_path / "instances.local.env"


# --- create ----------------------------------------------------------------


def test_create_bootstraps_a_register_that_did_not_exist(fresh: Path) -> None:
    template = crud.create(fresh, "mars", "nuc", dict(NUC_VALUES))

    assert template.name == "nuc"
    loaded = registry.load(fresh)
    assert loaded.names() == ("mars",)
    assert loaded.get("mars").ssh_host == "10.0.0.5"
    assert loaded.get("mars").kind == "server-nuc"


def test_create_appends_to_an_existing_register(register: Path) -> None:
    before = registry.load(register).names()

    crud.create(register, "mars", "nuc", dict(NUC_VALUES))

    assert registry.load(register).names() == before + ("mars",)


def test_create_keeps_the_comments_the_operator_wrote(register: Path) -> None:
    crud.create(register, "mars", "nuc", dict(NUC_VALUES))

    assert "# a register, as an operator would write it" in register.read_text(
        encoding="utf-8"
    )


def test_create_records_the_template_it_came_from(fresh: Path) -> None:
    crud.create(fresh, "mars", "nuc", dict(NUC_VALUES))

    assert "from template nuc v1" in fresh.read_text(encoding="utf-8")


def test_create_refuses_a_missing_mandatory_field(fresh: Path) -> None:
    with pytest.raises(TemplateError, match="still needs CHECKOUT"):
        crud.create(
            fresh,
            "mars",
            "nuc",
            {k: v for k, v in NUC_VALUES.items() if k != "CHECKOUT"},
        )

    assert not fresh.exists()


def test_create_refuses_a_field_the_template_does_not_declare(fresh: Path) -> None:
    values = dict(NUC_VALUES) | {"APP_ROOT": "/somewhere"}
    with pytest.raises(TemplateError, match="declares no field"):
        crud.create(fresh, "mars", "nuc", values)

    assert not fresh.exists()


def test_create_refuses_a_name_already_declared(register: Path) -> None:
    with pytest.raises(RegistryError, match="already declared"):
        crud.create(register, "boxone", "nuc", dict(NUC_VALUES))


def test_create_refuses_a_name_the_register_could_not_hold(fresh: Path) -> None:
    with pytest.raises(RegistryError, match="must be lower-case alphanumeric"):
        crud.create(fresh, "Mars-1", "nuc", dict(NUC_VALUES))

    assert not fresh.exists()


def test_create_refuses_an_unknown_template(fresh: Path) -> None:
    with pytest.raises(TemplateError, match="no type template 'ghost'"):
        crud.create(fresh, "mars", "ghost", {})


def test_a_rejected_bootstrap_leaves_no_file_behind(fresh: Path) -> None:
    """The stanza parses as KEY=VALUE but the register refuses the value."""
    values = dict(NUC_VALUES) | {"LIFECYCLE": "someday"}
    with pytest.raises(RegistryError, match="edit rejected"):
        crud.create(fresh, "mars", "nuc", values)

    assert not fresh.exists()


def test_a_rejected_edit_restores_the_previous_register(register: Path) -> None:
    before = register.read_text(encoding="utf-8")
    values = dict(NUC_VALUES) | {"LIFECYCLE": "someday"}

    with pytest.raises(RegistryError, match="edit rejected"):
        crud.create(register, "mars", "nuc", values)

    assert register.read_text(encoding="utf-8") == before


def test_a_remote_instance_creates_from_the_surveyed_template(fresh: Path) -> None:
    """Since the survey the remote type is evidenced, so no warning banner."""
    template = crud.create(fresh, "juno", "remote", {"CLUSTER_HOST": "cluster.example"})

    assert template.proven is True
    assert registry.load(fresh).get("juno").is_remote
    written = fresh.read_text(encoding="utf-8")
    assert "# UNPROVEN:" not in written
    # The question the survey could not close is still visible to be answered.
    assert "JUNO_CONSOLE_PERMITTED" in written


# --- update ----------------------------------------------------------------


def test_update_sets_an_existing_field(register: Path) -> None:
    crud.update(register, "boxone", {"SSH_HOST": "10.0.0.99"})

    assert registry.load(register).get("boxone").ssh_host == "10.0.0.99"


def test_update_adds_a_field_that_was_not_there(register: Path) -> None:
    crud.update(register, "boxone", {"LOCATION": "rack 2 / /workspace"})

    assert registry.load(register).get("boxone").location == "rack 2 / /workspace"


def test_update_with_an_empty_value_retracts_the_field(register: Path) -> None:
    crud.update(register, "boxone", {"NOTES": ""})

    assert registry.load(register).get("boxone").notes == ""
    assert "BOXONE_NOTES" not in register.read_text(encoding="utf-8")


def test_update_may_not_retract_a_mandatory_field(register: Path) -> None:
    before = register.read_text(encoding="utf-8")

    with pytest.raises(RegistryError, match="edit rejected"):
        crud.update(register, "boxone", {"CHECKOUT": ""})

    assert register.read_text(encoding="utf-8") == before


def test_update_refuses_a_field_the_template_does_not_declare(register: Path) -> None:
    with pytest.raises(RegistryError, match="declares no field"):
        crud.update(register, "boxone", {"APP_ROOT": "/nope"})


def test_update_refuses_an_unknown_instance(register: Path) -> None:
    with pytest.raises(RegistryError, match="is not declared"):
        crud.update(register, "ghost", {"NOTES": "x"})


def test_update_refuses_to_change_nothing(register: Path) -> None:
    with pytest.raises(RegistryError, match="changes nothing"):
        crud.update(register, "boxone", {})


def test_update_refuses_a_register_that_does_not_exist(fresh: Path) -> None:
    with pytest.raises(RegistryError, match="no instance register"):
        crud.update(fresh, "boxone", {"NOTES": "x"})


def test_update_leaves_the_other_instances_alone(register: Path) -> None:
    before = registry.load(register).get("boxtwo")

    crud.update(register, "boxone", {"SSH_HOST": "10.0.0.99"})

    assert registry.load(register).get("boxtwo").fields == before.fields


# --- remove ----------------------------------------------------------------


def test_remove_drops_the_declaration_and_the_fields(register: Path) -> None:
    crud.remove(register, "boxone")

    loaded = registry.load(register)
    assert "boxone" not in loaded.names()
    assert "BOXONE_" not in register.read_text(encoding="utf-8")


def test_remove_takes_its_own_stanza_header_with_it(fresh: Path) -> None:
    crud.create(fresh, "mars", "nuc", dict(NUC_VALUES))
    crud.create(fresh, "venus", "nuc", dict(NUC_VALUES))

    crud.remove(fresh, "mars")

    assert "# --- mars (" not in fresh.read_text(encoding="utf-8")
    assert "# --- venus (" in fresh.read_text(encoding="utf-8")


def test_remove_refuses_the_last_instance(fresh: Path) -> None:
    crud.create(fresh, "mars", "nuc", dict(NUC_VALUES))

    with pytest.raises(RegistryError, match="only declared instance"):
        crud.remove(fresh, "mars")

    assert registry.load(fresh).names() == ("mars",)


def test_remove_refuses_an_unknown_instance(register: Path) -> None:
    with pytest.raises(RegistryError, match="is not declared"):
        crud.remove(register, "ghost")


def test_remove_refuses_a_register_that_does_not_exist(fresh: Path) -> None:
    with pytest.raises(RegistryError, match="no instance register"):
        crud.remove(fresh, "boxone")
