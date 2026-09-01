"""
Tests for scripts/scan_dependencies.py (unit layer).

These cover ecosystem detection, the resolvability errors, the
.trivyignore.yaml schema (the anti-soft-pass contract), toolchain
verification, and the trivy invocation wiring via a recording fake.
The REAL integration test is the CI scan job running actual trivy
against the actual CVE database — these tests never substitute for it.
"""

import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import scan_dependencies as sd  # noqa: E402


def err_code(excinfo: "pytest.ExceptionInfo[sd.ScanError]") -> int:
    return excinfo.value.code


def test_detect_ecosystem_per_flavor(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    assert sd.detect_ecosystem(tmp_path) == "python"
    (tmp_path / "pyproject.toml").unlink()
    (tmp_path / "build.gradle.kts").write_text("plugins {}\n", encoding="utf-8")
    assert sd.detect_ecosystem(tmp_path) == "java"
    (tmp_path / "build.gradle.kts").unlink()
    (tmp_path / "Cargo.toml").write_text("[package]\n", encoding="utf-8")
    assert sd.detect_ecosystem(tmp_path) == "rust"
    (tmp_path / "Cargo.toml").unlink()
    (tmp_path / "vcpkg.json").write_text("{}\n", encoding="utf-8")
    assert sd.detect_ecosystem(tmp_path) == "cpp"


def test_detect_ecosystem_none_exits_4(tmp_path: Path) -> None:
    with pytest.raises(sd.ScanError) as excinfo:
        sd.detect_ecosystem(tmp_path)
    assert err_code(excinfo) == 4


def test_python_without_lockfile_exits_4(tmp_path: Path) -> None:
    with pytest.raises(sd.ScanError) as excinfo:
        sd.prepare_target("python", tmp_path, tmp_path)
    assert err_code(excinfo) == 4
    assert str(excinfo.value) == (
        f"{tmp_path}: uv.lock missing. Fix: uv lock (and commit it)"
    )


def test_python_exports_frozen_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "project"
    workdir = tmp_path / "scan"
    root.mkdir()
    workdir.mkdir()
    (root / "uv.lock").write_text("version = 1\n", encoding="utf-8")
    recorded: list[str] = []

    def fake_run(
        cmd: list[str], **kwargs: object
    ) -> "subprocess.CompletedProcess[str]":
        recorded.extend(cmd)
        assert kwargs["cwd"] == root
        return subprocess.CompletedProcess(cmd, 0, stdout="example==1.2.3\n")

    monkeypatch.setattr(sd.subprocess, "run", fake_run)
    assert sd.prepare_target("python", root, workdir) == workdir
    assert recorded == [
        "uv",
        "export",
        "--format",
        "requirements-txt",
        "--frozen",
    ]
    assert (workdir / "requirements.txt").read_text(encoding="utf-8") == (
        "example==1.2.3\n"
    )


def test_java_without_lockfile_exits_4(tmp_path: Path) -> None:
    with pytest.raises(sd.ScanError) as excinfo:
        sd.prepare_target("java", tmp_path, tmp_path)
    assert err_code(excinfo) == 4
    assert "--write-locks" in str(excinfo.value)


def ignorefile(tmp_path: Path, body: str) -> None:
    (tmp_path / sd.IGNOREFILE).write_text(body, encoding="utf-8")


def entry(expiry: date, statement: str = "not reachable here") -> str:
    return (
        "vulnerabilities:\n"
        "  - id: CVE-2026-0001\n"
        f'    statement: "{statement}"\n'
        f"    expired_at: {expiry.isoformat()}\n"
    )


def test_ignorefile_valid_passes(tmp_path: Path) -> None:
    ignorefile(tmp_path, entry(date.today() + timedelta(days=30)))
    sd.validate_ignorefile(tmp_path)


def test_ignorefile_missing_statement_exits_2(tmp_path: Path) -> None:
    ignorefile(tmp_path, entry(date.today(), statement=""))
    with pytest.raises(sd.ScanError) as excinfo:
        sd.validate_ignorefile(tmp_path)
    assert err_code(excinfo) == 2


def test_ignorefile_missing_expiry_exits_2(tmp_path: Path) -> None:
    body = 'vulnerabilities:\n  - id: CVE-2026-0001\n    statement: "x"\n'
    ignorefile(tmp_path, body)
    with pytest.raises(sd.ScanError) as excinfo:
        sd.validate_ignorefile(tmp_path)
    assert err_code(excinfo) == 2


def test_ignorefile_expiry_too_far_exits_2(tmp_path: Path) -> None:
    too_far = date.today() + timedelta(days=sd.MAX_EXCEPTION_DAYS + 1)
    ignorefile(tmp_path, entry(too_far))
    with pytest.raises(sd.ScanError) as excinfo:
        sd.validate_ignorefile(tmp_path)
    assert err_code(excinfo) == 2
    assert "90-day" in str(excinfo.value)


def test_plain_trivyignore_rejected_exits_2(tmp_path: Path) -> None:
    (tmp_path / ".trivyignore").write_text("CVE-2026-0001\n", encoding="utf-8")
    with pytest.raises(sd.ScanError) as excinfo:
        sd.validate_ignorefile(tmp_path)
    assert err_code(excinfo) == 2


def test_trivy_missing_exits_3(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PATH", str(tmp_path))
    with pytest.raises(sd.ScanError) as excinfo:
        sd.verify_trivy()
    assert err_code(excinfo) == 3
    assert "brew install trivy" in str(excinfo.value)


def test_run_trivy_wiring(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    recorded: list[str] = []

    def fake_run(cmd: list[str], **kwargs: object) -> "subprocess.CompletedProcess":
        recorded.extend(cmd)
        return subprocess.CompletedProcess(cmd, 1)

    monkeypatch.setattr(sd.subprocess, "run", fake_run)
    ignorefile(tmp_path, entry(date.today() + timedelta(days=10)))
    code = sd.run_trivy("trivy", tmp_path, tmp_path)
    assert code == 1
    assert ["--scanners", "vuln"] == recorded[2:4]
    assert ["--severity", sd.SEVERITIES] == recorded[4:6]
    assert ["--exit-code", "1"] == recorded[6:8]
    assert "--ignorefile" in recorded


def test_findings_print_human_decision_banner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: "pytest.CaptureFixture[str]",
) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    monkeypatch.setattr(sd, "verify_trivy", lambda: "trivy")
    monkeypatch.setattr(sd, "prepare_target", lambda eco, root, wd: root)
    monkeypatch.setattr(sd, "run_trivy", lambda b, r, t: 1)
    assert sd.scan(tmp_path) == 1
    out = capsys.readouterr().out
    assert "HUMAN DECISION REQUIRED" in out
    assert "ACTIVELY confirmed" in out
