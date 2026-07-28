# Plan — `vpath-agentic-resource-modeling`

**Example #2 of the kit: an OntoGate-driven configurator/modeler for VPath-Agents'
LLM-provider configuration, coupled to the platform's `agent-provider` resource.**

> This file is the build brief. It distills two existing concepts (the vpath_agents
> *cognition* config layer and the platform *agent-provider* resource) so the app can be
> built mostly from here, with the reference repos for deep-dive only.

---

## 1. Why this example exists (two goals)

1. **Prove an OntoGate-driven app project works end-to-end.** Gate modeling is **binding**
   here (the lesson from our battle-test): the app authors `.ontogate/` and
   **`python3 .ontogate/check.py` must be GREEN** as part of Definition-of-Done — not
   optional. Unlike `vpath-fortune-teller` (self-contained, NEED face empty), this app
   **fills the NEED face for real**.
2. **Prototype the configurative aspect** of VPath-Agents' new LLM-provider config — an
   **editor/modeler** for an agent-provider configuration, expressed in the platform's
   resource shape.

## 2. The non-negotiable constraint

We do **NOT** reinvent the configuration methodology. We **reuse** two existing concepts
and **link** them:

- the **cognition configuration layer** of `vpath_agents` (the 5-axis model), and
- the platform's **`agent-provider`** resource class.

The app composes/validates an agent-provider configuration *in the cognition shape* and
projects/consumes it *through the platform's agent-provider resource* — **declared, never
hand-built**.

## 3. Domain A — the cognition config concept (what we model)

Authoritative source: `vpath_agents/context/cognition_config/concept.md`. The old
`VPATH_AGENT_LLM_PROVIDER` string conflated independent axes; cognition separates **five**:

1. **Provider** (`llm_provider`) — routing target: `openai, anthropic, azure, openrouter,
   copilot, google, ollama, a2a, …`
2. **AuthMode** (`common/cognition/auth_mode.py`): `api_key | subscription | local |
   cloud_managed`. Determines which credential resolver + which model-set source applies.
3. **Credentials** (`credentials.py`): `ResolvedCredentials(model, transport_model,
   openai/azure/anthropic_api_key, api_base, api_version, env_updates)` — resolved by a
   pure `resolve_credentials(provider, llm_provider, auth_mode, model, env)`.
4. **ModelRequirements** (`requirements.py`): `function_calling, vision, reasoning,
   structured_output, min_context` — a construction-time capability gate, FAIL-HARD.
5. **ModelCatalog per (provider, auth_mode)** (`catalog.py` + `model_card/spec.py`):
   reachable model set, `model_source ∈ {curated, catalog, probe, open}`.

Declaration unit: `AuthModeSpec(llm_provider, mode, model_source, models?, probe?,
example_model?)`, declared per wrapper in `<pkg>/env_spec.py` as `SPEC.auth_modes`.
Capability facts come from the **vendored, offline** `common/model_registry/`
(`models.dev` shape; `ModelInfo.supports_vision/reasoning/structured_output`).
Resolution (`agent_factory/cognition_bridge.apply_cognition_resolution`):
**derive AuthMode → reachability → capability → credentials**, all FAIL-HARD, no fallback.

The **9 wrappers** are the agent runtimes (= the resource `variant`):
- Class A (in-process LiteLLM, creds pre-resolved): `basic-llm`, `basic-agent`.
- Class B (subprocess/CLI, self-resolve): `claude`, `gemini`, `opencode-srv`, `copilot`,
  `copilot-cli`, `pi`, `a2a`.

Ratified facts to honor: `api_key`/`azure` ⇒ `model_source: open` (BYO key reaches the full
catalog); only `subscription` (curated) and `local` (probe) enforce membership.

## 4. Domain B — the platform `agent-provider` resource (how we couple)

Authoritative: `kit/sdk-python/vpath-backend-sdk/docs/manifest-resources.md`; real
consumer `vpath_server/apps_infra/apps/vpath-chat-api`.

