# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html):
breaking changes bump MAJOR, new features bump MINOR, fixes bump PATCH.
The version lives in `pyproject.toml` (source of truth) and is mirrored in the
package `__init__.py` `__version__` — bump both together (see
`context/CHECKLIST.md`, Gate 3).

## [Unreleased]

### Added
- **Management console, axes 1 and 2** (EIP-248, under EIP-163). Instances are
  created from **versioned type templates** — `nuc`, `cloud-vm`, `standalone`
  and `remote` (win-claas) — in `src/vpath_platform_mgmt/instances/templates/`,
  with `templates.py` (load, validate, render a register stanza) and `crud.py`
  (create/update/remove). Every write is re-read through the register loader
  before it is kept; a rejected edit restores the previous file exactly.
- The **generic dual view** over all instance kinds — status, uptime, apps,
  state, operations, plus type-specific panels, the four location questions
  and the per-instance OntoGate link (`console/view.py`), served by one entry
  point that answers a human and the shell identically (`console/api.py`,
  `--json`). New console scripts: `vpath-console`, `vpath-instance`,
  `vpath-instance-status`.
- The **Electron shell** (`console/electron/`) — master-detail, renders the
  console payload and holds no logic of its own. Build form decided by the
  user on 2026-07-28, closing the open point in `README.md` ("graphical or
  chatbot-assisted, TBD").
- The **`remote` instance kind** with its own kind hooks: the probe reports it
  as `UNPROVEN` (nothing was tried) rather than `UNREACHABLE`, and the
  transport refuses to drive it, until
  `analysis/mgmt-console/remote-type-survey.issue.md` closes.
- The four location questions as register fields (`LOCATION`,
  `BUILD_PROCESS`, `SOURCE_REPOS`, `IMAGE_REGISTRY`) and `ONTOGATE_VIEW`.

### Changed
- `registry.py` split: the `Instance` shape and the kind/lifecycle constants
  moved to `instances/instance.py`, bringing both files back under the 250-line
  rule. `registry.py` re-exports every moved name, so existing imports are
  unaffected.

- **Distributable builds for both halves.** `make dist-python` produces the
  wheel and sdist, `make dist-console` the console binary for the host
  platform (electron-builder does not cross-compile), `make dist` both. New
  `make console` / `make console-install` run the shell from a checkout.

### Fixed
- The wheel packaged 66 files it should not have: setuptools discovered the
  console shell's `node_modules/node-gyp/gyp/pylib/gyp` as a Python package
  (it carries an `__init__.py`) and swept its sources in. Excluded from
  package discovery — the wheel drops from 478 KB to 84 KB.
- The shell resolved the Python side by walking four directories up from
  `__dirname`, which is the repository root only in a checkout — inside
  `app.asar` it is not. A packaged build now relies on the installed package
  instead, and reads its register from `<userData>/instances.local.env`
  rather than a path that would land inside `site-packages`.

### Security
- `electron` pinned to `^43.2.0`: the `^33` line carries a HIGH advisory
  (ASAR integrity bypass, among others).
- `electron-builder` pinned to `^26.15.3` and its transitive
  `brace-expansion` forced to `^5.0.8` via `overrides`. The `@25` tree carried
  28 advisories (27 high, 1 critical); `@26` still pinned vulnerable
  `brace-expansion` lines (GHSA-mh99-v99m-4gvg). `npm audit` now reports 0.

### Notes
- Axis 3 (apps) is not started; the console reports apps as unmanaged and
  names the issue that changes it. Uptime is reported as *not measured* rather
  than relabelling the install marker.
- The console binary is deliberately **not** self-contained: it stays a
  renderer over an installed `vpath-platform-mgmt`. Bundling a Python runtime
  would put a second, silently diverging copy of the console's logic inside
  the shell.

## [0.2.1] - 2026-06-28

### Changed
- Agent-behaviour rules now state the wanted behaviour positively instead of
  enumerating prohibitions, so the guidance is smaller and self-enforcing:
  - `CLAUDE.md` Hard Rule "Never create files unless necessary …" →
    "Work in the files that exist; create one only when the task needs it —
    no unsolicited .md docs; deliver exactly the scope asked, nothing more".
  - `context/RECOMMENDED_WAYS_OF_WORKING.md` §3 "Smallest correct solution" and
    "Bounded subagents" reworded to lead with the action, not the prohibition.

### Removed
- `plain-summary` skill: the redundant "Not this" section — the positive
  "Register" block above it already entails both of its points.

## [0.2.0] - 2026-06-14

### Added (since the field test)
- fable-team temp substitution + max-effort compensation: with Fable
  unavailable as the adversary, the judgment seat is held by a SECOND,
  independent Opus advisor (`advisor--opus`) pinned to `effort: max` — the
  reasoning-budget compensation for sharing the coordinator's tier. New
  read-only `advisor-opus` agent vendored at `.claude/agents/advisor-opus.md`
  (project memory); the skill records the substitution in its machine-checked
  food-chain block (`judgment_substitution`, `judgment_effort: max`), extends
  no-silent-downgrade to cover effort, and has the coordinator reinforce
  per-turn with the `ultrathink` keyword. The dormant `fable` agent def is
  kept as the restoration target
- CLAUDE.md self-honesty checks: the Project Structure tree is verified
  path-by-path at gate time (a stale tree blocks the push naming the
  missing path — update it in the same commit that changes the
  structure), and an OntoGate adoption contract — considering OntoGate
  is recommended and highlighted in CLAUDE.md; once `ontogate:` in the
  stamp block names a gate, that gate must exist or the push blocks
- Minimal CLAUDE.md (community-consensus rules, 2026-06 research): trimmed
  231 → ~125 lines — only per-session facts and hard rules remain; all
  situational guidance moved verbatim to `context/AGENT_WORKFLOW.md`
  behind a Must-Know-Map pointer. CLAUDE.md now carries a dated review
  stamp (180-day horizon) validated by `scripts/check_skill_assumptions.py`
  alongside the food-chain block: when stale the gate recommends a review;
  the agent proposes edits, the human approves. Line-limit contradiction
  resolved: 250 everywhere
- Mandatory dependency CVE gate (decision 005 on meta): universal
  `make scan` target (Trivy on the RESOLVED dependency set — frozen env
  on Python, lockfiles elsewhere), diff-aware pre-commit trigger on
  manifest changes, always-on CI scan job + weekly cron, CRITICAL/HIGH
  blocking. Waivers only via `.trivyignore.yaml` entries carrying a
  justification and ≤90-day expiry; on findings the gate instructs the
  agent to explain each CVE in plain language so a human can ACTIVELY
  confirm any accepted risk; `make setup`/init verify the trivy
  toolchain and hard-fail with install instructions when absent
- `/fable-team` skill vendored into `.claude/skills/` plus a project-level
  `fable` agent definition (`.claude/agents/fable.md`) — every project
  templated or synced from this one inherits the tiered-team protocol
  (Haiku fast lane / coordinator / Fable judgment), self-contained, with a
  context-economy rule: interactions expected to exceed ~5k tokens are
  handed to subagents, recurring same-kind work to one persistent agent
- fable-team protocol amendments: the Fable teammate stays alive after
  deliverables (context watched, kept under ~50%, distill-to-memory +
  respawn when approaching); teammates are named `role--tier` (e.g.
  `advisor--fable`, `test-runner--haiku`) so the agent list reads at a
  glance; and the skill challenges at invocation when the coordinator
  is not Opus-tier (explicit confirmation before inverse mode)
- Food-chain self-revalidation: the skill carries a dated, machine-checked
  assumptions block (who sits at the top of the model food chain);
  `scripts/check_skill_assumptions.py` (exit 0 fresh / 1 review
  recommended / 2 block broken) runs in the pre-push governance gate, and
  the skill instructs the coordinator to sanity-check the tier map at
  every invocation and RECOMMEND — never silently apply — a new food chain
- `githooks/pre-push` — the synchronous-adoption gate (Flavor Spine axiom
  F9, decision 004 on meta): in repos carrying a governed meta branch, the
  OntoGate gate must pass against LOCAL branches before any push, so a
  universal change and its merges into every flavor travel in one push set;
  silent no-op in stamped projects

### Changed
- RECOMMENDED_WAYS_OF_WORKING: OntoGate entry updated for vpath-ontogate
  0.2.0 — the method now ships as a versioned pip package with the ADOPT.md
  self-verifying agent runbook; README gains the interpreter-probe note
  (broken-python3 field case)
- LICENSE.TXT is now sync-TRACKED (field decision after the vpath_agents
  migration surfaced a stale 2024 copyright): pristine licenses auto-update;
  projects with a different license remove the TRACKED entry once
- README: sync exit-code semantics documented (1 = review pending, not an
  error); the 1-2 permanent "customized" entries of a personalized project
  declared normal and by design; `python3` used consistently
- context/CHECKLIST.md Gate-1 comment generalized (was Python-specific in a
  universal file — found by the Java field build)

### Added
- README "Two Ways to Work With This Repository": consumer mode (stamp +
  sync, no governance knowledge needed) vs maintainer mode (meta branch,
  EVOLUTION.md handbook)
- Enforcement hooks — the gate is now machinery, not discipline: committed
  `githooks/pre-commit` runs `make check` before every commit (activated by
  `make setup` / init script); `.claude/settings.json` +
  `.claude/hooks/post_edit_check.py` quality-check every AI edit immediately
  (flavor-aware: black/flake8 for .py, spotless for .java) and feed failures
  back to the assistant; both universal across flavors and synced to derived
  projects (`githooks/` added to TRACKED)
- Branch-per-flavor architecture (researched, decision 002 on meta): flavors
  are branches of this repo; `.template-version` now stamps `<sha> <ref>` and
  the sync/drift scripts default to the stamped flavor ref; the CI workflow
  is tracked as a directory so each flavor's workflow syncs correctly
- `context/FLAVORS.md`: the language-flavor boundary — what is universal
  (skills, gates, conventions, sync tooling) vs Python-specific, with a
  per-language substitution table (Java, Rust, C++) for manifest, layout,
  formatter/linter/test, the `make check` gate, CI matrix, and the
  TRACKED-list adjustments flavor projects need
- `context/RECOMMENDED_WAYS_OF_WORKING.md`: promoted-but-not-enforced
  practices (Gradle for dependency/build orchestration, OntoGate for
  ontology-gated stabilization), linked from the README; the inline
  OntoGate section moved there
- Tests for the template scripts (`tests/test_template_scripts.py`): all five
  sync classifications, apply behavior, 3-way merge, branch isolation —
  against a real miniature git history, no network
- `context/MAIN_META_CONVENTION.md`: two-tier rule for evolution artifacts
  (libraries: `docs/adr` on main; tree-is-product repos: `meta` orphan
  branch). This repo's own planning now lives on its `meta` branch.
- `scripts/sync_from_template.py`: pull template improvements into a derived
  project — auto-updates files whose content matches any historical template
  version (exact git-history match, rescues projects that missed many
  iterations), copies new files, deletes template-removed pristine files,
  and 3-way merges customized files via the `.template-version` stamp
- `scripts/check_template_drift.py`: compare a derived project against the
  current template; reports up-to-date / missing / differing tracked files
  (`--diff` shows diffs), exit 0 only when fully in sync
- README recommendation (not enforced) for OntoGate, VPath's
  ontology-gated engineering method, with repository link

## [0.1.0] - 2026-06-10

### Added
- Initial template: src-layout package with placeholder module, pytest suite,
  strict CI gate (black/flake8/mypy/pytest on Python 3.10-3.13)
- First-class AI skills under `.claude/skills/` and `CLAUDE.md` agent guide
- Best-practice references and the canonical checklist under `context/`
