# Implementation Plan — Management Console MVP

**Date:** 2026-08-10  
**Status:** draft · ready to execute (post-review)  
**Spine:** [summary.md](summary.md) · README “Primary goals” · EIP-248  
**Clarified model (2026-08-10):** `vpath_platform_mgmt` is a Python control
plane / local console. It is **not** an Electron app and **not** a packaging of
`vpath_server`. Electron appears only as `KIND=standalone` *managed instances*
(`APP_ROOT` + `HOME`). Platform stack lifecycle (install/upgrade/delete of k3s
etc.) stays **backlog B1** — out of this plan.

**Goal:** Ship the three axes MVP: dualism UI over server + standalone,
instance templates + register write path + health/history slice, Explorer
deploy demo on one registered **server** instance. App publish/build/deploy
reuses the existing ops surface.

**Architecture:** Extend `instances/` (templates, CRUD, richer probe, local
history) and expose fleet list/detail via `/api/instances*`. Console gains
master-detail over that API while keeping today’s single-instance ops drive
(`--instance`). Axis 3 iteration 1 proves Explorer via selector + health.

**Stack:** Python 3.10+, FastAPI, existing console static UI, pytest. No new
dependencies unless a later task proves need (then `make scan`).

**Constraints:** `AGENTS.md` (250-line files, type hints, fail-hard, ≥85%
coverage, `make check`). Register payload stays gitignored; type templates are
versioned. Kind hooks stay in `transport.py` / `probe.py` (decision M1).

**Rollback:** each phase is one PR; revert the PR. Register format changes need
a documented one-way adapter in the same PR.

---

## Out of scope (explicit)

| Item | Why |
|---|---|
| Packaging platform-mgmt as Electron | Rejected model (C) |
| B1 platform stack CRUD | Backlog |
| B2–B5 | Backlog |
| `remote` proven live ops | M2 + [remote-type-survey](remote-type-survey.issue.md) |
| OntoGate adoption in this repo | M3: thin link only |
| UI create (`POST /api/instances`) | CLI/`crud.py` only in MVP |
| Continuous deep monitoring | Stays with `/monitor/`; console links |
| Arsany Explorer remote cutover | After demo |

**MVP cut (Axis 1 apps/state):** detail pane shows status + ops entry + kind
stubs; **apps** reuse existing `/api/apps*` only after operator selects drive
instance (no second catalog). Full shared “state” panel beyond probe + history
slice is post-MVP polish.

---

## Phase 0 — Baseline freeze (½ day)

**Files:** edit this plan’s decision log only.

- [ ] Confirm entrypoints: `vpath-console`, `vpath`, `python -m …instances.selector|probe`
- [ ] Record kind set: `server-nuc` \| `server-cloud-vm` \| `standalone` \| `remote` (new, unproven)
- [ ] Alias: docs `nuc` → template `server-nuc`
- [ ] Run `make check`; paste baseline SHA into decision log below

**Done when:** baseline SHA recorded here.

---

## Phase 1 — Templates + register write + `remote` admit (Axis 2 / M1–M2)

**Creates**
- `instances/templates/{server-nuc,server-cloud-vm,standalone,remote}.yaml`
- `instances/templates/__init__.py` (load + validate)
- `instances/crud.py` (add / update / remove → env file, atomic replace)
- `tests/instances/test_templates.py`, `test_crud.py`, `test_remote_refused.py`

**Modifies**
- `registry.py` — admit `remote` into kinds; load templates; fail-hard unchanged
- `selector.py` / `transport.py` / `probe.py` — refuse live ops for `remote` and
  for `LIFECYCLE=planned` with explicit error (not silent skip)
- `docs/INSTANCES.md` — KIND table + template workflow + four place fields
- `instances.example.env` — templated shape including `server-cloud-vm`

**Behaviour**
1. `create(kind, name, fields)` validates against template, appends block
2. Missing required field → raise naming the field (no invented hosts)
3. `remote` may exist in register; probe/selector/gradle/deliver **refuse**

**Tests (fail first)**
- `standalone` requires `APP_ROOT` + `HOME`; `server-cloud-vm` requires SSH + profile fields
- Register with `KIND=remote` loads; `selector exec` / probe exit `2` with “unproven”
- CRUD round-trip; corrupt line fails hard on load

**Verify:** `pytest tests/instances/` then `make check`

---

## Phase 2 — Fleet API + dualism shell + history slice (Axis 1–2)

**Creates**
- `api/routes_instances.py`
- `instances/history.py` — append-only gitignored JSONL (path from env /
  default beside register); schema: `ts`, `name`, `kind`, `coarse`, `fields`
- `tests/test_api_instances.py`, `tests/instances/test_history.py`

