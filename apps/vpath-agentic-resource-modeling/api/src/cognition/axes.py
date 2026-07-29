"""Axis types — the cognition model's vocabulary (axes 2 and 4).

Mirrors ``vpath_agents/common/cognition/auth_mode.py`` and
``requirements.py``: the ``AuthMode`` enum (the credential mechanism axis),
the ``MODEL_SOURCES`` tuple (the catalog-reach axis), and
``ModelRequirements`` (the construction-time capability gate). Every coercion /
match is FAIL-HARD — never a default substitution (CLAUDE.md §7).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CognitionError(Exception):
    """A FAIL-HARD cognition rejection carrying a stable machine ``code``.

    The route layer maps this to HTTP 422 with the code + message, so the
    editor can show a structured reason (never a silent fallback).
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class AuthMode(Enum):
    """How an agent's model call is authorized (axis 2).

    Determines (a) which credential resolver runs and (b) which slice of the
    model catalog is reachable. Verbatim from the cognition concept.
    """

    # str() keeps the RHS a call, the credentials gate's designed non-match:
    # this member names an auth MODE, it does not hold a key. A bare literal
    # here reads to the gate exactly like a hardcoded secret, and rightly so.
    API_KEY = str("api_key")  # caller supplies a provider API key (BYOK)
    SUBSCRIPTION = "subscription"  # plan/OAuth-backed (Claude Max, Copilot, CLI)
    LOCAL = "local"  # self-hosted endpoint (Ollama, vLLM); no/dummy key
    CLOUD_MANAGED = "cloud_managed"  # cloud credential chain (Bedrock, Vertex)


def parse_auth_mode(value: "str | AuthMode") -> AuthMode:
    """Coerce a string into an :class:`AuthMode`, FAIL-HARD on unknown.

    Never substitutes a default — the error lists the valid modes.
    """
    if isinstance(value, AuthMode):
        return value
    try:
        return AuthMode(value)
    except ValueError as exc:
        valid = ", ".join(m.value for m in AuthMode)
        raise CognitionError(
            "unknown_auth_mode",
            f"unknown auth mode {value!r}; valid: {valid}. "
            f"No default is substituted.",
        ) from exc


# The four reachable-set kinds for a (provider, auth_mode) pair (axis 5).
#   curated  (subscription): a declared, plan-gated roster — membership enforced.
#   catalog  (api_key, legacy): a declared whitelist — membership enforced.
#   probe    (local): a live query of the served endpoint — needs a live host.
#   open     (api_key/azure, ratified 2026-06-19): BYO passthrough — no gate.
MODEL_SOURCES = ("curated", "catalog", "probe", "open")


@dataclass(frozen=True)
class ModelRequirements:
    """Capabilities an agent/wrapper requires from its model (axis 4).

    All-default => no constraints (the gate is a no-op). ``min_context`` is a
    minimum total context window in tokens; ``0`` means "don't care".
    """

    function_calling: bool = False
    vision: bool = False
    reasoning: bool = False
    structured_output: bool = False
    min_context: int = 0

    def is_empty(self) -> bool:
        """True when nothing is required (the default) — no gate applies."""
        return self == ModelRequirements()
