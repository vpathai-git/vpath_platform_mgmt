# Recommended Ways of Working

Recommendations VPath promotes for projects grown from this template.
**Recommended, not enforced** — unlike `context/CHECKLIST.md` (the mandatory
gates), these are directions we encourage you to adopt when the project's
shape calls for them. Each entry says what, why, and when it applies.

## 1. Manage dependencies and build orchestration with Gradle

**What:** Use [Gradle](https://gradle.org/) as the dependency-management and
build-orchestration layer, with Python tooling (pip/venv, the `make check`
gate) invoked from Gradle tasks rather than replaced by them.

**Why:** VPath's platform already runs on Gradle pipelines (build, deploy,
verification tiers). One orchestrator across polyglot components means one
task vocabulary, one dependency graph, one cache strategy — instead of a
Makefile here, npm scripts there, and shell glue in between. Gradle's
incremental builds and task dependencies also give AI agents a single,
inspectable entry point for "build everything that needs building."

**When it applies:** As soon as a project grows beyond a single Python
package — multiple components, generated artifacts, deployment steps, or
anything that must compose into the VPath platform pipeline. A single-module
library is fine on the template's Makefile alone.

## 2. Stabilize with OntoGate — ontology hooks on change

**What:** Adopt [OntoGate](https://github.com/vpathai-git/vpath_ontogate),
VPath's method for ontology-gated engineering, and add its hooks as the
project matures: the system's conceptual model (the *ontology*) becomes the
active gatekeeper of change. Every use case is written as a story composed
from the model's entities; a one-second checker verifies that changes compose
cleanly; anything that doesn't fit is either rejected or the model is
extended deliberately and on record.

**How (since vpath-ontogate 0.2.0):** the method ships as a versioned,
zero-runtime-dependency pip package with a self-verifying agent runbook —
point an agent at the ontogate checkout and `ADOPT.md` walks it through
interpreter probe-and-pin, package install, skill import, Spine authoring
and the first gate run, each step with its own verification. Your Spine
pins `model.method_version`, so method upgrades are visible, diffable
events. In governed repos the pre-push gate run also executes
`scripts/check_skill_assumptions.py`, which revalidates dated assumptions
that vendored skills carry (currently: the fable-team food chain) — its
exit 1 means "review recommended", never a blocked push.

**Why:** Systems rot by accumulation — the same problems solved differently
in different places until no one, human or AI, can say what the system *is*.
Documentation describes and drifts; OntoGate's ontology is checkable, so it
cannot silently drift. Human and AI contributors work against one explicit
picture of the system, and the gate catches structural misfits at
change-time instead of review-time.

**When it applies:** When the project develops a real domain model — more
than a handful of entities, multiple contributors (human or agent), or
recurring "we solved this differently over there" moments. Start with the
ontology and storybook; add the checker hooks once the model holds.

## 3. Working discipline for AI agents

**What:** A small set of working-process habits we ask AI agents (and humans) to
keep in this project — recommendations, not hard gates:
- **Verify before claiming** — don't report "done/fixed/works" without showing the
  real command output or a read screenshot; reproduce the failure, fix it, show it gone.
- **Stay in scope** — touch only the files the task names; treat "leave it / don't
  touch" as a boundary for the whole session; report adjacent issues instead of fixing
  them unasked.
- **Smallest correct solution** — build exactly what the task asks; surface anything
  extra as a proposal.
- **Reproduce ≠ fix** — when asked to analyze/reproduce, diagnose and stop; don't edit
  until told to fix.
- **Confirm before expensive or irreversible actions** — full rebuild/reinstall,
  publish/deploy, bulk delete, history rewrite: name the cheapest sufficient alternative
  and get a go first. (Routine commits are fine.)
- **Ask only when genuinely uncertain** — push through on unambiguous reversible work;
  reserve questions for truly ambiguous or high-stakes calls.
- **Bounded subagents** — spawn one only on explicit request, each with a stated
  upper bound and a named model.

**Why:** These habits keep agent work trustworthy and cheap — they head off the two
recurring failure modes (claiming success that isn't real, and doing more or other than
was asked) without adding ceremony to ordinary work.

**When it applies:** Always, for any agent or contributor in the repo. If one of these
must be enforced rather than encouraged, promote it to `context/CHECKLIST.md` with a gate.

## 4. Reporting style — the CTO briefing and a standing footer

**What:** Wire your reporting preferences into your personal `~/.claude/CLAUDE.md` so
agents brief you consistently. The house defaults: a fact-based **CTO briefing** on
demand (the `/plain-summary` skill — status-first, self-contained, ending in pickable
A/B/C options) and a short standing **footer** at the end of every reply. VPath debriefs
are forwarded to German-speaking decision-makers, so the footer is written **in German**
(a *Kurzstand*), even when the rest of the reply is English.

**Why:** A predictable status-first briefing lets a busy decision-maker see where things
stand in seconds, and a standing footer keeps the thread between turns — without them you
re-ask "where are we" every session.

**When it applies:** Any project where an agent reports progress to you. The skill lives
in `.claude/skills/plain-summary/` (committed, shared); the always-on footer and its
language are personal, so they belong in your global `~/.claude/CLAUDE.md`, not in a
committed project file.

## 5. Minimalism audits — hunt over-engineering on demand

**What:** A read-only over-engineering scan, the `/ponytail-audit` skill. It flags code
minimalism could remove — bloat, reinvented stdlib/native features, speculative
abstractions — over the working diff by default, or the whole repo with `--repo`, and
prints tagged one-line findings ending in `net: -N lines possible.` It is advisory: it
reports, never edits, and is never a gate (LLM judgment is not deterministic). The
minimalism doctrine it serves (the YAGNI ladder) is itself a hard rule — see `CLAUDE.md`
and `context/best_practices_short.md`; adopted from ponytail (MIT) under Decision 006.

**Why:** AI agents over-produce — extra options, needless layers, hand-rolled code the
stdlib already has. A periodic minimalism pass keeps a codebase honest without making
"write less" a blunt gate that would cut tests or guards.

**When it applies:** Any project. Run it before committing a sizable change, or
periodically across the repo. It never proposes removing a required regression test or a
trust-boundary guard. A deterministic minimalism gate would be a different tool — this one
stays advisory by design.

## 6. Context visibility — an optional status line + agent hook

**What:** A compact, colour-coded Claude Code status line showing live
context-window fill, generation speed, and the contexts of any spawned
teammates — so context exhaustion and auto-compaction stop arriving
unannounced. A companion `UserPromptSubmit` hook reports the same real fill
back into Claude's own context each turn, so the agent reads its budget
instead of self-estimating. The init script (`scripts/init_project.py`)
offers to install both; the bundled scripts are
`scripts/assets/statusline-context.sh` and `scripts/assets/context-report.sh`.

**Why:** Claude Code surfaces context fill only on demand (`/context`), and
the model has no native sense of its own budget (Opus 4.8 does not
self-track). During long or multi-agent sessions a persistent indicator is
the difference between steering and being surprised — and feeding the same
figure to the agent lets it compact deliberately rather than guess. The
figures are the same client-side numbers `/context` uses — accurate, not
estimated.

**When it applies:** Any project, but **opt-in only**. It writes to your
GLOBAL `~/.claude/` (two scripts plus a `statusLine` key and a
`UserPromptSubmit` hook in `settings.json`),
affecting every project — the same blast radius as the personal global
preferences in §4. So it is offered with an explicit prompt, default skip,
nothing written without consent, and it prints what changed and how to undo
it (Decision 007). The status-line script needs bash + `jq`
(macOS/Linux/WSL; `tmux` for the teammate block); the install logic itself
is cross-platform.

## 7. Completion chime — an optional turn-finished signal

**What:** A short audible completion signal when an agent turn finishes. Claude
Code installs it as a prompted global `Stop` hook in `~/.claude/settings.json`;
Codex wires the same project asset from `.codex/hooks.json`. Both paths call
`scripts/assets/completion-chime.sh`, which defaults to the macOS
`/System/Library/Sounds/Glass.aiff` sound.

**Why:** Long agent turns often finish while the human is reading or working
elsewhere. The chime is the audible sibling of the context-visibility feature:
small UX instrumentation that reduces polling the terminal and makes agent
completion observable without changing project behavior.

**When it applies:** Any local interactive workflow where an audible completion
signal is useful. Claude installation is opt-in because it writes to the global
Claude settings and affects every project. Codex uses the checked-in project
hook and therefore follows Codex's normal project-hook trust review. The
current implementation is macOS-oriented because it uses `afplay`; unsupported
systems fail loudly rather than pretending a sound was played.

---

Adding a recommendation? One entry per practice: what / why / when it
applies, with a link. If it becomes mandatory, it moves to
`context/CHECKLIST.md` and gets enforced by tooling instead.
