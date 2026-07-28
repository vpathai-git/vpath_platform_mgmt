"""What one instance *is* -- the kinds, the lifecycles, and the fields.

Split out of :mod:`registry` when the type templates arrived: that module now
parses and validates, this one only describes.  ``registry`` re-exports every
name here, so ``from .registry import Instance`` keeps working.

The four location questions
---------------------------
Axis 2 of the console requires the register to answer, for every instance,
where the moving parts live: the instance itself (``LOCATION``), its build
process (``BUILD_PROCESS``), the repositories that build pulls apps from
(``SOURCE_REPOS``), and its container images (``IMAGE_REGISTRY``).  They are
optional, because an honest blank is worth more than a guessed answer -- the
console renders a missing one as *not declared*, never as an empty string.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

# --- the classes of environment -------------------------------------------

KIND_SERVER_NUC = "server-nuc"
KIND_SERVER_CLOUD_VM = "server-cloud-vm"
KIND_STANDALONE = "standalone"
# The customer-side Windows cluster (win-claas line).  Declared, *unproven*:
# its access and deploy path are structured from what the server project
# already names, and stay marked unproven until the survey issue closes
# (analysis/mgmt-console/remote-type-survey.issue.md).
KIND_REMOTE = "remote"

SERVER_KINDS = frozenset({KIND_SERVER_NUC, KIND_SERVER_CLOUD_VM})
ALL_KINDS = frozenset(SERVER_KINDS | {KIND_STANDALONE, KIND_REMOTE})

# `live` = expected to exist now.  `planned` = named, agreed, not built yet;
# probing it is expected to find nothing, and finding something is a drift.
LIFECYCLE_LIVE = "live"
LIFECYCLE_PLANNED = "planned"
ALL_LIFECYCLES = frozenset({LIFECYCLE_LIVE, LIFECYCLE_PLANNED})

# Fields required per kind.  A `planned` instance is exempt: its coordinates
# are not knowable before it exists.
REQUIRED_SERVER_FIELDS = ("SSH_HOST", "SSH_USER", "ENV_PROFILE", "CHECKOUT")
REQUIRED_STANDALONE_FIELDS = ("APP_ROOT", "HOME")
# Deliberately the one field the server project itself names for this line (a
# customer cluster target).  Nothing else is required, because nothing else is
# established -- see the unproven marker on the `remote` template.
REQUIRED_REMOTE_FIELDS = ("CLUSTER_HOST",)

PATH_FIELDS = frozenset({"SSH_KEY", "CHECKOUT", "APP_ROOT", "HOME"})

# The four location questions, in the order the goal statement asks them.
LOCATION_FIELDS = ("LOCATION", "BUILD_PROCESS", "SOURCE_REPOS", "IMAGE_REGISTRY")


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
    def is_remote(self) -> bool:
        return self.kind == KIND_REMOTE

    @property
    def is_planned(self) -> bool:
        return self.lifecycle == LIFECYCLE_PLANNED

    @property
    def notes(self) -> str:
        return self.fields.get("NOTES", "")

    # -- the four location questions ----------------------------------------

    @property
    def location(self) -> str:
        """Host + filesystem: where this instance lives."""
        return self.fields.get("LOCATION", "")

    @property
    def build_process(self) -> str:
        """Where the build process that feeds this instance lives."""
        return self.fields.get("BUILD_PROCESS", "")

    @property
    def source_repos(self) -> str:
        """Which source repositories that build pulls apps from."""
        return self.fields.get("SOURCE_REPOS", "")

    @property
    def image_registry(self) -> str:
        """Where this instance's container images live."""
        return self.fields.get("IMAGE_REGISTRY", "")

    @property
    def ontogate_view(self) -> str:
        """Base URL of the OntoGate viewer serving this project's Spine.

        Declared per instance rather than derived: the viewer binds an
        auto-picked loopback port (``ontogate-view --port 0``), so no address
        is knowable in advance.  Blank means *no view declared* and is
        rendered as such -- never as a dead link.
        """
        return self.fields.get("ONTOGATE_VIEW", "")

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

    # -- remote coordinates (declared, unproven) ----------------------------

    @property
    def cluster_host(self) -> str:
        """The customer-side cluster target this instance names."""
        return self.fields.get("CLUSTER_HOST", "")

    @property
    def jump_host(self) -> str:
        """Bastion the cluster is reached through, if one is declared."""
        return self.fields.get("JUMP_HOST", "")

    @property
    def ssh_target(self) -> str:
        return f"{self.ssh_user}@{self.ssh_host}"


def required_fields(kind: str) -> tuple[str, ...]:
    """The fields a `live` instance of this kind must carry."""
    if kind in SERVER_KINDS:
        return REQUIRED_SERVER_FIELDS
    if kind == KIND_REMOTE:
        return REQUIRED_REMOTE_FIELDS
    return REQUIRED_STANDALONE_FIELDS
