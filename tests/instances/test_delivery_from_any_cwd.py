"""Delivery is aimed by the register, not by the shell it is started in.

The defect this file guards (stream 220, field-found in
``REPORT-s218-mars12-retest.md:442-446``): ``deliver`` built a ``git push``
without naming a repository, so git resolved the commit against the process
working directory.  Following the runbook -- ``cd .../vpath_platform_mgmt && …
selector deliver …`` -- therefore died with ``fatal: bad object <sha>`` and
``remote unpack failed``, while the identical command from a shell that had
already ``cd``-ed into the server checkout delivered fine.

What is real here and what is not
---------------------------------
Real: git, the objects, the pack transfer, the receiving repository, the
fast-forward, and the selector itself driving its own transport.  Substituted:
the network hop.  ``ssh`` is a POSIX stand-in on ``PATH`` that runs the remote
command locally, so the "box" is a throwaway clone in ``tmp_path`` -- no box,
no remote, nothing outside the test's own directory is touched.  The assertion
is positive: the commit must actually arrive at the box's ``HEAD``.

Two of the three tests are the drill's calibration, not decoration: one proves
the foreign directory genuinely cannot resolve the commit (otherwise the green
run would be vacuous), the other proves the run is identical from the server
checkout and from a foreign directory.  POSIX only -- the stand-in is a shell
script.
"""

from __future__ import annotations

import os
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

from vpath_platform_mgmt.instances import selector, transport
from vpath_platform_mgmt.instances.registry import load

# Fixed identity and dates: two rigs built from the same steps then carry the
# same commit shas, which is what makes the two runs comparable byte for byte.
GIT_ENV = {
    "GIT_AUTHOR_NAME": "drill",
    "GIT_AUTHOR_EMAIL": "drill@example.invalid",
    "GIT_COMMITTER_NAME": "drill",
    "GIT_COMMITTER_EMAIL": "drill@example.invalid",
    "GIT_AUTHOR_DATE": "2026-01-01T00:00:00+00:00",
    "GIT_COMMITTER_DATE": "2026-01-01T00:00:00+00:00",
}

SSH_STAND_IN = """\
#!/bin/sh
# Stands in for the network hop only: drop the ssh options and the target,
# then run the command the caller wanted to run on the box -- here, locally.
while [ $# -gt 0 ]; do
  case "$1" in
    -o|-i) shift 2 ;;
    -*) shift ;;
    *) break ;;
  esac
done
shift
exec /bin/sh -c "$*"
"""

REGISTER = """\
VPATH_INSTANCES=drill
DRILL_KIND=server-nuc
DRILL_SSH_HOST=drill.invalid
DRILL_SSH_USER=op
DRILL_SSH_KEY={key}
DRILL_ENV_PROFILE=nuc
DRILL_CHECKOUT={box}
DRILL_SOURCE_CHECKOUT={source}
"""


@dataclass(frozen=True)
class Rig:
    """One throwaway delivery: a source checkout, a box, and a register."""

    root: Path
    source: Path
    box: Path
    register: Path
    bin: Path
    sha: str

    @property
    def box_head(self) -> str:
        return git(self.box, "rev-parse", "HEAD")


@pytest.fixture(autouse=True)
def hermetic_git(monkeypatch: pytest.MonkeyPatch) -> None:
    """No ``GIT_*`` from the surrounding process reaches this rig.

    Not a nicety: a git hook exports ``GIT_DIR`` and ``GIT_INDEX_FILE`` into
    everything it runs, so under the project's own pre-commit gate every
    ``git`` call here would have operated on the repository under test instead
    of on ``tmp_path`` -- and did, until this fixture existed.  ``deliver``
    itself inherits the same environment, which is why the sweep covers the
    selector's own run and not only the setup (``GIT_SSH_COMMAND`` among them,
    which the transport refuses to be overridden by).
    """
    for name in list(os.environ):
        if name.startswith("GIT_"):
            monkeypatch.delenv(name, raising=False)
    for name, value in GIT_ENV.items():
        monkeypatch.setenv(name, value)


