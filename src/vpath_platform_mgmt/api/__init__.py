"""HTTP surface: FastAPI app, auth modes, and the thin web console."""

from vpath_platform_mgmt.api.app import create_app
from vpath_platform_mgmt.api.auth import AuthError, Identity, dev_identity

__all__ = ["AuthError", "Identity", "create_app", "dev_identity"]