- **Declaration** in `vpath-app.yaml`:
  ```yaml
  spec:
    resourceRequirements:
      required:
        - class: agent-provider
          actions: [use, configure]   # 'configure' = edit platform-level settings for it
      selection:
        agent-provider: user-selectable   # user picks among AUTHORIZED instances
  ```
- **Behavior** (closed class; `class_behavior.py`): the **shared** LLM key (Model A, one key
  per pod), `delivery=envfrom`, `identity_bearing=False`, **NOT user-bound/editable** —
  platform-managed. (Contrast: `credential` = per-user, header, identity-bearing;
  `connector` = network endpoint.)
- **Provisioning**: split — non-secret config (`provider`, `model`, `variant`) lands in
  `/etc/vpath/resource.json`; the API key arrives as an **env var** via envFrom secretRef
  (e.g. `OPENAI_API_KEY`). No headers/proxy for this class.
- **Consumption** (backend SDK): `ResourceManifest.load().require("agent-provider")` →
  `.variant`, `.get("provider")`, `.get("model")`, properties; `read_secret(...)` for the
  key. Fail-fast if absent.
- **Hull NEED contract**: `C-need-resource-requirements` (declare via
  `resourceRequirements`; the platform provisions/injects).

## 5. The mapping (cognition ↔ platform resource) — the heart of this example

| cognition axis | platform agent-provider |
|---|---|
| Provider (`llm_provider`) | `resource.properties.provider` |
| Model (chosen from the catalog) | `resource.properties.model` |
| Wrapper / runtime | `resource.variant` (e.g. `basic-llm`, `opencode-srv`) |
| Credentials — secret half | `*_API_KEY` via envfrom — **platform-owned; the app never edits it** |
| **AuthMode / ModelRequirements / catalog source** | **not expressed in the resource today** — the app's modeling layer ADDS this, validating a `(provider, auth_mode, model)` selection *before* it becomes a resource |

**The app's value:** it validates a cognition-correct selection (reachability + capability)
and **projects** it to the agent-provider resource shape; the platform then provisions it.

## 6. Altitude decision (made — redirect if wrong)

This is a **MODELING / EDITOR** app (R1), **not** a live platform mutator (R2):
- It lets a user **compose & validate** an agent-provider configuration and **see/emit** it
  as the resource shape (a `resource.json` preview + the manifest `resourceRequirements`
  snippet).
- It **reads the currently-bound** agent-provider (read-only, via `ResourceManifest`) to
  show "what's live".
- It does **NOT** mutate platform bindings and **never** handles secrets (agent-provider is
  platform-managed). Live admin binding via platform-api is a future extension (R2).

This fits the name ("Modeling"), the platform's "agent-provider is platform-managed"
constraint, and the goal "think about what the config aspect would look like".

## 7. The three things to build

1. **Frontend** (Next, `createVpathApp`, semantic tokens only, zero header chrome):
   an **editor** — pick **Provider → AuthMode → Model**, gated *live* by the cognition rules
   (catalog source + capability requirements via the backend); render the **resolved
   agent-provider resource shape** (`resource.json` preview + manifest snippet); show the
   **currently-bound** provider (read-only). Cover first-run/empty + error states.
2. **Backend** (FastAPI on `vpath_backend_sdk`, every route `require_auth`):
   - Embeds the cognition model: the 5 axes, the `AuthMode` enum, `model_source` kinds,
     `ModelRequirements`, and a **small, vendored, OFFLINE** slice of capability facts
     (a handful of provider/model records mirroring `common/model_registry/data.py`) —
     **do NOT call models.dev live**.
   - `POST /validate` a `(provider, auth_mode, model)` selection → reachability + capability
     check, **FAIL-HARD with structured errors** (e.g. `model_not_in_set`,
     `capability_unmet`), no fallback; returns the projected resource shape on success.
   - `GET /providers` (the catalog the editor offers) and `GET /resource/status` +
     the live agent-provider via `ResourceManifest` (read-only) — `422` if not bound.
