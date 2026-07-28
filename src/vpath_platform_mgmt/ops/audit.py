"""Append-only audit log: every action, including refused ones."""

from __future__ import annotations

import threading

from vpath_platform_mgmt.ops.model import AuditEvent

DEFAULT_MAX_ENTRIES = 500


class AuditLog:
    """Bounded, thread-safe, newest-first audit record."""

    def __init__(self, max_entries: int = DEFAULT_MAX_ENTRIES) -> None:
        if max_entries < 1:
            raise ValueError("max_entries must be >= 1")
        self._max_entries = max_entries
        self._events: list[AuditEvent] = []
        self._mutex = threading.Lock()

    def record(
        self, actor: str, role: str, action: str, target: str, result: str
    ) -> AuditEvent:
        """Append one event and return it."""
        event = AuditEvent(
            actor=actor, role=role, action=action, target=target, result=result
        )
        with self._mutex:
            self._events.insert(0, event)
            del self._events[self._max_entries :]
        return event

    def entries(self) -> list[dict[str, object]]:
        """Newest-first serializable events."""
        with self._mutex:
            return [event.to_dict() for event in self._events]
