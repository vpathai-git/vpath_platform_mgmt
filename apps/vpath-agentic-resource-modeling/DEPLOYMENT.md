# DEPLOYMENT — vpath-agentic-resource-modeling

This example ships **two layers over the same `agent-provider` citizen** (CITIZENS.md §1):

1. **Declaration** — compose a `(provider, auth_mode, model)` selection in the cognition shape,
   validate it (reachability + capability), and project it onto the `agent-provider` resource; plus a
   read-only view of the currently-bound resource. (`api/src/cognition/routes.py`, `.../catalog.py`,
   `.../validate.py`, `.../projection.py`.)
2. **Runtime (WP3)** — the canonical `get_agent_factory()` path: project the bound contract and run one
   agent through it. (`api/src/cognition/runtime.py`.)

## Endpoints

| Method + path (backend) | Web path (via the proxy) | Purpose |
|---|---|---|
| `GET /api/providers` | `/api/modeling/providers` | the cognition catalog the editor offers |
| `POST /api/validate` | `/api/modeling/validate` | validate + project a selection (422 on rejection) |
| `GET /api/resource/status` | `/api/modeling/resource/status` | the currently-bound `agent-provider` (read-only) |
| `GET /api/runtime/offerings` | `/api/modeling/runtime/offerings` | the bound contract, projected verbatim |
| `POST /api/runtime/invoke` | `/api/modeling/runtime/invoke` | construct one agent + send one message |

The web reaches the api through the SDK proxy (`createProxyRoute`, `src/app/api/modeling/[...path]`);
the Dapr-shape target is read from runtime env, never baked in (CLAUDE.md §5).

## What the app declares (and never does)

- Declares `spec.resourceRequirements.required: [{class: agent-provider, ...}]` (the NEED face, filled
  for real). The platform binds it (offer ∩ constraints) and delivers a `contracts[]` row in
  `resource.json`; the SDK `get_agent_factory()` reads that row and refuses anything outside it.
- **Never** holds a provider key, builds an LLM client, imports `vpath_agents` directly, or reads
  `resource.json` by hand. The factory is backend-only and imported from its module
  (`from vpath_backend_sdk.agent_factory import get_agent_factory, InstanceKey`).

## Fail-closed error contract (no fallback, no retry — CITIZENS.md §5)

- **Unbound** (no manifest / no `agent-provider` contract row) → `422 resource_not_bound`.
- **Out-of-contract** parameter → the typed refusal (`AgentNotInContract` / `ModelNotInContract` /
  `ProviderNotInContract` / `AmbiguousContractChoice`) as `422`, **with the contract quoted**. Nothing
  is coerced to a nearest-allowed value; to widen the contract, change the manifest and re-bind.
- **Upstream / provider** failure (unreachable endpoint, 401/REVOKED, lib fault) → `502`. A 401
  propagates untouched — no silent re-fetch, no retry on another agent/model.
- **Streaming** rides the runtime's real `chat_stream` when present; otherwise the answer is returned
  plainly. Streaming is **never simulated** (no buffer-then-chunk).

## Maturity — marked honestly (CITIZENS.md §6; playbook rule 10)

| Capability | State | Evidence |
|---|---|---|
| Declaration + projection (editor) | **field-verified** | `tests/scenarios/standalone-agentic.ts` |
| Read-only bound-resource status | **field-verified** | same scenario (`nothing bound yet` first-run) |
| Runtime refusal / contract path | **field-testable, TESTED** | `api/tests/test_runtime.py` (6 cases); `standalone-agentic-runtime.ts` fail-closed step |
| Live-LLM happy path (`create` + `chat`/`chat_stream`) | **code-complete-unverified** | no bound provider **contract** in this standalone (decision **K5**); see KNOWN_GAPS.md Delta C |

**The live-LLM happy path has NOT been seen working in a browser** (Rule 3/3a): the standalone binds no
`contracts[]` row (that bind step is cluster-only), so `get_agent_factory()` fails closed here. Do not
claim it works until a bound provider contract is present and the streamed answer is verified on the
real path.

## Deploy targets

- **Cluster (k3s)** — zero platform edits: manifest auto-discovery (P5). The bind step emits the
  `agent-provider` contract; the runtime path then runs live once a provider is bound.
- **Standalone (Electron)** — currently an additive `standalone/src/main/index.ts` entry is still
  required (the one known standalone-only registry gap; keep it additive). The runtime path is present
  but fails closed until a bound provider contract exists (KNOWN_GAPS.md Delta C).

## Tests

- **Python contract tests** — `api/tests/test_runtime.py`. Deterministic, no real LLM (the refusal /
  unbound paths resolve before the pinned lib is imported). Run:
  ```
  uv venv /tmp/arm-venv && uv pip install --python /tmp/arm-venv/bin/python \
      kit/sdk-python/vpath-backend-sdk pytest
  cd examples/vpath-agentic-resource-modeling/api && /tmp/arm-venv/bin/python -m pytest tests -q
  ```
- **UI scenarios** — `tests/scenarios/standalone-agentic.ts` (declaration) and
  `tests/scenarios/standalone-agentic-runtime.ts` (runtime fail-closed). Run via `kit/uitest` against a
  live standalone.
- **OntoGate book** — `.ontogate/check.py` (40 stories, incl. the WP3 runtime stories P28–P31 + the
  N09 red-drill). Run by `make check` (`scripts/check_app_books.py`).
