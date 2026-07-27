"""The register: what it accepts, and -- with equal care -- what it refuses.

Every acceptance test below has a refusal test beside it (the "red drill"):
proof that the check can actually fail.  A validation nobody has watched go red
is documentation, not a gate.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from vpath_platform_mgmt.instances import registry
from vpath_platform_mgmt.instances.registry import RegistryError, load, parse_lines

# --- reading a well-formed register ---------------------------------------


def test_declaration_order_is_preserved(register: Path) -> None:
    assert load(register).names() == ("boxone", "boxtwo", "standalone1", "later")


def test_server_instance_resolves_its_coordinates(register: Path) -> None:
    box = load(register).get("boxone")
    assert box.kind == registry.KIND_SERVER_NUC
    assert box.is_server and not box.is_standalone
    assert box.ssh_target == "boxuser@10.0.0.1"
    assert box.env_profile == "nuc"
    assert box.checkout == "/workspace"
    assert box.notes == "first box"


def test_standalone_instance_resolves_its_paths(
    register: Path, app_root: Path, standalone_home: Path
) -> None:
    app = load(register).get("standalone1")
    assert app.is_standalone and not app.is_server
    assert app.app_root == str(app_root)
    assert app.home == str(standalone_home)


def test_planned_instance_needs_no_coordinates(register: Path) -> None:
    later = load(register).get("later")
    assert later.is_planned
    assert later.app_root == ""


def test_path_fields_expand_home(tmp_path: Path) -> None:
    values = parse_lines(["BOX_CHECKOUT=$HOME/somewhere"], "t")
    assert registry.expand(values["BOX_CHECKOUT"]).startswith(str(Path.home()))


def test_a_quoted_value_keeps_its_content(tmp_path: Path) -> None:
    assert parse_lines(['BOX_NOTES="a note"'], "t")["BOX_NOTES"] == "a note"


# --- red drills: each check proves it can fail ----------------------------


def test_missing_register_names_the_template(tmp_path: Path) -> None:
    with pytest.raises(RegistryError, match="instances.example.env"):
        load(tmp_path / "nope.env")


def test_unknown_instance_lists_what_is_declared(register: Path) -> None:
    with pytest.raises(RegistryError, match="unknown instance 'mars'"):
        load(register).get("mars")


def test_a_line_that_is_not_an_assignment_is_refused() -> None:
    with pytest.raises(RegistryError, match="not a KEY=VALUE line"):
        parse_lines(["BOX_KIND server-nuc"], "t")


def test_an_inline_comment_is_part_of_the_value() -> None:
    # Documented behaviour, and the reason the template forbids inline
    # comments: the parser must not have to guess where a value ends.
    assert parse_lines(["BOX_SSH_HOST=1.2.3.4  # the box"], "t")["BOX_SSH_HOST"] == (
        "1.2.3.4  # the box"
    )


def test_a_key_declared_twice_is_refused() -> None:
    with pytest.raises(RegistryError, match="declared twice"):
        parse_lines(["BOX_KIND=server-nuc", "BOX_KIND=standalone"], "t")


def test_empty_instance_list_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "r.env"
    path.write_text("VPATH_INSTANCES=\n", encoding="utf-8")
    with pytest.raises(RegistryError, match="nothing declared"):
        load(path)


def test_unknown_kind_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "r.env"
    path.write_text("VPATH_INSTANCES=box\nBOX_KIND=laptop\n", encoding="utf-8")
    with pytest.raises(RegistryError, match="BOX_KIND is 'laptop'"):
        load(path)


def test_unknown_lifecycle_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "r.env"
    path.write_text(
        "VPATH_INSTANCES=box\nBOX_KIND=standalone\nBOX_LIFECYCLE=maybe\n",
        encoding="utf-8",
    )
    with pytest.raises(RegistryError, match="BOX_LIFECYCLE is 'maybe'"):
        load(path)


def test_a_live_server_without_a_checkout_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "r.env"
    path.write_text(
        "VPATH_INSTANCES=box\n"
        "BOX_KIND=server-nuc\n"
        "BOX_SSH_HOST=1.2.3.4\n"
        "BOX_SSH_USER=u\n"
        "BOX_ENV_PROFILE=nuc\n",
        encoding="utf-8",
    )
    with pytest.raises(RegistryError, match="BOX_CHECKOUT"):
        load(path)


def test_a_live_standalone_without_a_home_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "r.env"
    path.write_text(
        "VPATH_INSTANCES=box\nBOX_KIND=standalone\nBOX_APP_ROOT=/tmp\n",
        encoding="utf-8",
    )
    with pytest.raises(RegistryError, match="BOX_HOME"):
        load(path)


def test_an_instance_declared_twice_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "r.env"
    path.write_text(
        "VPATH_INSTANCES=box box\nBOX_KIND=standalone\n"
        "BOX_APP_ROOT=/tmp\nBOX_HOME=/tmp\n",
        encoding="utf-8",
    )
    with pytest.raises(RegistryError, match="declared twice"):
        load(path)


def test_an_upper_case_instance_name_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "r.env"
    path.write_text("VPATH_INSTANCES=Box\n", encoding="utf-8")
    with pytest.raises(RegistryError, match="must be lower-case"):
        load(path)


def test_the_register_location_follows_the_env_var(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(registry.REGISTER_ENV_VAR, str(tmp_path / "elsewhere.env"))
    assert registry.default_register_path().name == "elsewhere.env"


def test_the_register_location_defaults_next_to_the_repo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(registry.REGISTER_ENV_VAR, raising=False)
    assert registry.default_register_path().name == registry.DEFAULT_REGISTER_NAME
