"""Ops control plane: verbs, RBAC, locks, audit, job execution.

The guardrail layer defined in docs/PLATFORM_FUNCTIONS.md: every verb runs
as a job, gated by role, serialized by locks, and audited — including
refusals. Engine adapters decide how verbs execute (simulated or real).
"""

from vpath_platform_mgmt.ops.argocd import ArgoClient, ArgoError
from vpath_platform_mgmt.ops.audit import AuditLog
from vpath_platform_mgmt.ops.engine import (
    EngineAdapter,
    EngineFailure,
    LocalEngine,
    SimulatedEngine,
)
from vpath_platform_mgmt.ops.gitea import GiteaClient, GiteaError
from vpath_platform_mgmt.ops.gitops_engine import GitOpsEngine
from vpath_platform_mgmt.ops.locks import LockManager
from vpath_platform_mgmt.ops.model import (
    ConfirmationRequiredError,
    Job,
    JobState,
    LockHeldError,
    OpsError,
    RefusedError,
    Role,
    UnknownVerbError,
    Verb,
)
from vpath_platform_mgmt.ops.service import OpsService

__all__ = [
    "ArgoClient",
    "ArgoError",
    "AuditLog",
    "ConfirmationRequiredError",
    "EngineAdapter",
    "EngineFailure",
    "GitOpsEngine",
    "GiteaClient",
    "GiteaError",
    "Job",
    "JobState",
    "LocalEngine",
    "LockHeldError",
    "LockManager",
    "OpsError",
    "OpsService",
    "RefusedError",
    "Role",
    "SimulatedEngine",
    "UnknownVerbError",
    "Verb",
]
