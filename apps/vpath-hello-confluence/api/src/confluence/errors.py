"""Typed Confluence errors — fail hard, never swallow (CLAUDE.md §7)."""

from __future__ import annotations


class ConfluenceError(Exception):
    """Raised on any non-2xx Confluence response or missing credential.

    `status` is the HTTP status (0 for client-side/config errors). `detail` is a
    short, non-secret message. The credential/token is NEVER included.
    """

    def __init__(self, status: int, detail: str) -> None:
        self.status = status
        self.detail = detail
        super().__init__(f"confluence error {status}: {detail}")
