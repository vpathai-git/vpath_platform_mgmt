# Prompt-Level Advice — Storage, Edit/Recommend Flows, Targets

Where this project stores guidance for AI agents, how that guidance is
edited or recommended, and where it is aimed. A "single source of truth"
map for the advice surface itself — so the next person can see at a glance
that the same idea may live in more than one place, and why.

_This is a universal artifact (`context/`, `sync_class=universal`): it is
byte-identical on every flavor and OntoGate axiom F2 keeps it that way.
Consolidating the fragmentation it reveals is tracked on the `meta` branch
(`todos/015`), deliberately blocked until enough fleet experience exists to
consolidate against evidence rather than tidiness. Last mapped: 2026-06-28._

```
                         PROMPT-LEVEL ADVICE — STORAGE, EDIT/RECOMMEND FLOWS, TARGETS
                                       (vpath_empty_project)

 LEGEND   [U] universal · byte-identical on every flavor      --->  authored / edited (who writes)
          [E] edit_in_place · per-flavor, 3-way merged        ~~~>  gate / recommend (surfaces advice)
          [M] meta-only · NEVER ships (axiom F1)              ====>  target / propagation (where it lands)
          [L] machine-local · not in git


+- 1. WHERE ADVICE IS STORED --------------------------------------------------------------------+
|                                                                                                |
|  A) SHIPPING REPO  (main = Python  +  flavor/java)                                             |
|     +------------------------------------------+   +-----------------------------------------+ |
|     | AGENTS.md                          [E]   |   | context/                          [U]   | |
|     |   shared governance + project map         |   |  AGENT_WORKFLOW.md  (thinking modes)    | |
|     | CLAUDE.md                          [E]   |   |  best_practices_short.md  (#39 KISS)    | |
|     |   Claude adapter, @AGENTS.md import       |   |  GENERAL_BEST_PRACTICES_...             | |
|     |   <!--CLAUDE-MD-ASSUMPTIONS--> stamp      |   |  GENERAL_PROJECT_TEMPLATE.md            | |
|     +------------------------------------------+   |  CHECKLIST.md  FLAVORS.md               | |
|     | .claude/                           [U]   |   |  RECOMMENDED_WAYS_OF_WORKING.md         | |
|     |  skills/ (8): careful-commit decide-next |   |  MAIN_META_CONVENTION.md                | |
|     |    fable-team find-fix-for-good fix-and- |   |  ADVICE_MAP.md  (this file)             | |
|     |    persist plain-summary verify-ui       |   +-----------------------------------------+ |
|     |    webapp-testing  -> each SKILL.md       |   +-----------------------------------------+ |
|     |  agents/: advisor-opus.md · fable.md     |   | CONTRIBUTING.md  [U]  commit format     | |
|     |    (subagent system prompts; fable-team  |   | README.md        [E]  on-ramp           | |
|     |     SKILL.md carries <!--FOOD-CHAIN-->)   |   +-----------------------------------------+ |
|     |  settings.json (Claude edit hook)        |   .claude/agent-memory/<agent>/      [L]      |
|     | .codex/                            [U]   |     advisor-opus/  fable/(MEMORY.md +         |
|     |  hooks.json (Stop chime only)            |     project_*.md) — SUBAGENT-written,        |
|     |  skills -> ../.claude/skills             |                                               |
|     | scripts/agent_hooks/post_edit_check.py   |                                               |
|     | scripts/assets/completion-chime.sh       |                                               |
|     +------------------------------------------+                                             |
|                                                      not shipped                              |
|  B) META BRANCH  (orphan · "how to evolve" · axiom F1: never on a shipping branch)        [M] |
|     .ontogate/  ONTOLOGY.md STORYBOOK.md ontology.json usecases.json check.py PYTHON FINDINGS  |
|     EVOLUTION.md (maintainer handbook) · decisions/ · todos/ · analysis/ · reports/           |
|                                                                                                |
|  C) GLOBAL USER SCOPE  (~/.claude · machine-local, not in repo)                           [L] |
|     CLAUDE.md (private rules) · skills/ (superset incl. fable-team) · agents/ (advisor-opus,   |
|     fable)            (rules/: none)                                                           |
|                                                                                                |
|  D) AUTO-MEMORY  (~/.claude/projects/<repo>/memory/ · Claude-written, per-repo)           [L] |
|     MEMORY.md (index, 1st 200 lines auto-loaded) · topic files                                 |
|                                                                                                |
|  E) MANAGED / POLICY  (org: /Library/.../ClaudeCode/CLAUDE.md · managed-settings.claudeMd)     |
|     — a valid TARGET location, currently unused                                          [n/a] |
+------------------------------------------------------------------------------------------------+

+- 2. CONTROL FLOWS — TO EDIT (who changes the advice) ------------------------------------------+
|  human   ---> CLAUDE.md · SKILL.md · context/* · agents/* · CONTRIBUTING     (direct edit)     |
|  agent   ---> PROPOSES edit ---> human APPROVES  (dated-assumption rule: "agent proposes,      |
|               human approves; never silently rewrite" — CLAUDE.md stamp + food-chain block)    |
|  Claude  ---> writes AUTO-MEMORY itself (MEMORY.md / topic files)                              |
|  subagent---> writes its own .claude/agent-memory/<agent>/ (memory: project)                   |
|  universal edit ====> land on main ====> cherry-pick/merge into EVERY flavor ====> ONE push set|
|                       (F2 byte-identity + F9 synchronous adoption)                            |
+------------------------------------------------------------------------------------------------+

+- 3. CONTROL FLOWS — TO RECOMMEND / ENFORCE (gates that surface advice) ------------------------+
|  Claude Write|Edit ~~~> scripts/agent_hooks/post_edit_check.py -> quality-checks file, feeds   |
|                        failures back into Claude's turn (flavor-aware py/java)                 |
|  Codex Stop       ~~~> scripts/assets/completion-chime.sh -> audible turn-finished signal      |
|  on commit        ~~~> githooks/pre-commit -> make check (+ make scan if a manifest staged)    |
|  on push          ~~~> githooks/pre-push ->                                                    |
|                        • meta:.ontogate/check.py  (F1-F10; GATE OPEN/CLOSED)                   |
|                        • scripts/check_skill_assumptions.py ->                                 |
|                              exit1 = "REVALIDATION DUE" (push proceeds, REVIEW RECOMMENDED)    |
|                              exit2 = stamp missing/malformed (push BLOCKED)                    |
|                              also: CLAUDE.md structure-tree + OntoGate-adoption contract       |
|  on derived proj  ~~~> scripts/check_template_drift.py  -> reports stale advice (recommend sync)|
|  at /fable-team   ~~~> food-chain self-check -> RECOMMEND re-tier (human consents, never auto) |
|  in CLAUDE.md     ~~~> "task done 3+ times -> PROPOSE capturing it as a skill"                 |
+------------------------------------------------------------------------------------------------+

+- 4. WHERE IT AIMS TO PUT IT (targets) --------------------------------------------------------+
|  T1  LIVE SESSION CONTEXT  (load order, broadest->narrowest):                                  |
|        managed CLAUDE.md => ~/.claude/CLAUDE.md => ./CLAUDE.md -> @AGENTS.md => CLAUDE.local    |
|        + MEMORY.md (1st 200 ln) + skills on /invoke or relevance + context/* ONLY when a       |
|        Must-Know-Map pointer sends you there (nothing situational auto-loads)                  |
|  T2  SUBAGENTS (advisor-opus / fable) ====> get their agents/*.md system prompt; inherit NO    |
|        CLAUDE.md -> every handoff must RESTATE binding constraints                             |
|  T3  BOTH FLAVORS in this repo ====> universal advice byte-identical (main == flavor/java)     |
|  T4  DERIVED / STAMPED PROJECTS ====> inherit .claude/ + .codex/ + context/ + CONTRIBUTING     |
|        [U auto-update if pristine] and AGENTS.md/CLAUDE.md/README [E 3-way merge] via sync     |
|  T5  GLOBAL REUSE ====> fable-team skill + advisor-opus agent vendored to ~/.claude            |
|  T6  ORG/MANAGED ====> policy CLAUDE.md (available target, not used)                           |
+------------------------------------------------------------------------------------------------+
```

