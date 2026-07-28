"""Confluence read-only client (spaces + page tree)."""

from .client import ConfluenceClient
from .errors import ConfluenceError
from .models import PageNode, Space

__all__ = ["ConfluenceClient", "ConfluenceError", "PageNode", "Space"]
