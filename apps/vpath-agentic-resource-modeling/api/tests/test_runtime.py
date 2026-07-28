"""Contract tests for the agent RUNTIME endpoints (cognition/runtime.py).

These are DETERMINISTIC and need NO real LLM: every assertion exercises the
fail-closed / out-of-contract path, which the SDK factory resolves BEFORE it
ever imports the pinned agent lib. The live-LLM happy path (a real ``create`` +
``chat``) is deliberately NOT tested here — it needs a bound provider and is
covered as code-complete/unverified (see KNOWN_GAPS.md / DEPLOYMENT.md).

The suite mounts the real ``runtime_router`` on a bare FastAPI app, overrides
``require_auth`` with a verified-identity stand-in (the platform verifies the
token in production; the SDK enforces the InstanceKey shape either way), and
points the SDK's ResourceManifest at a fixture ``resource.json`` per case.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from vpath_backend_sdk import require_auth
from vpath_backend_sdk.agent_factory import get_agent_factory
from vpath_backend_sdk.auth_context import AuthContext

from cognition.runtime import runtime_router


def _ctx(subject: str = "alice") -> AuthContext:
    """A verified-identity AuthContext stand-in; ``ctx.sub`` is the username."""
    principal = f"user:{subject}"
    return AuthContext(
        subject=principal,
        actor=principal,
        chain=(principal,),
        username=subject,
        email=None,
        groups=(),
        credential_type="keycloak_jwt",
        scopes=(),
        is_admin=False,
        is_maintainer=False,
    )


def _contract(
    *,
    agents: tuple[str, ...] = ("basic-llm",),
    models: tuple[str, ...] = ("gpt-4o",),
    llm_providers: tuple[str, ...] = ("openai",),
) -> dict:
    """The bind-emitted agent-provider contract row shape (a satisfied row)."""
    return {
        "requirement": {
            "id": "agent",
            "class": "agent-provider",
            "actions": ["use"],
            "required": True,
        },
        "satisfied": True,
        "allowed": {
            "agents": list(agents),
            "models": list(models),
            "llm_providers": list(llm_providers),
        },
        "members": [{"type": "agent-provider", "variant": a} for a in agents],
        "transport": {"kind": "direct-provider"},
    }


@pytest.fixture
def make_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Build a TestClient bound to a fixture manifest (or an absent one, for the
    unbound path). The SDK factory cache is cleared so each case re-binds."""

    def _make(contracts: Optional[list[dict]], subject: str = "alice") -> TestClient:
        get_agent_factory.cache_clear()
        if contracts is None:
            manifest = tmp_path / "absent.json"  # never created -> unbound
        else:
            manifest = tmp_path / "resource.json"
            manifest.write_text(
                json.dumps(
                    {
                        "resolved_at": "2026-07-22T00:00:00+00:00",
                        "resources": [],
                        "contracts": contracts,
                    }
                ),
                encoding="utf-8",
            )
        monkeypatch.setenv("VPATH_RESOURCE_JSON_PATH", str(manifest))
        app = FastAPI()
        app.include_router(runtime_router, prefix="/api")
        app.dependency_overrides[require_auth] = lambda: _ctx(subject)
        return TestClient(app)

    return _make


def _invoke_body(**overrides: Any) -> dict:
    body = {"agent": "basic-llm", "model": "gpt-4o", "message": "hello"}
    body.update(overrides)
    return body


def test_offerings_projects_bound_contract(make_client) -> None:
    """GET /runtime/offerings is a pure projection of the bound contract."""
    client = make_client([_contract()])
    resp = client.get("/api/runtime/offerings")
    assert resp.status_code == 200
    assert resp.json() == {
        "agents": ["basic-llm"],
        "models": ["gpt-4o"],
        "llm_providers": ["openai"],
    }


def test_invoke_out_of_contract_agent_is_typed_refusal(make_client) -> None:
    """An agent outside the contract is refused 422 AgentNotInContract, with the
    contract quoted — never coerced to a nearest-allowed agent."""
    client = make_client([_contract(agents=("basic-llm",))])
    resp = client.post("/api/runtime/invoke", json=_invoke_body(agent="rogue-agent"))
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["code"] == "AgentNotInContract"
    assert "rogue-agent" in detail["message"]
    assert detail["contract"] == {
        "agents": ["basic-llm"],
        "models": ["gpt-4o"],
        "llm_providers": ["openai"],
    }


def test_invoke_out_of_contract_model_is_typed_refusal(make_client) -> None:
    """A model outside the contract is refused 422 ModelNotInContract."""
    client = make_client([_contract(models=("gpt-4o",))])
    resp = client.post(
        "/api/runtime/invoke", json=_invoke_body(model="gpt-not-offered")
    )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["code"] == "ModelNotInContract"
    assert "gpt-not-offered" in detail["message"]


def test_invoke_ambiguous_provider_is_typed_refusal(make_client) -> None:
    """An unstated llm_provider over a multi-value contract is refused (never a
    silent default) — 422 AmbiguousContractChoice."""
    client = make_client([_contract(llm_providers=("openai", "azure"))])
    resp = client.post("/api/runtime/invoke", json=_invoke_body())
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "AmbiguousContractChoice"


def test_offerings_unbound_is_resource_not_bound(make_client) -> None:
    """No bound contract -> 422 resource_not_bound (a real first-use state)."""
    client = make_client(None)
    resp = client.get("/api/runtime/offerings")
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "resource_not_bound"


def test_invoke_unbound_is_resource_not_bound(make_client) -> None:
    """Invoking with nothing bound fails closed — 422 resource_not_bound."""
    client = make_client(None)
    resp = client.post("/api/runtime/invoke", json=_invoke_body())
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "resource_not_bound"
