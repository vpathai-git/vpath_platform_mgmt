"""The ``vpath`` CLI — thin client of the Ops API (decision 3: one API,
two thin surfaces; the CLI never contains ops logic)."""

from vpath_platform_mgmt.cli.client import ApiError, Caller, OpsClient

__all__ = ["ApiError", "Caller", "OpsClient"]
