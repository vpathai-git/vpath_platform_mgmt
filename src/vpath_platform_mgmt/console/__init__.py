"""The management console: one view over every platform type.

The console is split in two on purpose.  Everything that decides *what is
true* lives here in Python and is tested: :mod:`.view` builds the generic
dual view (axis 1), :mod:`.api` is the single entry point that serves it and
performs instance CRUD from the versioned type templates (axis 2).  The
Electron shell in ``electron/`` only renders what this package hands it -- it
holds no logic of its own, so nothing the operator sees can disagree with what
``make check`` verified.

Entry point::

    python -m vpath_platform_mgmt.console.api view --probe
"""

from .view import build, instance_view

__all__ = ["build", "instance_view"]
