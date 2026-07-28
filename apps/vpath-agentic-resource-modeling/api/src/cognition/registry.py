"""Vendored, OFFLINE model-capability facts (axis 4's data source).

A small, deterministic slice mirroring
``vpath_agents/common/model_registry/data.py`` (the models.dev ``base_model``
inheritance shape): canonical capability records keyed by a base-model slug,
plus ``(llm_provider, model)`` bindings that point at a canonical record and may
override individual fields.

This is a curated seed read at runtime — we NEVER call models.dev live
(CLAUDE.md §5). ``lookup`` FAIL-HARDs on an unknown pair: a model the registry
cannot describe is a loud error, which is exactly what the capability matcher
relies on to refuse "assume capable".
"""

from __future__ import annotations

from dataclasses import dataclass

from .axes import CognitionError

# Canonical capability records (base models). Verbatim subset of the vendored
# vpath_agents registry — same numbers, same flags.
CANONICAL: dict[str, dict] = {
    "claude-opus": {
        "context_window": 200000,
        "supports_function_calling": True,
        "supports_vision": True,
        "supports_reasoning": True,
        "supports_structured_output": True,
    },
    "claude-sonnet": {
        "context_window": 200000,
        "supports_function_calling": True,
        "supports_vision": True,
        "supports_reasoning": True,
        "supports_structured_output": True,
    },
    "claude-haiku": {
        "context_window": 200000,
        "supports_function_calling": True,
        "supports_vision": True,
        "supports_reasoning": False,
        "supports_structured_output": True,
    },
    "gpt-4o": {
        "context_window": 128000,
        "supports_function_calling": True,
        "supports_vision": True,
        "supports_reasoning": False,
        "supports_structured_output": True,
    },
    "gpt-4o-mini": {
        "context_window": 128000,
        "supports_function_calling": True,
        "supports_vision": True,
        "supports_reasoning": False,
        "supports_structured_output": True,
    },
    "gpt-4-turbo": {
        "context_window": 128000,
        "supports_function_calling": True,
        "supports_vision": True,
        "supports_reasoning": False,
        "supports_structured_output": True,
    },
    "gpt-4": {
        "context_window": 8192,
        "supports_function_calling": True,
        "supports_vision": False,
        "supports_reasoning": False,
        "supports_structured_output": False,
    },
    "gpt-3.5-turbo": {
        "context_window": 16385,
        "supports_function_calling": True,
        "supports_vision": False,
        "supports_reasoning": False,
        "supports_structured_output": False,
    },
}

# (llm_provider, model_id) -> {"base_model": <CANONICAL key>, **overrides}.
# ``anthropic`` covers both the Anthropic API and the Claude Max bridge
# subscription — same models, same capability records.
BINDINGS: dict[tuple[str, str], dict] = {
    ("anthropic", "opus"): {"base_model": "claude-opus"},
    ("anthropic", "sonnet"): {"base_model": "claude-sonnet"},
    ("anthropic", "haiku"): {"base_model": "claude-haiku"},
    ("openai", "gpt-4o"): {"base_model": "gpt-4o"},
    ("openai", "gpt-4o-mini"): {"base_model": "gpt-4o-mini"},
    ("openai", "gpt-4-turbo"): {"base_model": "gpt-4-turbo"},
    ("openai", "gpt-4"): {"base_model": "gpt-4"},
    ("openai", "gpt-3.5-turbo"): {"base_model": "gpt-3.5-turbo"},
    ("azure", "azure/gpt-4"): {"base_model": "gpt-4"},
    ("azure", "azure/gpt-35-turbo"): {"base_model": "gpt-3.5-turbo"},
    ("azure", "azure/gpt-4-turbo"): {"base_model": "gpt-4-turbo"},
}


@dataclass(frozen=True)
class ModelInfo:
    """The capability facts for one ``(llm_provider, model)`` pair."""

    name: str
    provider: str
    context_window: int
    supports_function_calling: bool
    supports_vision: bool
    supports_reasoning: bool
    supports_structured_output: bool

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "provider": self.provider,
            "context_window": self.context_window,
            "supports_function_calling": self.supports_function_calling,
            "supports_vision": self.supports_vision,
            "supports_reasoning": self.supports_reasoning,
            "supports_structured_output": self.supports_structured_output,
        }


def lookup(llm_provider: str, model: str) -> ModelInfo:
    """Resolve ``(llm_provider, model)`` to :class:`ModelInfo`, applying
    ``base_model`` inheritance, or FAIL-HARD when no record exists.

    Never returns a default/empty ModelInfo — an undescribable model is a loud
    ``model_no_capability_record`` error (add it to the registry).
    """
    binding = BINDINGS.get((llm_provider, model))
    if binding is None:
        known = sorted({m for (_p, m) in BINDINGS})
        raise CognitionError(
            "model_no_capability_record",
            f"no capability record for ({llm_provider!r}, {model!r}) in the "
            f"vendored model registry. Known models: {known}. "
            f"No default is substituted.",
        )
    base_key = binding["base_model"]
    record = dict(CANONICAL[base_key])
    record.update({k: v for k, v in binding.items() if k != "base_model"})
    return ModelInfo(
        name=model,
        provider=llm_provider,
        context_window=record.get("context_window", 4096),
        supports_function_calling=record.get("supports_function_calling", False),
        supports_vision=record.get("supports_vision", False),
        supports_reasoning=record.get("supports_reasoning", False),
        supports_structured_output=record.get("supports_structured_output", False),
    )


def has_record(llm_provider: str, model: str) -> bool:
    """True iff the registry can describe this pair (no exception)."""
    return (llm_provider, model) in BINDINGS
