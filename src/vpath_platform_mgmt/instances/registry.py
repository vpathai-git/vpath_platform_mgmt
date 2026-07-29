"""The instance register -- which environments exist and how to reach them.

What this module is
-------------------
The VPATH platform runs on several instances of two classes: *server*
environments (a k3s box -- NUC or cloud VM -- carrying the full platform) and
*standalone* environments (a local Electron shell embedding the platform).
Every operator has a different set of them, with their own addresses, users and
key paths.  None of that may be committed.

So the repository carries the *schema*, the *template* and the *mechanism*; the
operator carries the *values* in a gitignored file.  This module reads that file
and hands out validated instances.

The boundary this module defends
--------------------------------
The register says **where** an environment is and **from where** it is driven.
It never says **how** the platform is installed, built or deployed -- that is
the server project's pipeline and stays there.  Concretely: the register names
the env profile (``config/dot_env/.env.<profile>`` in the server checkout) but
never copies a value out of it.  Ports, workspace paths and target directories
are read from that profile at the moment they are needed, so there is exactly
one place where each of them is declared.

File format
-----------
``KEY=VALUE`` lines, ``#`` starts a comment **only at the beginning of a line**
-- the same posture as the server's ``config/dot_env`` profiles, which are
guarded against inline comments for the same reason: otherwise a ``#`` inside a
value is ambiguous.  ``~`` and ``$HOME`` are expanded in path-valued fields.

Every instance is declared once in ``VPATH_INSTANCES`` (whitespace-separated)
and described by fields prefixed with its upper-cased name.

There is no default register and no fallback instance.  A missing file, an
unknown name or a missing required field raises -- silently guessing which box
to talk to is the most expensive mistake this tooling can make.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

# --- the two classes of environment ---------------------------------------

KIND_SERVER_NUC = "server-nuc"
KIND_SERVER_CLOUD_VM = "server-cloud-vm"
KIND_STANDALONE = "standalone"

SERVER_KINDS = frozenset({KIND_SERVER_NUC, KIND_SERVER_CLOUD_VM})
ALL_KINDS = frozenset(SERVER_KINDS | {KIND_STANDALONE})

# `live` = expected to exist now.  `planned` = named, agreed, not built yet;
# probing it is expected to find nothing, and finding something is a drift.
LIFECYCLE_LIVE = "live"
LIFECYCLE_PLANNED = "planned"
ALL_LIFECYCLES = frozenset({LIFECYCLE_LIVE, LIFECYCLE_PLANNED})

# Fields required per kind.  A `planned` instance is exempt: its coordinates
# are not knowable before it exists.
REQUIRED_SERVER_FIELDS = ("SSH_HOST", "SSH_USER", "ENV_PROFILE", "CHECKOUT")
REQUIRED_STANDALONE_FIELDS = ("APP_ROOT", "HOME")

PATH_FIELDS = frozenset({"SSH_KEY", "CHECKOUT", "APP_ROOT", "HOME"})

DEFAULT_REGISTER_NAME = "instances.local.env"
REGISTER_ENV_VAR = "VPATH_INSTANCES_FILE"
TEMPLATE_NAME = "instances.example.env"

NAME_RE = re.compile(r"^[a-z][a-z0-9]*$")
_LINE_RE = re.compile(r"^(?P<key>[A-Za-z_][A-Za-z0-9_]*)=(?P<value>.*)$")


class RegistryError(Exception):
    """The register could not be read, or does not say what it must say.

    Always carries the file it is talking about, so the operator knows which
    file to open.
    """


@dataclass(frozen=True)
class Instance:
    """One environment, as the register declares it."""

    name: str
    kind: str
    lifecycle: str
    fields: Mapping[str, str] = field(default_factory=dict)
    source: str = ""

    # -- generic ------------------------------------------------------------

    @property
    def is_server(self) -> bool:
        return self.kind in SERVER_KINDS

    @property
    def is_standalone(self) -> bool:
        return self.kind == KIND_STANDALONE

    @property
    def is_planned(self) -> bool:
        return self.lifecycle == LIFECYCLE_PLANNED

    @property
    def notes(self) -> str:
        return self.fields.get("NOTES", "")

    # -- server coordinates -------------------------------------------------

    @property
    def ssh_host(self) -> str:
        return self.fields.get("SSH_HOST", "")

    @property
    def ssh_user(self) -> str:
        return self.fields.get("SSH_USER", "")

    @property
    def ssh_key(self) -> str:
        """Path to the private key, or "" to let ssh pick its default."""
        return self.fields.get("SSH_KEY", "")

    @property
    def ssh_key_source(self) -> str:
        """Where the key comes from when it is not materialised yet.

        Informational, and the message the selector prints when the key path
        does not exist -- so the operator is told what to extract, not just
        that something is missing.
        """
        return self.fields.get("SSH_KEY_SOURCE", "")

    @property
    def ssh_alias(self) -> str:
        return self.fields.get("SSH_ALIAS", "")

    @property
    def env_profile(self) -> str:
        """Name of the server's env profile, used as ``-Penv=<profile>``."""
        return self.fields.get("ENV_PROFILE", "")

    @property
    def checkout(self) -> str:
        """The server checkout **on the box**: delivery target and Gradle cwd."""
        return self.fields.get("CHECKOUT", "")

    # -- standalone coordinates ---------------------------------------------

    @property
    def app_root(self) -> str:
        """The app repository carrying the Electron shell."""
        return self.fields.get("APP_ROOT", "")

    @property
    def home(self) -> str:
        """``VPATH_STANDALONE_HOME`` -- runtime state, keys and KPs."""
        return self.fields.get("HOME", "")

    @property
    def ssh_target(self) -> str:
        return f"{self.ssh_user}@{self.ssh_host}"


