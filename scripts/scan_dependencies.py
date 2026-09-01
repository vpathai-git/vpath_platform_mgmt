#!/usr/bin/env python3
"""Scan the RESOLVED dependency set against current CVE data (Trivy).

Universal `make scan` implementation, flavor-aware by manifest detection
(same pattern as .claude/hooks/post_edit_check.py): Python scans the
committed uv.lock export, Java the committed gradle.lockfile, Rust Cargo.lock,
C++ conan/vcpkg manifests. Blocks CRITICAL and HIGH severities, unfixed
included. Exceptions only via .trivyignore.yaml entries carrying a
justification and an expiry date no more than 90 days out.

Exit codes (all non-zero block):
  0 = clean
  1 = CRITICAL/HIGH vulnerabilities found (or trivy scan failure)
  2 = .trivyignore.yaml schema violation
  3 = trivy binary missing
  4 = dependency set not resolvable
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

SEVERITIES = "CRITICAL,HIGH"
IGNOREFILE = ".trivyignore.yaml"
MAX_EXCEPTION_DAYS = 90
INSTALL_HELP = (
    "trivy is required (mandatory CVE gate). Install:\n"
    "  macOS:   brew install trivy\n"
    "  Windows: choco install trivy\n"
    "  Linux:   apt-get install trivy "
    "(or see https://trivy.dev/latest/getting-started/installation/)"
)
FINDINGS_GUIDANCE = """
================ CVE FINDINGS - HUMAN DECISION REQUIRED ================
AGENT INSTRUCTION: explain EACH finding above in plain language
(/plain-summary style, four fields) so a non-engineer can decide:
  What it is        - the vulnerability, one simple sentence
  How it affects us - is the vulnerable code path actually used here?
  What changes      - what an attacker could do to THIS project
  The options       - upgrade/replace/pin the library, or a waiver
A waiver (.trivyignore.yaml entry: id + statement + expired_at,
max {days} days out) is allowed ONLY after a human has read that
explanation and ACTIVELY confirmed accepting the risk. Never add a
waiver autonomously; never treat this gate as passed.
========================================================================="""


class ScanError(Exception):
    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code


def verify_trivy() -> str:
    binary = shutil.which("trivy")
    if not binary:
        raise ScanError(3, INSTALL_HELP)
    return binary


def detect_ecosystem(root: Path) -> str:
    if (root / "pyproject.toml").is_file() or (root / "requirements.txt").is_file():
        return "python"
    if (root / "build.gradle.kts").is_file() or (root / "build.gradle").is_file():
        return "java"
    if (root / "Cargo.toml").is_file():
        return "rust"
    if (root / "vcpkg.json").is_file() or list(root.glob("conanfile.*")):
        return "cpp"
    raise ScanError(4, f"{root}: no recognized dependency manifest found")


def prepare_target(ecosystem: str, root: Path, workdir: Path) -> Path:
    if ecosystem == "python":
        if not (root / "uv.lock").is_file():
            raise ScanError(4, f"{root}: uv.lock missing. Fix: uv lock (and commit it)")
        result = subprocess.run(
            ["uv", "export", "--format", "requirements-txt", "--frozen"],
            cwd=root,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0 or not result.stdout.strip():
            raise ScanError(
                4,
                f"{root}: uv export failed. Fix: uv lock (and commit it)",
            )
        frozen = workdir / "requirements.txt"
        frozen.write_text(result.stdout, encoding="utf-8")
        return workdir
    if ecosystem == "java":
        if not (root / "gradle.lockfile").is_file():
            raise ScanError(
                4,
                f"{root}: gradle.lockfile missing. "
                "Fix: ./gradlew dependencies --write-locks (and commit it)",
            )
        return root
    if ecosystem == "rust":
        if not (root / "Cargo.lock").is_file():
            raise ScanError(
                4, f"{root}: Cargo.lock missing. Fix: cargo generate-lockfile"
            )
        return root
    return root


def parse_ignore_entries(text: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line == "vulnerabilities:":
            continue
        if line.startswith("- "):
            entries.append({})
            line = line[2:]
        if ":" not in line or not entries:
            raise ScanError(2, f"{IGNOREFILE}: unparseable line: {raw!r}")
        key, value = line.split(":", 1)
        entries[-1][key.strip()] = value.strip().strip("\"'")
    return entries


def validate_ignorefile(root: Path) -> None:
    if (root / ".trivyignore").is_file():
        raise ScanError(
            2,
            ".trivyignore (plain format) is not allowed - exceptions need "
            f"a justification and expiry; use {IGNOREFILE}",
        )
    path = root / IGNOREFILE
    if not path.is_file():
        return
    horizon = date.today() + timedelta(days=MAX_EXCEPTION_DAYS)
    for entry in parse_ignore_entries(path.read_text(encoding="utf-8")):
        label = entry.get("id", "<missing id>")
        if not entry.get("id"):
            raise ScanError(2, f"{IGNOREFILE}: entry without 'id'")
        if not entry.get("statement"):
            raise ScanError(2, f"{IGNOREFILE}: {label}: 'statement' missing or empty")
        try:
            expiry = date.fromisoformat(entry.get("expired_at", ""))
        except ValueError:
            raise ScanError(
                2, f"{IGNOREFILE}: {label}: 'expired_at' missing or not an ISO date"
            ) from None
        if expiry > horizon:
            raise ScanError(
                2,
                f"{IGNOREFILE}: {label}: expiry {expiry.isoformat()} exceeds "
                f"the {MAX_EXCEPTION_DAYS}-day maximum",
            )


def run_trivy(binary: str, root: Path, target: Path) -> int:
    cmd = [
        binary,
        "fs",
        "--scanners",
        "vuln",
        "--severity",
        SEVERITIES,
        "--exit-code",
        "1",
    ]
    ignorefile = root / IGNOREFILE
    if ignorefile.is_file():
        cmd += ["--ignorefile", str(ignorefile)]
    cmd.append(str(target))
    return subprocess.run(cmd).returncode


def scan(root: Path) -> int:
    binary = verify_trivy()
    ecosystem = detect_ecosystem(root)
    validate_ignorefile(root)
    with tempfile.TemporaryDirectory() as tmp:
        target = prepare_target(ecosystem, root, Path(tmp))
        print(
            f"scan: ecosystem={ecosystem}, blocking severities: {SEVERITIES}",
            flush=True,
        )
        code = run_trivy(binary, root, target)
    if code == 0:
        print("scan: dependency set clean")
    elif code == 1:
        print(FINDINGS_GUIDANCE.format(days=MAX_EXCEPTION_DAYS))
    return code


def main() -> int:
    parser = argparse.ArgumentParser(description="Mandatory dependency CVE gate.")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="project root (default: this repo)",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="only verify the trivy toolchain is present",
    )
    args = parser.parse_args()
    try:
        if args.verify_only:
            verify_trivy()
            print("scan: trivy toolchain present")
            return 0
        return scan(args.root)
    except ScanError as exc:
        print(f"scan: {exc}", file=sys.stderr)
        return exc.code


if __name__ == "__main__":
    sys.exit(main())