**Modifies**
- `api/app.py` — mount routes
- `console.html|js|css` — left list, detail pane (status, history, kind stubs,
  ops entry that does **not** auto-switch engine)
- `probe.py` — after each reading, append history event
- `tests/test_api_console.py`

**API**
- `GET /api/instances` → name, kind, lifecycle, coarse health
- `GET /api/instances/{name}` → masked register + latest probe + last N history
- **No** write/POST in MVP

**Error logs (MVP):** when console is driving the same instance, surface last
failed job log ref from existing jobs API; no new log shipper. Uptime = probe
fields already defined in instance-status strand.

**Tests:** empty register `[]`; server+standalone listed; secrets masked;
history append + read; UI markers for list/detail

**Verify:** `pytest tests/test_api_instances.py tests/test_api_console.py tests/instances/test_history.py` then `make check`

---

## Phase 3 — Standalone status-file probe (parallel track)

**Independent of Phase 4.** Hard gate only for *standalone* deploy demos.

**Depends on (external):** Electron supervisor status file under `HOME`.

**Modifies:** `probe.py`, `docs/INSTANCES.md`,
`tests/instances/test_probe_standalone_status_file.py`

**Contract keys:** `pid`, `port`|`ports`, `started_at`, `version`|`build_id`.
Missing file → named gap, never fake healthy.

**Verify:** fixture unit tests; optional Alpha manual probe.

---

## Phase 4 — Explorer deploy demo (Axis 3 / M4) — ∥ Phase 3

**Does not wait on Phase 3.** Server-instance path only for MVP success.

**Issue:** [explorer-quick-extraction.issue.md](explorer-quick-extraction.issue.md)  
**Tree:** `apps/vpath-explorer/`

- [ ] THROWAWAY + Arsany-future note in `apps/vpath-explorer/README.md`
- [ ] Deploy via selector to one registered **server** instance + health proof
- [ ] Runbook: `explorer-deploy-demo.notes.md` (steps, instance, haltepunkte)
- [ ] Standalone deploy demo = optional follow-up after Phase 3

**Verify:** notes checklist + `make check` if code touched.

---

## Phase 5 — Thin OntoGate link (M3)

Optional `ONTOGATE_URL` on register; detail UI link or “not available”;
tests in `test_api_instances.py`. No repo-root `.ontogate/`.

---

## Phase 6 — Docs sync

- [ ] Update [summary.md](summary.md): phase completion table; kind wording to
  code set `server-nuc` \| `server-cloud-vm` \| `standalone` \| `remote`
  (docs alias `nuc` → `server-nuc`; product types `nuc`/`standalone`/`remote`
  map onto that set)
- [ ] Align stale “not implemented” stamps with `docs/ADDING_AN_APP.md`
- [ ] Final `make check`

---

## Suggested PR order

| PR | Phase | Notes |
|---|---|---|
| 1 | 0–1 | Templates, CRUD, `remote` refuse paths |
| 2 | 2 | Fleet API, UI shell, history slice |
| 3a | 4 | Explorer server demo (**parallel** with 3b) |
| 3b | 3 | Standalone status file (external-blocked OK) |
| 4 | 5–6 | OntoGate link + docs |

---

## Verification matrix

| Requirement | Evidence |
|---|---|
| Dualism list/detail | `/api/instances*` + console tests |
| Templates + CRUD + cloud-vm | `test_templates` / `test_crud` |
| `remote` admitted, ops refused | `test_remote_refused` |
| History + error-log slice | `test_history` + jobs log ref in UI |
| Explorer demo (server) | `explorer-deploy-demo.notes.md` |
| Quality gate | `make check` |
| Not Electron control plane | no Electron packaging tasks |

---

## Decision log

- 2026-08-10: Electron A/B rejected; model **C**.
- 2026-08-10: MVP excludes B1–B5, UI instance POST, deep monitor duplication.
- 2026-08-10: Axis 1 apps = reuse drive-instance `/api/apps*`; dualism “state”
  beyond probe+history is polish.
- 2026-08-10: Phase 4 ∥ Phase 3; Explorer MVP proof is **server** only.
- 2026-08-10: Review fixes applied (code-reviewer 7c3df34f).
- Phase 0 baseline SHA: d2373cf (main tip when branch opened)
- Phase 1 landed on branch `feature/mgmt-console-mvp-phase1` (templates, crud, remote refuse).
- Phase 2 landed on same branch: `/api/instances*`, history JSONL, console master-detail (`instances.js`).
- Phase 3–6 landed: status-file probe, Explorer THROWAWAY + runbook, `ONTOGATE_URL`, docs sync.
  Live Explorer health on a real box remains an operator checklist item.
