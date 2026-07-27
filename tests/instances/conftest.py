"""Shared fixtures: a register on disk and a runner that starts no process.

The fake runner is deliberately *not* a stand-in for a box.  It exists so the
judging logic can be driven into every branch -- including the branches a real
fleet almost never shows, like a silent platform or a torn checkout.  The proof
that the tooling works against real instances is a live run against the fleet,
recorded in the stream's report; that is a different kind of evidence and
neither replaces the other.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Sequence

import pytest

from vpath_platform_mgmt.instances.transport import CommandResult

REGISTER = """\
# a register, as an operator would write it
VPATH_INSTANCES=boxone boxtwo standalone1 later

BOXONE_KIND=server-nuc
BOXONE_SSH_HOST=10.0.0.1
BOXONE_SSH_USER=boxuser
BOXONE_SSH_KEY=__KEY__
BOXONE_SSH_ALIAS=boxone
BOXONE_ENV_PROFILE=nuc
BOXONE_CHECKOUT=/workspace
BOXONE_NOTES=first box

BOXTWO_KIND=server-cloud-vm
BOXTWO_SSH_HOST=203.0.113.7
BOXTWO_SSH_USER=cloud
BOXTWO_SSH_KEY_SOURCE=bundle.zip::key.pem
BOXTWO_ENV_PROFILE=vm5
BOXTWO_CHECKOUT=/workspace

STANDALONE1_KIND=standalone
STANDALONE1_APP_ROOT=__APP_ROOT__
STANDALONE1_HOME=__HOME__

LATER_KIND=standalone
LATER_LIFECYCLE=planned
"""

PAYLOAD_HEALTHY = """\
checkout_sha=1a2c51dc78910a4c2fc9d8c93ab5492c6a8d3c54
checkout_branch=main
envfile=/workspace/config/dot_env/.env.nuc
target_dir=infra_build_nuc
vpath_port=30600
marker=/workspace/infra_build_nuc/phase-gates/platformReady.marker
marker_mtime=2026-07-26T04:52:25Z
api_url=https://127.0.0.1:30600/api/version
api_body={"version":"2.0.0","build_id":"1a2c51dc78910a4c2fc9d8c93ab5492c6a8d3c54"}
deployments=53/53
image=vpath-web:1.0
image_sha=1a2c51dc78910a4c2fc9d8c93ab5492c6a8d3c54-dirty
"""


@pytest.fixture()
def app_root(tmp_path: Path) -> Path:
    root = tmp_path / "app"
    (root / "kit").mkdir(parents=True)
    (root / "kit" / "VERSION").write_text(
        "# Vendored VPATH substrate\n"
        "source_sha: 09ede4b209e49cda6c318663ac552ba84e277437\n",
        encoding="utf-8",
    )
    return root


@pytest.fixture()
def standalone_home(tmp_path: Path) -> Path:
    home = tmp_path / "home"
    (home / "runtime").mkdir(parents=True)
    (home / "runtime" / "state.db").write_bytes(b"x")
    return home


@pytest.fixture()
def ssh_key(tmp_path: Path) -> Path:
    key = tmp_path / "testkey"
    key.write_text("not a real key\n", encoding="utf-8")
    return key


@pytest.fixture()
def register(
    tmp_path: Path, app_root: Path, standalone_home: Path, ssh_key: Path
) -> Path:
    path = tmp_path / "instances.local.env"
    path.write_text(
        REGISTER.replace("__APP_ROOT__", str(app_root))
        .replace("__HOME__", str(standalone_home))
        .replace("__KEY__", str(ssh_key)),
        encoding="utf-8",
    )
    return path


FakeRunner = Callable[[Sequence[str], int], CommandResult]


def runner_returning(stdout: str, returncode: int = 0, stderr: str = "") -> FakeRunner:
    """A runner that answers every command the same way."""

    def run(argv: Sequence[str], timeout: int) -> CommandResult:
        return CommandResult(
            argv=tuple(argv), returncode=returncode, stdout=stdout, stderr=stderr
        )

    return run


def recording_runner(stdout: str = "") -> tuple[FakeRunner, list[tuple[str, ...]]]:
    """A runner that records what it was asked to run."""
    seen: list[tuple[str, ...]] = []

    def run(argv: Sequence[str], timeout: int) -> CommandResult:
        seen.append(tuple(argv))
        return CommandResult(argv=tuple(argv), returncode=0, stdout=stdout, stderr="")

    return run, seen
