"""Agent RUNTIME — the canonical get_agent_factory() path for this example.

Where ``routes.py`` DECLARES (compose + project a selection onto the
agent-provider resource) and reads the binding read-only, this module RUNS the
bound agent through the SDK's ONE door (CITIZENS.md §1):

  GET  /runtime/offerings — the bound contract projected verbatim
                            (``factory.offerings().to_dict()``); a pure read.
  POST /runtime/invoke    — construct ONE agent inside the contract
                            (``factory.create(...)`` keyed by the verified sub +
                            a conversation id) and send it one message; the
                            answer STREAMS when the runtime exposes a real
                            ``chat_stream``, else it is returned plainly — never
                            a simulated stream (CLAUDE.md "Never Simulate").

Fail-closed error contract (CITIZENS.md §5 — no fallback, no retry on another
agent/model):
  * unbound (no manifest / no agent-provider contract row)  -> 422 resource_not_bound
  * out-of-contract parameter (AgentNotInContract, ...)     -> 422, contract quoted
  * cognition path not operable / upstream/provider failure -> 502

The factory is BACKEND-ONLY and is imported from its module, never the package
root (CITIZENS.md §1). This app NEVER holds a provider key or builds an LLM
client — the SDK transport owns credentials.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, AsyncIterator, Mapping, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from starlette.concurrency import iterate_in_threadpool, run_in_threadpool
from vpath_backend_sdk import AuthContext, require_auth
from vpath_backend_sdk.agent_factory import (
    AgentContractError,
    AgentContractInvalid,
    AgentContractMissing,
    AgentContractViolation,
    InstanceKey,
    get_agent_factory,
)

runtime_router = APIRouter()

_NOT_BOUND_HINT = (
    "the platform writes a bound agent-provider contract to resource.json once "
    "an agent-provider is bound; nothing is invented in its absence."
)


class InvokeRequest(BaseModel):
    """One message to one agent, constructed inside the binding contract."""

    agent: str = Field(min_length=1, max_length=64)
    model: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=8192)
    llm_provider: Optional[str] = Field(default=None, max_length=64)
    conversation_id: Optional[str] = Field(default=None, max_length=128)
    stream: bool = False


def _factory() -> Any:
    """Open the app's ONE door to agents, mapping the fail-closed door errors
    (unbound / unusable contract) onto the app's 422 contract. lru_cache does
    not cache these exceptions, so a later call re-binds once bound."""
    try:
        return get_agent_factory()
    except FileNotFoundError as exc:
        raise _http(422, "resource_not_bound", f"{_NOT_BOUND_HINT} ({exc})") from exc
    except AgentContractMissing as exc:
        raise _http(422, "resource_not_bound", str(exc)) from exc
    except AgentContractInvalid as exc:
        raise _http(422, "contract_unusable", str(exc)) from exc


def _http(status: int, code: str, message: str, **extra: Any) -> HTTPException:
    return HTTPException(
        status_code=status, detail={"code": code, "message": message, **extra}
    )


def _refusal(exc: AgentContractViolation, factory: Any) -> HTTPException:
    """A typed out-of-contract refusal (AgentNotInContract, ModelNotInContract,
    ...) surfaced as 422 with the contract quoted — never coerced."""
    return _http(
        422,
        type(exc).__name__,
        str(exc),
        contract=factory.offerings().to_dict(),
    )


@runtime_router.get("/runtime/offerings")
async def offerings(ctx: AuthContext = Depends(require_auth)) -> dict:
    """The bound contract, projected verbatim — a pure read, no availability
    probing, byte-faithful to resource.json."""
    del ctx  # identity is verified by the dependency; the read is contract-wide
    return _factory().offerings().to_dict()


@runtime_router.post("/runtime/invoke")
async def invoke(body: InvokeRequest, ctx: AuthContext = Depends(require_auth)) -> Any:
    """Construct one agent inside the contract and send it one message."""
    factory = _factory()
    conversation_id = body.conversation_id or uuid.uuid4().hex
    instance = await _create(factory, body, ctx.sub, conversation_id)

    if body.stream and callable(getattr(instance, "chat_stream", None)):
        return _stream(factory, instance, body.message)

    answer = await _send(factory, instance, body.message)
    return {
        "conversation_id": conversation_id,
        "agent": body.agent,
        "model": body.model,
        "streamed": False,
        "answer": str(answer),
    }


async def _create(
    factory: Any, body: InvokeRequest, user_sub: str, conversation_id: str
) -> Any:
    """factory.create(...) keyed per user + per conversation (R-7). Construction
    is fail-fast; out-of-contract -> 422, an inoperable cognition path -> 502."""
    try:
        return await run_in_threadpool(
            factory.create,
            agent=body.agent,
            model=body.model,
            llm_provider=body.llm_provider,
            instance_key=InstanceKey(
                user_sub=user_sub, conversation_id=conversation_id
            ),
        )
    except AgentContractViolation as exc:
        raise _refusal(exc, factory) from exc
    except AgentContractMissing as exc:  # bound-then-unbound between door and use
        raise _http(422, "resource_not_bound", str(exc)) from exc
    except AgentContractError as exc:  # transport / instance-key / unusable contract
        raise _http(502, "cognition_unavailable", str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 — provider/upstream: lib, 401, network
        raise _http(502, "cognition_upstream_error", str(exc)) from exc


async def _send(factory: Any, instance: Any, message: str) -> Any:
    """One non-streamed message. A capability exercised outside the contract at
    send time is still a typed 422; a provider/upstream fault is a 502."""
    try:
        return await run_in_threadpool(instance.chat, message)
    except AgentContractViolation as exc:
        raise _refusal(exc, factory) from exc
    except AgentContractError as exc:
        raise _http(502, "cognition_unavailable", str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise _http(502, "cognition_upstream_error", str(exc)) from exc


def _stream(factory: Any, instance: Any, message: str) -> StreamingResponse:
    """Real streaming over the runtime's own incremental surface. chat_stream()
    yields a SYNC iterator that blocks on the LLM's network chunks — consumed in
    a threadpool so the event loop is never stalled. Nothing is buffered and
    re-emitted as one chunk (that would be a simulated stream)."""

    async def events() -> AsyncIterator[str]:
        try:
            iterator = await run_in_threadpool(instance.chat_stream, message)
            async for item in iterate_in_threadpool(iterator):
                yield _sse(item)
            yield f"data: {json.dumps({'delta': '', 'is_final': True})}\n\n"
        except AgentContractViolation as exc:
            yield _sse_error("out_of_contract", str(exc))
        except AgentContractError as exc:
            yield _sse_error("cognition_unavailable", str(exc))
        except Exception as exc:  # noqa: BLE001
            yield _sse_error("cognition_upstream_error", str(exc))

    return StreamingResponse(events(), media_type="text/event-stream")


def _sse(item: Any) -> str:
    if isinstance(item, Mapping) and "event_type" in item:
        return f"data: {json.dumps(dict(item))}\n\n"
    return f"data: {json.dumps({'delta': str(item), 'is_final': False})}\n\n"


def _sse_error(code: str, message: str) -> str:
    return f"data: {json.dumps({'error': code, 'detail': message})}\n\n"
