---
name: decide-next
description: Tech-exec status briefing + one-by-one decision triage. Use when a session has accumulated multiple open decisions that block further autonomous work — produces a self-contained status summary, walks the user through each decision sequentially via AskUserQuestion (topic → question → consequences → recommendation), validates the chosen answers for contradictions, and writes a concrete next-direction plan.
---

# Decide Next — Tech-Exec Decision Triage

Use this skill at a natural session boundary, when:
- Multiple open decisions have accumulated and you cannot proceed without input
- Or the user explicitly invokes `/decide-next`

Do **not** use it for single-decision moments (just ask directly), or to
confirm actions you could safely take alone.

## Arguments

None required. Optional natural-language hint for scope (e.g. "just the
refactor track", "include uncommitted changes"). Default: everything
the assistant believes is currently blocking next steps.

## Procedure

### 1 — Gather state (self-contained briefing inputs)

Read the project state so the briefing reads correctly to someone who
did NOT see the session. Sources, in order:

- `git status --short` and `git diff --stat`
- `git log -10 --oneline`
- The project's planning/tracking docs, if any (e.g. `docs/`, `TODO.md`,
  open issue list, roadmap files)
- Any recent failure output (test runs, CI logs, error logs)
- Untracked top-level docs created this session

If gathering takes more than ~6 tool calls, delegate to an `Explore`
subagent with a tight prompt — do not let context bloat with raw output.

### 2 — Produce the tech-exec briefing

Print **4 to 10 lines**, plain prose, no headers. Cover:

- One sentence: what changed in this session.
- One sentence: what is broken or degraded (with file paths or component
  names — no vague "issues").
- Numbered list: the decisions that need human input. Just titles here,
  not the full question. The list cap is **6** — if more, group them.
- One closing sentence stating total decisions queued and estimated time
  to answer (5-15 sec each, so "≈ 1 minute" is realistic for 4 decisions).

Tone: tech-exec register. Complete sentences. No jargon shorthand from
session context ("the W2a thing", "the basePath bug"). No emojis. The
user must be able to read this cold and orient.

### 3 — Identify the decisions precisely

For each decision listed in step 2, prepare internally:

- **Topic** — one sentence, the thing under decision
- **Options** — 2 to 4 mutually exclusive choices
- **Consequences** — one short sentence per option, what happens if chosen
- **Recommendation** — one option marked, with one-line rationale

A real decision is something where:
- The assistant genuinely cannot proceed without input, AND
- The wrong choice has non-trivial cost to reverse

If a "decision" fails either gate, drop it. Do not manufacture decisions.
If after pruning there are zero real decisions, say so explicitly in
the briefing and exit the skill without asking anything.

### 4 — Ask one question at a time

Use the `AskUserQuestion` tool. **One question per tool call.** Do not
batch into a 4-question form — the user explicitly wants sequential.

Each call:

```
question:    Full sentence framing the topic.
             Lead with one-line context so the question stands alone,
             then the ask.
             Example: "The release build failed on the packaging step
             and the staging environment is gone. How do you want to
             proceed?"

header:      ≤ 12 chars label (e.g. "Release", "Commit plan")

options:     2-4 entries. Format:
  - label:        ≤ 5 words. Mark first option "<text> (Recommended)"
                  only if there is a clear recommendation.
  - description:  One sentence: the consequence + tradeoff.
                  Example: "Rebuilds staging from scratch (~30 min);
                  resolves env state but blocks other work."

multiSelect: false  (unless options are genuinely non-exclusive)
```

Do NOT add an "Other" option — the harness adds it automatically.

After each answer, before asking the next:
- Note the choice internally (running tally).
- If the answer rules out an upcoming decision, drop that decision and
  move on. Do not ask a question whose premise just got invalidated.
- If the answer adds a new decision (a fork in the chosen path),
  insert it next.

### 5 — Coherence check

After all answers are collected, look for contradictions:

- Two answers that require incompatible system states
- A choice that requires resources another choice ruled out
- A timeline that doesn't fit the sequence
- A "do X first" answer paired with "skip the prerequisite for X"

If contradictions exist, surface them with **one** follow-up
`AskUserQuestion` that quotes both prior answers verbatim and asks the
user to resolve. Do not silently reconcile.

If no contradictions, proceed to step 6.

### 6 — Direction summary

Print **5 to 12 lines** of plain prose:

- The chosen path in execution order, numbered
- Per step: who acts (assistant / user / external) and what dependency
  it has
- Anything explicitly deferred — including why and when it returns
- Any decision the user picked AGAINST the recommendation — call it out
  once, neutrally, then move on (do not relitigate)

End with **one** concrete next-action sentence: what the assistant does
the moment the user replies, or what the user does next if action is
on them.

## What this skill is NOT

- A planning tool — no plan file is written.
- A status dashboard — the briefing is preamble for the questions, not
  the deliverable.
- A way to delegate decisions the assistant could safely make alone.
- A batched form — questions are strictly sequential.
- A re-prompt loop — if the user picks an unexpected option, accept it.

## Tone

Tech-exec register. Complete sentences. Flat statements over hedges
("Rebuilds the environment" not "Probably would rebuild the environment").
Concrete numbers ("~30 min", "2 files", "blocks steps 4-6") over
qualifiers ("a while", "some files", "downstream work").

No emojis. No "let me", "I'll go ahead and", "great question". The user
is busy. Each option description should be answerable in 5-15 seconds.

## Failure modes to avoid

- **Manufactured decisions.** If you don't have a real fork, end the
  skill. Don't ask filler questions to look thorough.
- **Stale context creep.** The briefing must be readable cold. If you
  catch yourself writing "as we discussed earlier" — rewrite.
- **Recommendation-stuffing.** Only mark one option recommended if
  there is a clear best choice. If three options are equally
  defensible, recommend none.
- **Asking permission for trivia.** "Should I commit the doc file?"
  is not a decision — just commit it or don't, with reasoning.
- **Re-asking after pivot.** If an answer invalidates a later question,
  drop that question. Do not ask it anyway for completeness.
