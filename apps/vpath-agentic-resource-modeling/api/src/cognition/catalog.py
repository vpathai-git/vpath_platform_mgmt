"""The reachable-model catalog (axes 1 + 5) and the wrapper/variant table.

Mirrors ``vpath_agents``' ``AuthModeSpec`` (declared per wrapper in
``env_spec.py``) and ``catalog.resolve_model_set``: one declaration per
``(llm_provider, auth_mode)`` with its ``model_source`` and (for curated/catalog)
the committed roster. Ratified facts honored (concept §10, 2026-06-19):

  * ``api_key``/``azure`` => ``open`` (BYO key reaches the full catalog; a
    whitelist would reject valid new models). Only ``subscription`` (curated)
    and ``local`` (probe) enforce membership.

The ``probe`` source needs a LIVE local endpoint, which an offline modeler has
no access to — so resolving a probe set FAIL-HARDs with ``probe_requires_live_endpoint``
rather than faking a served list (CLAUDE.md §7 — never simulate a feature).

The nine wrappers are the agent runtimes (= the resource ``variant``):
Class A (in-process LiteLLM, creds pre-resolved): basic-llm, basic-agent;
Class B (subprocess/CLI, self-resolve): claude, gemini, opencode-srv, copilot,
copilot-cli, pi, a2a. This OFFLINE slice wires the variants over the providers
it can describe with vendored capability facts.
"""

from __future__ import annotations

from dataclasses import dataclass

from .axes import MODEL_SOURCES, AuthMode, CognitionError

# For ``open`` modes the membership set is NOT gated; these are the models the
# editor OFFERS as suggestions (each has a vendored capability record). For
# ``curated`` modes the tuple IS the committed, membership-enforced roster.


@dataclass(frozen=True)
class ProbeSpec:
    """How to discover the served model set for a ``local`` (probe) auth mode.

    Pure data (mirrors vpath_agents ``model_card/spec.ProbeSpec``):
    ``endpoint_env`` names the env var holding the endpoint base URL (e.g.
    ``OLLAMA_API_BASE``); ``path`` is the listing endpoint (``/api/tags`` for
    Ollama, ``/v1/models`` for vLLM). The live probe client is out of scope for
    this OFFLINE modeler — resolving a probe set FAIL-HARDs here (never faked).
    """

    endpoint_env: str
    path: str


@dataclass(frozen=True)
class AuthModeSpec:
    """One ``(llm_provider, auth_mode)`` declaration — the editor's CRUD object,
    mirroring vpath_agents ``model_card/spec.AuthModeSpec``.

    The model set is config-as-data (no model-id literals in logic): ``models``
    is the curated/whitelisted roster for ``curated``/``catalog``; ``probe``
    carries the discovery spec for ``probe``; ``open`` needs neither (BYO
    passthrough). ``__post_init__`` enforces those invariants FAIL-HARD.
    """

    llm_provider: str
    mode: AuthMode
    model_source: str  # one of axes.MODEL_SOURCES
    models: tuple[str, ...] = ()  # roster (curated) OR offered suggestions (open)
    probe: ProbeSpec | None = None
    example_model: str | None = None

    def __post_init__(self) -> None:
        # Mirror AuthModeSpec.__post_init__ in vpath_agents: a malformed spec is
        # a hard error at construction, never a silent default.
        if self.model_source not in MODEL_SOURCES:
            raise ValueError(
                f"AuthModeSpec({self.llm_provider}/{self.mode.value}): "
                f"model_source={self.model_source!r} not in {MODEL_SOURCES}"
            )
        if self.model_source == "probe" and self.probe is None:
            raise ValueError(
                f"AuthModeSpec({self.llm_provider}/{self.mode.value}): "
                f"model_source='probe' requires a ProbeSpec"
            )
        if self.model_source in ("curated", "catalog") and not self.models:
            raise ValueError(
                f"AuthModeSpec({self.llm_provider}/{self.mode.value}): "
                f"model_source={self.model_source!r} requires a non-empty "
                f"models tuple"
            )
        # "open": user-defined passthrough — neither models nor probe required.


# provider -> {auth_mode_value -> AuthModeSpec}
PROVIDERS: dict[str, dict[str, AuthModeSpec]] = {
    "openai": {
        "api_key": AuthModeSpec(
            "openai",
            AuthMode.API_KEY,
            "open",
            ("gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"),
            example_model="gpt-4o",
        ),
    },
    "azure": {
        "api_key": AuthModeSpec(
            "azure",
            AuthMode.API_KEY,
            "open",
            ("azure/gpt-4-turbo", "azure/gpt-4", "azure/gpt-35-turbo"),
            example_model="azure/gpt-4-turbo",
        ),
    },
    "anthropic": {
        "subscription": AuthModeSpec(
            "anthropic",
            AuthMode.SUBSCRIPTION,
            "curated",
            ("opus", "sonnet"),
            example_model="sonnet",
        ),
        "api_key": AuthModeSpec(
            "anthropic",
            AuthMode.API_KEY,
            "open",
            ("opus", "sonnet", "haiku"),
            example_model="sonnet",
        ),
    },
    "ollama": {
        "local": AuthModeSpec(
            "ollama",
            AuthMode.LOCAL,
            "probe",
            (),  # served set is discovered live; none offline
            probe=ProbeSpec(endpoint_env="OLLAMA_API_BASE", path="/api/tags"),
            example_model=None,
        ),
    },
}


