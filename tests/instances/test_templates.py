"""Kind templates: required fields and ops posture come from versioned YAML."""

from __future__ import annotations

import pytest

from vpath_platform_mgmt.instances import templates
from vpath_platform_mgmt.instances.templates import TemplateError, load_template


def test_server_nuc_template_requires_ssh_and_checkout() -> None:
    tpl = load_template("server-nuc")
    assert tpl.kind == "server-nuc"
    assert tpl.ops == "live"
    assert "SSH_HOST" in tpl.required
    assert "CHECKOUT" in tpl.required


def test_standalone_template_requires_app_root_and_home() -> None:
    tpl = load_template("standalone")
    assert set(tpl.required) == {"APP_ROOT", "HOME"}
    assert tpl.ops == "live"


def test_server_cloud_vm_template_is_live() -> None:
    tpl = load_template("server-cloud-vm")
    assert tpl.ops == "live"
    assert "ENV_PROFILE" in tpl.required


def test_remote_template_is_unproven() -> None:
    tpl = load_template("remote")
    assert tpl.ops == "unproven"


def test_unknown_kind_is_refused() -> None:
    with pytest.raises(TemplateError, match="unknown kind"):
        load_template("not-a-kind")


def test_all_kinds_are_covered() -> None:
    from vpath_platform_mgmt.instances import registry

    assert set(templates.kinds()) == {
        "server-nuc",
        "server-cloud-vm",
        "standalone",
        "remote",
    }
    assert set(registry.ALL_KINDS) == set(templates.kinds())