def git(cwd: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    return done.stdout.strip()


def build_rig(root: Path) -> Rig:
    """A source checkout one commit ahead of a box that clones it."""
    root.mkdir(parents=True)
    source, box, binaries = root / "source", root / "box", root / "bin"
    binaries.mkdir()

    subprocess.run(["git", "init", "-q", "-b", "main", str(source)], check=True)
    git(source, "commit", "-q", "--allow-empty", "-m", "base")
    subprocess.run(["git", "clone", "-q", str(source), str(box)], check=True)
    git(source, "commit", "-q", "--allow-empty", "-m", "target")

    stand_in = binaries / "ssh"
    stand_in.write_text(SSH_STAND_IN, encoding="utf-8")
    stand_in.chmod(0o755)

    key = root / "key"
    key.write_text("", encoding="utf-8")  # require_ssh only checks it is there

    register = root / "instances.local.env"
    register.write_text(
        REGISTER.format(key=key, box=box, source=source), encoding="utf-8"
    )
    return Rig(
        root=root,
        source=source,
        box=box,
        register=register,
        bin=binaries,
        sha=git(source, "rev-parse", "HEAD"),
    )


@pytest.fixture()
def foreign_cwd(tmp_path: Path, hermetic_git: None) -> Path:
    """A directory that is a git repository *without* the delivered commit.

    The field case exactly: the management checkout the runbook line stands in.
    """
    elsewhere = tmp_path / "management_checkout"
    elsewhere.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main", str(elsewhere)], check=True)
    git(elsewhere, "commit", "-q", "--allow-empty", "-m", "unrelated")
    return elsewhere


def deliver_from(rig: Rig, cwd: Path, monkeypatch: pytest.MonkeyPatch) -> int:
    monkeypatch.setenv("PATH", f"{rig.bin}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.chdir(cwd)
    return selector.main(
        ["--register", str(rig.register), "deliver", "drill", "--sha", rig.sha]
    )


def test_the_commit_arrives_when_the_delivery_is_started_anywhere_else(
    tmp_path: Path, foreign_cwd: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rig = build_rig(tmp_path / "rig")
    before = rig.box_head

    code = deliver_from(rig, foreign_cwd, monkeypatch)

    assert code == selector.EXIT_OK
    assert before != rig.sha, "the box would have carried the commit anyway"
    assert rig.box_head == rig.sha, "the box did not receive the commit"


def test_that_foreign_directory_really_cannot_resolve_the_commit(
    tmp_path: Path, foreign_cwd: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Calibration: the drill above must not be able to pass by accident.

    The same push *without* the register's source repository -- the form that
    shipped before stream 220 -- run from the same directory, with the same
    stand-in transport.  If this ever stops failing, the green run above proves
    nothing and this file is broken, not the code.
    """
    rig = build_rig(tmp_path / "rig")
    monkeypatch.setenv("PATH", f"{rig.bin}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.chdir(foreign_cwd)

    instance = load(rig.register).get("drill")
    cwd_relative_push = (
        f"git -c core.sshCommand={shlex.quote(transport.git_ssh_command(instance))} "
        f"push --no-verify "
        f"{shlex.quote(instance.ssh_target + ':' + instance.checkout)} "
        f"{shlex.quote(rig.sha)}:refs/heads/delivery"
    )
    result = transport.run(shlex.split(cwd_relative_push))

    assert not result.ok
    assert f"bad object {rig.sha}" in result.stderr, result.stderr
    assert rig.box_head != rig.sha, "the box received a commit it could not have"


def test_the_delivery_is_identical_from_the_server_checkout_and_from_elsewhere(
    tmp_path: Path,
    foreign_cwd: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Same commit, same output, same resulting box -- wherever it was typed.

    Two rigs are built from the same steps, so they carry the same shas; the
    only difference between the two runs is the directory they were started in
    and the rig's own path, which is normalised away before comparing.
    """
    home = build_rig(tmp_path / "from_the_checkout")
    away = build_rig(tmp_path / "from_elsewhere")
    assert home.sha == away.sha

    assert deliver_from(home, home.source, monkeypatch) == selector.EXIT_OK
    from_the_checkout = capsys.readouterr()
    assert deliver_from(away, foreign_cwd, monkeypatch) == selector.EXIT_OK
    from_elsewhere = capsys.readouterr()

    def normalised(text: str, rig: Rig) -> str:
        return text.replace(str(rig.root), "<rig>")

    assert normalised(from_elsewhere.out, away) == normalised(
        from_the_checkout.out, home
    )
    assert normalised(from_elsewhere.err, away) == normalised(
        from_the_checkout.err, home
    )
    assert away.box_head == home.box_head == home.sha
