"""Platform instances: the register, the selector, and the status probe.

One register declares every environment the operator has -- server boxes and
local standalones alike.  The selector turns a name into an invocation of the
server project's pipeline; the probe turns the same name into a reading of what
that environment currently is.  Neither of them owns a second copy of anything
the server already declares.

Entry points::

    python -m vpath_platform_mgmt.instances.selector list
    python -m vpath_platform_mgmt.instances.probe
"""

from .registry import (
    ALL_KINDS,
    KIND_REMOTE,
    KIND_SERVER_CLOUD_VM,
    KIND_SERVER_NUC,
    KIND_STANDALONE,
    Instance,
    Registry,
    RegistryError,
    load,
)

__all__ = [
    "ALL_KINDS",
    "KIND_REMOTE",
    "KIND_SERVER_CLOUD_VM",
    "KIND_SERVER_NUC",
    "KIND_STANDALONE",
    "Instance",
    "Registry",
    "RegistryError",
    "load",
]
