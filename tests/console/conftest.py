"""A register carrying one instance of every type the console must render.

The console's whole claim is that it shows *all* platform types through one
shape, so its fixture has to contain all of them -- including the remote type
that cannot be probed and the planned one that does not exist yet.  A fixture
with only the easy kinds would prove the easy half.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import pytest

from vpath_platform_mgmt.instances.transport import CommandResult

REGISTER = """\
# every type the console must render
VPATH_INSTANCES=mercury8 terra alpha juno bravo

MERCURY8_KIND=server-nuc
MERCURY8_SSH_HOST=10.0.0.1
MERCURY8_SSH_USER=boxuser
MERCURY8_ENV_PROFILE=nuc
MERCURY8_CHECKOUT=/workspace
MERCURY8_LOCATION=lab rack 2 / /workspace
MERCURY8_ONTOGATE_VIEW=http://127.0.0.1:8731
MERCURY8_NOTES=first NUC

TERRA_KIND=server-cloud-vm
TERRA_SSH_HOST=203.0.113.7
TERRA_SSH_USER=cloud
TERRA_ENV_PROFILE=vm5
TERRA_CHECKOUT=/workspace

ALPHA_KIND=standalone
ALPHA_APP_ROOT=__APP_ROOT__
ALPHA_HOME=__HOME__

JUNO_KIND=remote
JUNO_CLUSTER_HOST=dehwllvpath01.example.local

BRAVO_KIND=standalone
BRAVO_LIFECYCLE=planned
"""


@pytest.fixture()
def console_register(tmp_path: Path) -> Path:
    path = tmp_path / "instances.local.env"
    path.write_text(
        REGISTER.replace("__APP_ROOT__", str(tmp_path / "app")).replace(
            "__HOME__", str(tmp_path / "home")
        ),
        encoding="utf-8",
    )
    return path


@pytest.fixture()
def silent_runner() -> object:
    """A runner that answers nothing -- every probe becomes a named gap."""

    def run(argv: Sequence[str], timeout: int) -> CommandResult:
        return CommandResult(argv=tuple(argv), returncode=1, stdout="", stderr="no")

    return run
