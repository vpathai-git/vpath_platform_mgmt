"""Lock manager: per-app serialization, cluster-exclusive destructive ops."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

from vpath_platform_mgmt.ops.model import CLUSTER_SCOPE, LockHeldError


@dataclass(frozen=True)
class LockInfo:
    """Who holds a lock, for which job, since when."""

    scope: str
    holder: str
    job_id: str
    since: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, object]:
        """JSON-serializable view of the lock."""
        return {
            "scope": self.scope,
            "holder": self.holder,
            "job_id": self.job_id,
            "since": self.since,
        }


class LockManager:
    """Grants locks per docs/PLATFORM_FUNCTIONS.md.

    ``app:<name>`` scopes serialize jobs per app and may coexist across
    different apps. ``cluster`` is exclusive: it is refused while any lock
    is held, and while held it refuses everything else.
    """

    def __init__(self) -> None:
        self._locks: dict[str, LockInfo] = {}
        self._mutex = threading.Lock()

    def acquire(self, scope: str, holder: str, job_id: str) -> None:
        """Take the lock or raise ``LockHeldError`` naming the blocker."""
        with self._mutex:
            blocker = self._blocking_lock(scope)
            if blocker is not None:
                raise LockHeldError(
                    f"{scope} blocked: {blocker.scope} held by "
                    f"{blocker.holder} (job {blocker.job_id})"
                )
            self._locks[scope] = LockInfo(scope=scope, holder=holder, job_id=job_id)

    def _blocking_lock(self, scope: str) -> LockInfo | None:
        if CLUSTER_SCOPE in self._locks:
            return self._locks[CLUSTER_SCOPE]
        if scope == CLUSTER_SCOPE and self._locks:
            return next(iter(self._locks.values()))
        return self._locks.get(scope)

    def release(self, scope: str) -> None:
        """Release a lock; releasing a free lock is a no-op by design."""
        with self._mutex:
            self._locks.pop(scope, None)

    def snapshot(self) -> list[dict[str, object]]:
        """Current locks for display (console 'who is deploying what')."""
        with self._mutex:
            return [lock.to_dict() for lock in self._locks.values()]