## In one line each

- **All storages:** repo-shipping (`AGENTS.md`, `CLAUDE.md`,
  `.claude/skills|agents|settings`, `.codex/hooks.json|skills`, `context/*`,
  `CONTRIBUTING.md`, `README.md`) + meta-governance (`.ontogate/`,
  `EVOLUTION.md`, `decisions/todos/analysis/reports`) + machine-local
  (`~/.claude/CLAUDE.md|skills|agents`, auto-memory `MEMORY.md`, subagent
  `agent-memory/`) + the unused org/managed slot.
- **Edit flows:** human-direct · agent-proposes/human-approves · Claude-auto-memory ·
  subagent-self-memory · universal-change → all-flavors → one-push-set.
- **Recommend/enforce flows:** Claude edit-check · Codex Stop chime · pre-commit · the pre-push
  OntoGate + skill-assumptions gates · drift checker · fable-team food-chain
  self-check · "capture as a skill" / OntoGate-adoption prompts.
- **Targets:** live session context (in load order) · subagents (no CLAUDE.md
  inheritance) · both flavors · derived projects via sync · the global scope ·
  org/managed policy.

## Two caveats worth knowing

1. **Machine-local advice is real but unshipped.** `.claude/agent-memory/` and
   `~/.claude/projects/<repo>/memory/` are agent/Claude-written and gitignored —
   they shape behaviour but never travel with the repo.
2. **Storage vs pointer.** Some advice lives where it is *enforced* (a hard rule
   in `CLAUDE.md`), some only where it is *referenced* (a principle in `context/`
   reached via the Must-Know Map). Example: "prefer the simplest solution" is in
   `context/best_practices_short.md` #39 and `RECOMMENDED_WAYS_OF_WORKING.md`,
   **not** a first-class `CLAUDE.md` hard rule. The closest CLAUDE.md rule is the
   scope rule "do exactly what was asked, nothing more."