@dataclass(frozen=True)
class Variant:
    """An agent runtime (= the agent-provider resource ``variant``)."""

    name: str
    wrapper_class: str  # "A" (in-process LiteLLM) | "B" (subprocess/CLI)
    # The (llm_provider, auth_mode_value) pairs this wrapper declares it accepts.
    supports: tuple[tuple[str, str], ...]


# A faithful slice of the nine-wrapper matrix (concept §6), wired over the
# providers this offline modeler can describe.
VARIANTS: dict[str, Variant] = {
    "basic-llm": Variant(
        "basic-llm",
        "A",
        # LiteLLM (in-process) also reaches a local Ollama endpoint, so basic-llm
        # is the lone wrapper here that declares (ollama, local) — selecting it
        # exercises the 'probe' source, which FAIL-HARDs offline (no live host).
        (
            ("openai", "api_key"),
            ("azure", "api_key"),
            ("anthropic", "subscription"),
            ("ollama", "local"),
        ),
    ),
    "basic-agent": Variant(
        "basic-agent",
        "A",
        (("openai", "api_key"), ("azure", "api_key")),
    ),
    "claude": Variant(
        "claude",
        "B",
        (("anthropic", "subscription"),),
    ),
    "opencode-srv": Variant(
        "opencode-srv",
        "B",
        (("openai", "api_key"), ("azure", "api_key")),
    ),
    "pi": Variant(
        "pi",
        "B",
        (("openai", "api_key"), ("anthropic", "api_key")),
    ),
}


def find_auth_mode_spec(llm_provider: str, auth_mode: AuthMode) -> AuthModeSpec:
    """The matching :class:`AuthModeSpec`, or FAIL-HARD listing what's declared."""
    provider_specs = PROVIDERS.get(llm_provider)
    if not provider_specs:
        raise CognitionError(
            "unknown_provider",
            f"unknown provider {llm_provider!r}; known: {sorted(PROVIDERS)}. "
            f"No default is substituted.",
        )
    spec = provider_specs.get(auth_mode.value)
    if spec is None:
        declared = sorted(provider_specs)
        raise CognitionError(
            "auth_mode_not_declared",
            f"provider {llm_provider!r} declares no auth-mode "
            f"{auth_mode.value!r}; declared: {declared}. "
            f"No default is substituted.",
        )
    return spec


def resolve_model_set(spec: AuthModeSpec) -> frozenset[str]:
    """The membership-enforced reachable set for a ``curated``/``catalog`` spec.

    ``open`` has no enumerable set (BYO passthrough — caller must skip the gate);
    ``probe`` needs a live endpoint this offline modeler does not have. Both
    reaching here are FAIL-HARD (never a faked set).
    """
    if spec.model_source in ("curated", "catalog"):
        return frozenset(spec.models)
    if spec.model_source == "open":
        raise CognitionError(
            "open_mode_has_no_membership_gate",
            f"({spec.llm_provider!r}, {spec.mode.value!r}) is an 'open' "
            f"passthrough mode with no enumerable model set — it must not be "
            f"gated by membership.",
        )
    # probe (local) — the served set comes from a live listing call we cannot
    # make offline. Name the ProbeSpec target so the reason is concrete.
    probe = spec.probe
    target = f"${probe.endpoint_env}{probe.path}" if probe else "a live endpoint"
    raise CognitionError(
        "probe_requires_live_endpoint",
        f"({spec.llm_provider!r}, {spec.mode.value!r}) resolves its model set by "
        f"probing {target}, which this offline modeler cannot reach. Run it "
        f"against a live served endpoint to enumerate models.",
    )


def variant_or_fail(name: str) -> Variant:
    """The :class:`Variant` for ``name``, or FAIL-HARD."""
    v = VARIANTS.get(name)
    if v is None:
        raise CognitionError(
            "unknown_variant",
            f"unknown wrapper/variant {name!r}; known: {sorted(VARIANTS)}. "
            f"No default is substituted.",
        )
    return v


def describe_catalog() -> dict:
    """A JSON-serializable view of the whole catalog for the editor."""
    providers = []
    for provider, modes in PROVIDERS.items():
        providers.append(
            {
                "provider": provider,
                "auth_modes": [
                    {
                        "auth_mode": spec.mode.value,
                        "model_source": spec.model_source,
                        "membership_enforced": spec.model_source
                        in ("curated", "catalog"),
                        "models": list(spec.models),
                        "example_model": spec.example_model,
                        "probe": (
                            {
                                "endpoint_env": spec.probe.endpoint_env,
                                "path": spec.probe.path,
                            }
                            if spec.probe
                            else None
                        ),
                    }
                    for spec in modes.values()
                ],
            }
        )
    variants = [
        {
            "name": v.name,
            "wrapper_class": v.wrapper_class,
            "supports": [{"provider": p, "auth_mode": a} for (p, a) in v.supports],
        }
        for v in VARIANTS.values()
    ]
    return {"providers": providers, "variants": variants}