3. **Manifest** (`vpath-app.yaml`): `resourceRequirements.required: [{class: agent-provider,
   actions: [use, configure]}]` + `selection: {agent-provider: user-selectable}`;
   `auth.oidcClient`; `ui {title: "Agentic Resource Modeling", icon, description,
   sidebar: true}`; `basePath: /agentic-resource-modeling`; health; dapr; TLS volumes. The
   proxy route + `healthz`/`version` come from the SDK (mirror `vpath-fortune-teller`).

## 8. OntoGate adoption (BINDING — Definition-of-Done)

Author `examples/vpath-agentic-resource-modeling/.ontogate/` **mirroring**
`examples/vpath-fortune-teller/.ontogate/` (reference the kit `foundation/` via `sys.path`;
put red-drill mutation fixtures under `.ontogate/tests/` so `run_audit` skips them):
- `spine.yaml` (Spine-3: `model.app_repo`, the FILL sockets, the NEED face, the 27 contract
  ids), `ontology.json` (via `regenerate.py`, freshness-stamped), `usecases.json`
  (one POSITIVE story per contract + the NEGATIVE red-drill), `check.py` (3-layer:
  gatelib + `foundation.audit.run_audit` + app stories), `tests/mutations.py`.
- **Because this app fills the NEED face for real**, include a NEED-face story that exercises
  `C-need-resource-requirements` (positive: the agent-provider declaration is present;
  negative red-drill: delete `resourceRequirements` → the contract goes RED). Also keep the
  credential-relevant `C-no-bespoke-secret-mount` negative (the app must never read a K8s
  secret name for the key).
- **DoD:** `python3 examples/vpath-agentic-resource-modeling/.ontogate/check.py` → GREEN
  (`N stories, 0 mismatches; APP green`).

## 9. Boundaries / do-not

- **No secrets in app.** Never read/store/prompt an LLM API key — it's platform-injected
  (envfrom). The app models config, not credentials.
- **Do not reinvent** the cognition model or the resource concept — reuse/vendor the offline
  facts; **declare** the resource.
- Read the reference repos **READ-ONLY**; write only under
  `examples/vpath-agentic-resource-modeling/` (+ a `tests/scenarios/` UI scenario).
- Dual-target, fail-fast (no soft pass), **palette tokens only**, **zero header chrome** —
  per `CLAUDE.md` §1–§9.

## 10. Definition of Done

- `make check` GREEN; backend black/flake8 clean; `next build` GREEN.
- `.ontogate/check.py` GREEN (hull adoption real, NEED face exercised).
- Verification per Rule 3/3a attempted; if standalone bring-up is unavailable in the
  checkout, gate + backend tests green + a UI scenario authored + an **honest** gap report.
  **No faked/simulated verification.**
- Committed in logical sets (conventional commits).

## 11. References (READ-ONLY)

- **cognition config**: `/Users/drnorden/projects/vpath/vpath_agents/context/cognition_config/concept.md`;
  `…/src/vpath_agents/common/cognition/{auth_mode,catalog,credentials,requirements,resolved}.py`;
  `…/common/model_registry/{data,lookup}.py`; `…/agent_factory/cognition_bridge.py`;
  `…/dot_env/.env.pi.example` (the provider/auth-mode menu exemplar).
- **platform resource**: `kit/sdk-python/vpath-backend-sdk/docs/manifest-resources.md` (in
  this repo); `/Users/drnorden/projects/vpath/vpath_server/apps_infra/apps/vpath-chat-api/`
  (manifest `vpath-app.yaml` + `src/server.py` — the real consumer);
  `…/vpath-kp-admin-web/vpath-app.yaml` (the `user-selectable` example).
- **hull / OntoGate**: `foundation/ADOPTION.md`, `foundation/spine.yaml`
  (`C-need-resource-requirements`); `examples/vpath-fortune-teller/.ontogate/`
  (the adoption pattern to mirror).
