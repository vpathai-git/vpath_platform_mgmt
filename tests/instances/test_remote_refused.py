"""remote kind loads as declared/unproven; live ops are refused."""

from __future__ import annotations

from pathlib import Path

import pytest

from vpath_platform_mgmt.instances import crud, probe, selector
from vpath_platform_mgmt.instances.registry import Instance, load
from vpath_platform_mgmt.instances.transport import TransportError, require_live_ops


def _remote_register(tmp_path: Path, *, lifecycle: str = "planned") -> Path:
    path = tmp_path / "instances.local.env"
    crud.create(
        path,
        "claas",
        "remote",
        {"NOTES": "win-claas declared unproven"},
        lifecycle=lifecycle,
    )
    return path


def test_remote_loads_from_register(tmp_path: Path) -> None:
    path = _remote_register(tmp_path)
    inst = load(path).get("claas")
    assert inst.kind == "remote"
    assert inst.is_planned


def test_selector_exec_refuses_remote(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    path = _remote_register(tmp_path, lifecycle="live")
    code = selector.main(
        ["--register", str(path), "exec", "claas", "--", "true"],
    )
    assert code == selector.EXIT_UNDETERMINED
    assert "unproven" in capsys.readouterr().err


def test_selector_gradle_refuses_remote_live(tmp_path: Path) -> None:
    path = _remote_register(tmp_path, lifecycle="live")
    code = selector.main(
        ["--register", str(path), "gradle", "claas", "--", "tasks"],
    )
    assert code == selector.EXIT_UNDETERMINED


def test_probe_marks_remote_unproven(tmp_path: Path) -> None:
    path = _remote_register(tmp_path, lifecycle="live")
    inst = load(path).get("claas")

    def _unused_runner(argv: object, timeout: int) -> None:
        raise AssertionError("remote probe must not run commands")

    reading = probe.read_instance(
        inst,
        timeout=1,
        runner=_unused_runner,  # type: ignore[arg-type]
    )
    assert reading.verdict == probe.UNPROVEN


def test_require_live_ops_names_unproven() -> None:
    inst = Instance(name="claas", kind="remote", lifecycle="live", source="t")
    with pytest.raises(TransportError, match="unproven"):
        require_live_ops(inst)
