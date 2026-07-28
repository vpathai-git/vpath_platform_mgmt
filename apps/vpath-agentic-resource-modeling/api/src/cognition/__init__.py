"""The cognition modeling layer — a small, self-contained, OFFLINE slice of
vpath_agents' cognition-config concept (the 5-axis model).

This package REUSES the concept (it does not reinvent it): the five axes
(Provider, AuthMode, Credentials, ModelRequirements, ModelCatalog), the
``model_source`` kinds, and a vendored slice of capability facts that mirrors
``vpath_agents/common/model_registry/data.py``. Capability facts are read from
the vendored registry only — we NEVER call models.dev live (CLAUDE.md §5/§7).

The app composes/validates a ``(provider, auth_mode, model)`` selection in this
cognition shape and PROJECTS it onto the platform's ``agent-provider`` resource
(declared in the manifest, never hand-built).
"""