@dataclass(frozen=True)
class Registry:
    """Every instance the operator has declared, in declaration order."""

    instances: tuple[Instance, ...]
    path: Path

    def names(self) -> tuple[str, ...]:
        return tuple(i.name for i in self.instances)

    def get(self, name: str) -> Instance:
        for instance in self.instances:
            if instance.name == name:
                return instance
        raise RegistryError(
            f"unknown instance {name!r} -- {self.path} declares "
            f"{', '.join(self.names()) or '<none>'}"
        )


def default_register_path(start: Path | None = None) -> Path:
    """Where the register is expected, without reading it.

    Precedence: ``$VPATH_INSTANCES_FILE``, then ``<repo-root>/instances.local.env``.
    """
    from_env = os.environ.get(REGISTER_ENV_VAR)
    if from_env:
        return Path(from_env).expanduser()
    root = Path(start) if start is not None else Path(__file__).resolve().parents[3]
    return root / DEFAULT_REGISTER_NAME


def expand(value: str) -> str:
    """Expand ``~`` and ``$HOME``-style references in a path field.

    ``$HOME`` is resolved explicitly before ``expandvars``: on Windows a
    PowerShell-spawned Python has ``USERPROFILE`` but often no ``HOME``, and
    ``expandvars`` would pass the reference through verbatim — turning a
    path field into a literal ``$HOME/...`` that exists nowhere.
    """
    home = os.environ.get("HOME") or str(Path.home())
    resolved = re.sub(r"\$\{HOME\}|\$HOME\b", home.replace("\\", "\\\\"), value)
    return os.path.expanduser(os.path.expandvars(resolved))


def parse_lines(lines: list[str], source: str) -> dict[str, str]:
    """Parse ``KEY=VALUE`` lines into a mapping, rejecting anything else.

    A line that is neither blank, nor a full-line comment, nor a ``KEY=VALUE``
    assignment is an error: a register that silently drops a line the operator
    wrote is a register that will one day point at the wrong box.
    """
    values: dict[str, str] = {}
    for number, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = _LINE_RE.match(line)
        if match is None:
            raise RegistryError(
                f"{source}:{number}: not a KEY=VALUE line -- "
                f"{_describe_malformed(line)}"
            )
        key = match.group("key")
        if key in values:
            raise RegistryError(f"{source}:{number}: {key} declared twice")
        values[key] = _unquote(match.group("value").strip())
    return values


def _describe_malformed(line: str) -> str:
    """Name a malformed register line without repeating what it carries.

    The register is the one file holding an operator's access data, and this
    message is printed to stderr by every consumer -- so it is captured into
    whatever log the run is being teed into.  Echoing the line would put the
    value there.  The key is named because a key is not a secret; everything
    right of the ``=`` is described by shape only.
    """
    key, separator, _ = line.partition("=")
    if separator:
        return f"key {key.strip()!r} is not a bare identifier"
    return f"no '=' found in {len(line)} characters"


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def _instance_from(name: str, values: Mapping[str, str], source: str) -> Instance:
    prefix = f"{name.upper()}_"
    fields = {k[len(prefix) :]: v for k, v in values.items() if k.startswith(prefix)}

    kind = fields.get("KIND", "")
    if kind not in ALL_KINDS:
        raise RegistryError(
            f"{source}: {prefix}KIND is {kind!r}; expected one of "
            f"{', '.join(sorted(ALL_KINDS))}"
        )

    lifecycle = fields.get("LIFECYCLE", LIFECYCLE_LIVE)
    if lifecycle not in ALL_LIFECYCLES:
        raise RegistryError(
            f"{source}: {prefix}LIFECYCLE is {lifecycle!r}; expected one of "
            f"{', '.join(sorted(ALL_LIFECYCLES))}"
        )

    if lifecycle == LIFECYCLE_LIVE:
        required = (
            REQUIRED_SERVER_FIELDS
            if kind in SERVER_KINDS
            else REQUIRED_STANDALONE_FIELDS
        )
        missing = [key for key in required if not fields.get(key)]
        if missing:
            raise RegistryError(
                f"{source}: instance {name!r} ({kind}) is missing "
                + ", ".join(f"{prefix}{key}" for key in missing)
            )

    expanded = {k: (expand(v) if k in PATH_FIELDS else v) for k, v in fields.items()}
    return Instance(
        name=name, kind=kind, lifecycle=lifecycle, fields=expanded, source=source
    )


def load(path: Path | None = None) -> Registry:
    """Read and validate the register.  Raises rather than guessing."""
    register = Path(path) if path is not None else default_register_path()
    if not register.is_file():
        raise RegistryError(
            f"no instance register at {register} -- copy {TEMPLATE_NAME} there "
            f"and fill in your own instances (it is gitignored), or point "
            f"{REGISTER_ENV_VAR} at one"
        )

    source = str(register)
    values = parse_lines(register.read_text(encoding="utf-8").splitlines(), source)

    declared = values.get("VPATH_INSTANCES", "").split()
    if not declared:
        raise RegistryError(f"{source}: VPATH_INSTANCES is empty -- nothing declared")

    seen: set[str] = set()
    instances: list[Instance] = []
    for name in declared:
        if not NAME_RE.match(name):
            raise RegistryError(
                f"{source}: instance name {name!r} must be lower-case "
                f"alphanumeric starting with a letter"
            )
        if name in seen:
            raise RegistryError(f"{source}: instance {name!r} declared twice")
        seen.add(name)
        instances.append(_instance_from(name, values, source))

    return Registry(instances=tuple(instances), path=register)
