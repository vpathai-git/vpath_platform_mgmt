# Known gaps — standalone runtime deltas (`as_is`, accepted)

**Status: ACCEPTED as-is — filed + fixed UPSTREAM, not yet in this kit.** These are NOT app
defects: this app declares `spec.ui` and `spec.resourceRequirements` correctly, and its OntoGate
hull contracts (`C-zero-header`, `C-need-resource-requirements`) stay GREEN — it inherits the
platform GIVENs and declares its NEEDs. The gap is that the **standalone** runtime does not yet
*fulfill* those manifest-declared GIVENs for kit-authored (off-monorepo) apps the way the k3s
cluster does.

## Delta A — no activity-bar header (from `spec.ui`)

On the standalone, the in-app `VpathActivityBar` header does not render for this app (the **sidebar
tile** does — that part is platform-side and present). Mechanism: `createVpathApp` resolves the
activity identity from the SDK's build-time-generated `app-identity-defaults.ts` (platform apps
only); kit apps are absent from that baked map, and the vendored `kit/sdk` is pinned at a SHA that
**predates the fix**. The runtime `spec.ui` is not consulted by the SDK for these apps.

- Filed: **GitHub `vpathai-git/vpath_server#21`** — "spec.ui → activity-bar header not derivable for
  externally-authored apps (SDK build-tooling gap)". **CLOSED/completed (2026-06-19).** Fix commit
  `ba0fc957` (Wave M1) on branch `fix/standalone-dogfooding`.

## Delta B — no resource approval / binding window (from `spec.resourceRequirements`)

The standalone does not prompt to approve/bind a declared resource. For an **agent-provider** (what
this app declares) the standalone **seeds a default** `resource.json` at boot **by design** —
agent-provider is `envfrom` / not identity-bearing, so it is platform-provided, not user-bound. For a
*credential* class the fixed gate now fail-closes (401 + `X-Vpath-Bind-Required`), but there is **no
bind-flow UI yet**, and the cluster's first-launch **interception ceremony** (`confirmed_at`) is
**deliberately omitted** in the single-tenant standalone.

- Filed: **GitHub `vpathai-git/vpath_server#22`** — "Standalone runtime: no resource-gate —
  resourceRequirements unfulfilled". **CLOSED/completed (2026-06-19).** Fix commit `d923d6f9`
  (Wave M2: `resource-gate.ts` + `binding-store.ts`) on `fix/standalone-dogfooding`.
- **Unfiled:** a real selection/approval flow for the **agent-provider** path (this app's
  `selection: agent-provider: user-selectable`) is out of #22's scope by design and has no separate
  bug yet. Candidate follow-up report.

## Delta C — agent runtime: no bound provider CONTRACT in the standalone (live invoke unverified)

WP3 added the runtime path (`api/src/cognition/runtime.py`): `GET /api/runtime/offerings`
projects the bound contract, and `POST /api/runtime/invoke` runs one agent through the SDK's
`get_agent_factory().create(...)` + a message. Two maturity states, marked honestly (CITIZENS.md §6):

- **Refusal / contract path — `field-testable`, TESTED.** Unbound → `422 resource_not_bound`;
  out-of-contract parameter → the typed refusal (`AgentNotInContract` / `ModelNotInContract` /
  `AmbiguousContractChoice`) as `422` with the contract quoted. These resolve BEFORE the SDK ever
  imports the pinned agent lib, so they run with NO real LLM — proven by `api/tests/test_runtime.py`
  (6 cases) and by the `runtime-fail-closed-on-cold-load` step of
  `tests/scenarios/standalone-agentic-runtime.ts`.
- **Live-LLM happy path (`create` + `chat`/`chat_stream`) — `code-complete-unverified`.** It needs a
  bound agent-provider **contract** (`contracts[]` in resource.json). The bind step that emits that
  array (`agent_contract_binding.py`, offer ∩ constraints) is **cluster-only**; the standalone seeds
  only a read-only `resources[]` default (Delta B), not a `contracts[]` row — so `get_agent_factory()`
  raises `AgentContractMissing` and the runtime fails closed. There is no bound provider in this
  environment (decision **K5**), so the streamed happy path is code-complete but **not** user-visibly
  verified here. It is NOT simulated: `stream=true` requires a real `chat_stream` on the runtime, else
  the answer is returned plainly (never a buffered-then-chunked fake).

- **Unfiled:** a live agent-provider **contract** in the standalone (cluster-parity bind) is out of
  scope for #21/#22 and has no separate bug yet. Candidate follow-up report — same family as the
  Delta B "real selection/approval flow" note above.

## Shared root cause + resolution path

Both reduce to one root: **off-cluster fulfillment is not manifest-driven** — the standalone had no
TS manifest parser (substrate added in `6e7c3057`, M0; then #21/M1, #22/M2). Root report on the kit
`meta` branch: `reports/2026-06-15-1601-standalone-runtime-deltas-header-and-resource-gate.md`.

The fix lives on platform branch `fix/standalone-dogfooding`, **NOT on platform `main`**. **When it
merges to main, re-vendor `kit/sdk`** (`scripts/refresh_kit.sh` + bump `kit/VERSION`) and the header
(Delta A) + the resource gate (Delta B) flow into kit apps automatically. We do **not** vendor the
unmerged branch now (pin-to-stable-SHA discipline).

> ⚠️ Don't grep platform `main` for "#21"/"#22" — the internal tracker reuses those numbers for
> unrelated tickets. The GitHub issues above are the standalone ones.
