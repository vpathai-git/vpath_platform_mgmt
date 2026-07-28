"""Domain model: roles, verbs, jobs, audit events, and typed ops errors."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum


class Role(str, Enum):
    """Platform roles, ordered by privilege (see docs/USER_ACCESS.md)."""

    SERVER_DEV = "server-dev"
    APP_DEV = "app-dev"
    ADMIN = "admin"


ROLE_RANK: dict[Role, int] = {Role.SERVER_DEV: 0, Role.APP_DEV: 1, Role.ADMIN: 2}


class Verb(str, Enum):
    """Operations the platform executes (see docs/PLATFORM_FUNCTIONS.md)."""

    BUILD = "build"
    DEPLOY = "deploy"
    HEALTH = "health"
    STATUS = "status"
    LOGS = "logs"
    UNINSTALL = "uninstall"
    REINSTALL = "reinstall"
    ERASE = "erase"


VERB_ROLE: dict[Verb, Role] = {
    Verb.BUILD: Role.APP_DEV,
    Verb.DEPLOY: Role.APP_DEV,
    Verb.UNINSTALL: Role.APP_DEV,
    Verb.HEALTH: Role.SERVER_DEV,
    Verb.STATUS: Role.SERVER_DEV,
    Verb.LOGS: Role.SERVER_DEV,
    Verb.REINSTALL: Role.ADMIN,
    Verb.ERASE: Role.ADMIN,
}

DESTRUCTIVE_VERBS: frozenset[Verb] = frozenset({Verb.REINSTALL, Verb.ERASE})
READ_VERBS: frozenset[Verb] = frozenset({Verb.HEALTH, Verb.STATUS, Verb.LOGS})

CLUSTER_SCOPE = "cluster"


def lock_scope(verb: Verb, app: str) -> str | None:
    """Lock a verb needs: cluster-exclusive, per-app, or none for reads."""
    if verb in DESTRUCTIVE_VERBS:
        return CLUSTER_SCOPE
    if verb in READ_VERBS:
        return None
    return f"app:{app}"


class JobState(str, Enum):
    """Lifecycle of a job."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass
class Job:
    """One verb invocation: who asked for what, and how it is going."""

    verb: Verb
    app: str
    actor: str
    role: Role
    # Which adapter executed this job. Stamped per job so no screenshot or
    # log excerpt of a simulated run can be mistaken for a real deployment.
    engine: str = "unknown"
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    state: JobState = JobState.QUEUED
    step: str = "queued"
    log: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    result: dict[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        """JSON-serializable view of the job."""
        return {
            "id": self.id,
            "verb": self.verb.value,
            "app": self.app,
            "actor": self.actor,
            "role": self.role.value,
            "engine": self.engine,
            "state": self.state.value,
            "step": self.step,
            "log": list(self.log),
            "created_at": self.created_at,
            "result": self.result,
        }


@dataclass(frozen=True)
class AuditEvent:
    """Append-only record of an action — including refused ones."""

    actor: str
    role: str
    action: str
    target: str
    result: str
    at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, object]:
        """JSON-serializable view of the event."""
        return {
            "actor": self.actor,
            "role": self.role,
            "action": self.action,
            "target": self.target,
            "result": self.result,
            "at": self.at,
        }


class OpsError(Exception):
    """Base for typed ops failures; carries the HTTP status the API maps to."""

    http_status = 400

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class UnknownVerbError(OpsError):
    """The requested verb does not exist."""

    http_status = 400


class RefusedError(OpsError):
    """RBAC refused the verb for this role. Refusals are audited."""

    http_status = 403


class ConfirmationRequiredError(OpsError):
    """Destructive verb submitted without the typed confirmation."""

    http_status = 400


class LockHeldError(OpsError):
    """The required lock is held by another job."""

    http_status = 409
