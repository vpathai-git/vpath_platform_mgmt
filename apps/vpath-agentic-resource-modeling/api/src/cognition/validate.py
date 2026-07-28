"""The resolution flow — the cognition gate, FAIL-HARD at every step.

Mirrors ``agent_factory/cognition_bridge.apply_cognition_resolution``:

  1. derive/parse the AuthMode (axis 2),
  2. REACHABILITY — the requested model must be in the reachable set for the
     (provider, auth_mode); ``open`` skips the membership gate (axis 5),
  3. CAPABILITY — if the caller declares ModelRequirements, the model must
     PROVE them against the vendored registry (axis 4),
  4. (variant compatibility) — the chosen wrapper must declare it accepts this
     (provider, auth_mode).

All four are FAIL-HARD with a structured ``CognitionError`` (no fallback). On
success the selection is PROJECTED onto the agent-provider resource shape.
"""

from __future__ import annotations

from .axes import CognitionError, ModelRequirements, parse_auth_mode
from .catalog import find_auth_mode_spec, resolve_model_set, variant_or_fail
from .projection import project
from .registry import has_record, lookup


def _check_reachability(spec, model: str) -> None:
    """Step 2: membership gate for curated/catalog; open skips; probe FAIL-HARD."""
    if spec.model_source == "open":
        return  # BYO passthrough — no membership gate (ratified)
    reachable = resolve_model_set(spec)  # FAIL-HARD for probe (live endpoint)
    if model not in reachable:
        raise CognitionError(
            "model_not_in_set",
            f"model {model!r} is not in the {spec.model_source} set for "
            f"({spec.llm_provider!r}, {spec.mode.value!r}): "
            f"{sorted(reachable)}. No default is substituted.",
        )


def _check_capability(provider: str, model: str, reqs: ModelRequirements) -> dict:
    """Step 3: prove the model satisfies the declared requirements, or FAIL-HARD.

    Returns the resolved capability facts (so the editor can show them). When no
    requirement is declared AND the model has no registry record (legitimate for
    an ``open`` BYO model), capabilities are reported as ``unknown`` — never
    assumed (CLAUDE.md §7).
    """
    if reqs.is_empty() and not has_record(provider, model):
        return {"known": False}
    info = lookup(provider, model)  # FAIL-HARD if no capability record
    unmet = []
    if reqs.function_calling and not info.supports_function_calling:
        unmet.append("function_calling")
    if reqs.vision and not info.supports_vision:
        unmet.append("vision")
    if reqs.reasoning and not info.supports_reasoning:
        unmet.append("reasoning")
    if reqs.structured_output and not info.supports_structured_output:
        unmet.append("structured_output")
    if reqs.min_context and info.context_window < reqs.min_context:
        unmet.append(
            f"min_context>={reqs.min_context} (model has {info.context_window})"
        )
    if unmet:
        raise CognitionError(
            "capability_unmet",
            f"model {model!r} does not satisfy required capabilities: "
            f"{', '.join(unmet)}. No default is substituted.",
        )
    return {"known": True, **info.as_dict()}


def _check_variant(variant_name: str, provider: str, auth_mode_value: str) -> None:
    """Step 4: the wrapper must declare it accepts this (provider, auth_mode)."""
    variant = variant_or_fail(variant_name)
    if (provider, auth_mode_value) not in variant.supports:
        declared = [f"{p}/{a}" for (p, a) in variant.supports]
        raise CognitionError(
            "variant_incompatible",
            f"wrapper {variant_name!r} (class {variant.wrapper_class}) does not "
            f"declare ({provider!r}, {auth_mode_value!r}); it declares: "
            f"{declared}. No default is substituted.",
        )


def validate_selection(
    provider: str,
    auth_mode_value: str,
    model: str,
    variant: str,
    requirements: ModelRequirements,
) -> dict:
    """Run the full FAIL-HARD flow and PROJECT on success.

    Raises :class:`CognitionError` (structured) on any rejection. The route
    layer maps that to HTTP 422 — never a soft pass.
    """
    auth_mode = parse_auth_mode(auth_mode_value)  # step 1 (FAIL-HARD)
    spec = find_auth_mode_spec(provider, auth_mode)  # FAIL-HARD on unknown combo
    _check_variant(variant, provider, auth_mode.value)  # step 4
    _check_reachability(spec, model)  # step 2
    capabilities = _check_capability(provider, model, requirements)  # step 3
    return {
        "valid": True,
        "selection": {
            "provider": provider,
            "auth_mode": auth_mode.value,
            "model": model,
            "variant": variant,
        },
        "model_source": spec.model_source,
        "membership_enforced": spec.model_source in ("curated", "catalog"),
        "capabilities": capabilities,
        "projection": project(provider, model, variant, auth_mode.value),
    }
