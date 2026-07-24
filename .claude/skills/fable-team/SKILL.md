---
name: fable-team
description: Run the session as a tiered team using the full model range — Haiku handles the fast, well-specified work (searches, fact checks, test runs, summaries, pipeline babysitting); the session agent (typically Opus) coordinates and executes the substantive work; a dedicated advisor (CURRENTLY a second, independent Opus instance — Fable temporarily unavailable as adversary) is brought in ONLY for deep planning handoffs, unsticking, conceptual/OntoGate work, refactorings/feature planning, and high-stakes review, kept in the loop with results-only briefs. Use when the user invokes /fable-team, says "bring in Fable", "fable team", or asks for advisor-tier planning/review on a task.
---

# Fable Team — tiered collaboration protocol

> **TEMPORARY SUBSTITUTION (set 2026-06-14): Fable is unavailable as the
> adversary.** Until restored, the judgment/advisor seat is held by a **second,
> independent Opus instance** (`advisor--opus`, `model: opus`) running at
> **`effort: max`**. Throughout this skill the judgment role is written as
> **"the advisor"**; for now that advisor is Opus, not Fable. Its leverage is
> *independence and dedicated adversarial attention* (a fresh mind, clean
> context, refute-first stance) — **not** a higher tier, since it is the same
> tier as the coordinator. To compensate for the missing tier, the advisor is
> pinned to **maximum reasoning effort** (`effort: max` in
> `.claude/agents/advisor-opus.md`, vendored with this project; a user-global
> `~/.claude/agents/advisor-opus.md` may also exist — project-level takes
> precedence): the depth it cannot get from tier it takes from reasoning
> budget. (`max` is the highest durable per-agent effort; the session-only
> `ultracode` mode is not frontmatter-settable — the coordinator reinforces
> per-turn with the `ultrathink` keyword in handoffs.) The food-chain block
> below records the substitution. **To restore Fable:** when Fable is
> available as an adversary again, put `fable` back in the judgment seat
> (`tier_judgment`, the tier map, the spawn target `advisor-opus` →
> `fable` / `advisor--opus` → `advisor--fable`, and drop the `effort: max`
> compensation if Fable's tier makes it unnecessary) and drop this banner. The
> dormant `fable` agent def (`.claude/agents/fable.md`, vendored here) is kept
> for that.

One rule governs everything in this skill: **the advisor thinks, the
coordinator does.** The advisor's value is judgment density and independence,
not throughput. Every call to the advisor must be a moment where judgment is
the bottleneck. If execution is the bottleneck, the advisor is the wrong tool.

You — the session agent — are the **coordinator**. You own the
conversation, all execution, all coordination detail, and the final
report to the user. The advisor never talks to the user directly; you relay
what matters.

## The tier map — use the full range

| Tier | Role | What flows there |
|---|---|---|
| **Haiku** | Fast hands | Easy, well-specified, low-risk work where speed beats depth (see the Haiku lane below) |
| **Coordinator** (session model, typically Opus) | Owner | Substantive implementation, integration, judging what flows up or down, everything user-facing |
| **Advisor** (2nd independent instance — currently Opus; normally Fable) | Judgment | Plans, architecture, refactorings, reviews, unsticking — decisions with long shadows |

Matching work to tier is itself coordinator judgment, and it cuts both
ways: sending easy work down is the same skill as sending heavy
decisions up. Neither direction is a statement about anyone's ability —
it's load-matching.

## Food chain — a dated assumption, not an eternal truth

The tier map above is a snapshot of the model lineup. It WILL go stale
when a new top-tier model ships, and it currently reflects a deliberate
temporary substitution (Fable → 2nd Opus in the judgment seat). The block
below is machine-checked (`scripts/check_skill_assumptions.py`, run by the
pre-push governance gate in governed repos):

<!-- FOOD-CHAIN-ASSUMPTIONS-BEGIN -->
```yaml
tier_judgment: opus            # TEMP substitution — Fable unavailable as adversary; 2nd Opus holds the seat
tier_coordinator: opus
tier_fast: haiku
agent_model_values: haiku, sonnet, opus, fable   # tool still offers `fable`; restore it to tier_judgment when available
top_of_chain: Fable 5 (Mythos-class tier, above Opus) — TEMPORARILY UNAVAILABLE as adversary
judgment_substitution: opus    # 2nd independent Opus instance; REMOVE this line + restore `fable` when available
judgment_effort: max           # advisor pinned to effort:max to compensate for the missing tier; drop with the substitution
validated: 2026-06-14
review_horizon_days: 180
```
<!-- FOOD-CHAIN-ASSUMPTIONS-END -->

**Self-check at invocation** (coordinator duty, every /fable-team
session): compare this block against what you can observe — your own
model identity and the model values your Agent tool accepts. A deliberate
temporary substitution is recorded above (`judgment_substitution`): while it
stands, `tier_judgment: opus` is INTENTIONAL and is not a mismatch — Fable is
deliberately benched as the adversary, not missing. If, beyond that, the tool
offers a value not listed here, or a tier above `fable` exists, or `validated`
is older than the horizon: tell the user, RECOMMEND the corrected food chain
(the highest available tier takes the judgment seat), and update this block —
both the tier map and the `validated:` date — only with the user's consent.
When Fable becomes available as an adversary again, recommend restoring it to
the judgment seat (and removing the substitution). Never silently re-tier;
never quietly keep using a map you can see is wrong. If everything matches the
recorded state and the date is fresh, proceed without ceremony.

Re-stamping = update the tier map table, this block, and (on machines
that carry one) the user-global copy at `~/.claude/skills/fable-team/`,
in the same change.

**Coordinator tier check** (same moment, before any work): this
protocol assumes an Opus-tier coordinator. Check your own model
identity at invocation. If you are NOT Opus-tier — e.g. the session
was started on Fable — do not silently proceed: challenge the user
first, along the lines of "You started me as Fable — the fable-team
design has Opus coordinating and the advisor reserved for judgment calls.
Are you sure?" (AskUserQuestion: continue as-is / restart on Opus).
Only on explicit confirmation continue — as inverse mode if the
session is a higher tier than the advisor seat (see below), or as a
knowingly down-tiered coordinator otherwise.

## When to call the advisor — exactly four triggers

1. **Plan handoff.** A non-trivial task arrives (multi-file, design
   choices to make, irreversibility, or unclear decomposition). Hand
   the task to the advisor BEFORE writing code; the advisor returns the
   plan, you execute it. Trivial tasks (single obvious change, mechanical
   sweep, well-trodden pattern) are planned and done by you alone.
2. **Stuck.** Two genuinely different approaches have failed, or the
   system's behavior contradicts your model of it, or you are about to
   choose between options whose consequences you cannot bound. Bring
   the evidence, not the frustration.
3. **Conceptual / OntoGate work.** Spine expression, demand
   expressibility ("is this expressible or does the Spine need to be
   extended?"), impact simulation, "does this compose?", architecture
   decisions, taxonomy/model design. This is judgment-dense by
   definition — always the advisor.
4. **High-stakes review.** Changes touching production data or vaults,
   irreversible or outward-facing operations, security-relevant code,
   or the final review of a major deliverable before the user sees it.
   Routine diffs do NOT qualify — review those yourself or with
   /code-review.

**Sustainability gravity.** Decisions with long shadows — greater
refactorings, changes with many dependents, feature planning, anything
of architectural importance — have natural gravity toward the advisor,
even when the coordinator could plausibly handle them. We work sustainably:
the cost of an advisor plan is trivial next to the cost of living with a
suboptimal structural decision. When in doubt about whether something
is architectural, it probably is.

**Never delegate to the advisor:** running tests or interpreting ordinary
test output, easy reviews, routine implementation, mechanical edits,
formatting, status checks, coordination details, retries, anything
whose answer you can verify cheaply yourself. Handholding test runs
through the advisor is precisely the failure mode this skill exists to
prevent — most of it belongs in the Haiku lane below, or with you.

**Gray zone?** If you genuinely cannot tell whether a task deserves
the advisor, ask the user with AskUserQuestion — one question, two options
("advisor handles it" / "I handle it"), with your recommendation first.
Do not ask when the triggers above already decide it.

## The Haiku lane — fast hands for easy work

Haiku is a genuinely capable tool-calling agent and very cheap — use it
wherever you want results fast and the work follows clear rules.
Delegate to Haiku (`Agent` with `model: "haiku"`):

- Web double-checks and simple fact verification
- Test runs with clearly pass/fail output
- Summarizations and reporting (e.g. "summarize what was just done")
- Finding things in the file system; broad searches
- Extracting information from files when the extraction follows simple
  rules
- Babysitting semi-stable pipelines — not complicated, just not yet
  stable enough to leave alone: watch, restart on known signatures,
  report anything novel
- Lower-priority research sweeps where speed matters more than depth

**Brief Haiku for good judgment, every time.** Each Haiku prompt must
make it aware of its place on the team and its escalation duty — in
this spirit, not as a warning label:

> You're the fast lane of a tiered team — your job is speed on
> well-specified work, and good judgment about its edges. If you hit
> surprises, ambiguity, or results that don't match what the task
> description led you to expect, stop and report back with what you
> found: the coordinator knows what to do with it, and escalating
> early is a success, not a failure. Rather ask than decide something
> suboptimal. Never invent URLs, citations, or facts — "not found" is
> a perfectly good answer.

**Coordinator-side handling:** Haiku output is fast and literal. Facts,
URLs, and citations sourced from Haiku get verified before they enter a
decision or a deliverable; judgment-dense research synthesis stays at
your tier or above. Haiku verifies and fetches — it does not conclude.

## Escalate on surprise — the rule at every tier

The same rule of thumb binds the whole team, in both directions: **when
solving a problem keeps producing surprises — you iterate and it's not
obvious what's going on — escalate rather than settle for a suboptimal
decision.** Haiku escalates to you; you escalate to the advisor. The
coordinator applies it to itself honestly: don't overestimate how well
you understand a problem that keeps surprising you — a string of
surprises is evidence the model of the problem is wrong, and getting a
deeper read at that moment is the efficient move, not the cautious one.
Rather ask than decide something suboptimal.

## The persistent advisor teammate

The advisor is one long-lived teammate, not a series of throwaway oracles.

- **Spawn lazily** at the first trigger of the session:
  `Agent(name: "advisor--opus", subagent_type: "advisor-opus", ...)` — the
  `advisor-opus` agent definition (`.claude/agents/advisor-opus.md`, vendored
  with this project; a user-global `~/.claude/agents/advisor-opus.md` may also
  exist — project-level takes precedence) pins `model: opus` and `effort: max`,
  makes it structurally read-only (no Write/Edit), and gives it persistent
  per-project memory. It is a SECOND, independent Opus instance standing in for
  Fable, run at maximum reasoning effort to compensate for the missing tier.
  Never spawn more than one advisor.
- **Reinforce max effort per turn.** The `effort: max` frontmatter pin is the
  durable mechanism; on top of it, include the `ultrathink` keyword in every
  handoff prompt and SendMessage to the advisor (plans, reviews, unsticking) —
  it is a recognized per-turn deep-reasoning trigger and costs nothing to add.
  This is the compensation for benching Fable; do not skip it.
- **No silent downgrade — tier OR effort.** If the teammate turns out not to be
  running at the advisor tier (currently Opus — capacity fallback, cap reached,
  model pin not honored) OR not at max effort (effort pin not honored, env var
  forcing a lower level), that is a loud failure: tell the user and do not
  present the answer as an advisor verdict. Never soft-pass a downgraded
  review. If the spawn fails because the `opus` model value or the `max`
  effort level is rejected or unavailable in this environment, that is the
  same loud failure — tell the user and proceed only on their explicit choice
  of substitute tier/effort.
- **The advisor cannot spawn subagents.** Hand it everything it needs to
  answer by reading; do not ask it to delegate or fan out.
- **Continue, never restart:** all later contact goes through
  `SendMessage(to: "advisor--opus")` so its context accumulates across
  the session. If SendMessage fails because the agent is gone, respawn
  it with a condensed catch-up brief and carry on.
- **Keep it in the loop on results, not process.** After completing a
  meaningful unit of work (a plan executed, a decision landed, a
  surprise discovered), send a brief. Batch — never ping per-step,
  never after every test run.
- **Keep the advisor alive after the deliverable.** Do not shut the teammate
  down when its work lands: the accumulated context is valuable — it
  stays available for questions and can continue thinking about
  adjacent or queued concerns once the implementation exists.
- **Watch its context window.** Keep the advisor's context below ~50%
  utilization. When it approaches the line, have it distill standing
  knowledge into its memory directory, then respawn fresh with a
  condensed catch-up brief — continuity lives in memory and briefs,
  not in a bloated context.

**Brief format** (≤10 lines, every time):

```
RESULT BRIEF <n>
Decided:  <decisions taken since last brief>
Built:    <what now exists, with file paths>
Verified: <what was checked and the verdict — one line, no logs>
Surprise: <anything that contradicted expectations, or "none">
Open:     <questions/risks still live, or "none">
```

Never send: test logs, stack traces from routine failures, diffs of
work-in-progress churn, coordination chatter, or anything you would
not put in a handoff to a senior architect.

## Handoff protocol (triggers 1–3)

An advisor handoff prompt must contain, in this order:

1. **Goal, verbatim** — the user's words, not your paraphrase.
2. **Binding constraints** — the rules that constrain the solution
   (e.g. no-fallbacks/zero-silent-degradation, license policy,
   OntoGate gating, <200-line Python files). The advisor inherits no
   CLAUDE.md; state what binds.
3. **Pointers, not pastes** — file paths and entry points. The advisor has
   tools; let it read.
4. **What was already tried** (stuck handoffs) — each approach, why it
   failed, the evidence.
5. **Deliverable spec** — for planning: a step-by-step plan with
   file-level actions, ordering, risks, verification criteria per
   step, and an explicit "what would make this plan wrong" section.

**Plan acceptance:** you must be able to execute the returned plan
without re-deriving it. If a step is ambiguous, push back via
SendMessage — do not improvise around it. Deviations you discover
during execution go into the next result brief.

**Review verdicts are binding:** reviews come back as PASS/FAIL with
blockers carrying `file:line` references. If the advisor flags a blocker in
a high-stakes review, it stays a blocker until resolved or explicitly
overruled by the user. No soft-passing an advisor finding.

**Plans are starting points, not contracts:** when execution hits a real
obstacle the plan didn't anticipate, stop and go back to the advisor with the
new information — over-trusting a stale plan is a named failure mode.
Never improvise around a plan that reality has contradicted.

## Non-blocking calls

When the advisor's answer does not block your next action (e.g. a review of
finished work while you start the next queued task), send the request
with `run_in_background: true` or via SendMessage and keep working on
independent items. Never sit idle waiting on the advisor when independent
work exists; never start dependent work before the answer arrives.

## Inverse mode — when the session outranks the advisor seat

Entered only after the coordinator tier check above — the user has
explicitly confirmed running with a coordinator at a higher tier than the
current advisor seat (e.g. a Fable-tier session while the advisor seat is a
2nd Opus). If the session model already outranks the advisor seat, do not
spawn a lower-tier advisor to second-guess it. The tiering inverts: you do
the judgment work (planning, conceptual, review, unsticking) inline, and
delegate the throughput work down the tier map — substantive implementation
to Opus/Sonnet, the Haiku lane to Haiku — via the Agent tool. Same principle,
opposite direction: the expensive mind plans and judges, the cheaper hands
execute.

## Context economy — expected token burn is a delegation dimension

Tier (difficulty) is not the only routing axis. Before doing work
inline, estimate its **context cost to you**: tool-calling boilerplate,
file dumps, retry churn, long command output. The coordinator's context
is the team's most expensive shared resource — keep it clean of
verbosity and hold the distilled results, not the transcripts.

- **Hand off above ~5,000 expected tokens of interaction.** If a unit
  of work will plausibly burn more than ~5,000 tokens of back-and-forth
  in your own context (certainly by 10,000), delegate it to a subagent
  even when you could do it inline — you receive the conclusion, the
  pollution stays in the subagent. Below that, the handoff overhead
  (briefing + relay) outweighs the saving; do it inline. Be reasonable,
  not dogmatic: a 4k-token job that might balloon is a handoff too.
- **Repetitive same-kind work gets ONE persistent agent.** When the
  same kind of request will recur (run-and-report cycles, repeated
  lookups, batch item processing), spawn a single long-lived agent once
  (`Agent` with a `name`) and feed it requests via `SendMessage` —
  its context accumulates the working knowledge; yours accumulates
  only the answers. Do not respawn per request, and do not let the
  briefing tax of N throwaway agents exceed what one running agent
  costs.
- **What comes back up must be distilled.** Subagents return
  conclusions sized to the decision they feed — never raw logs,
  full file contents, or play-by-play.

## Naming spawned teammates — role plus tier, always

Every spawned teammate is named after its ROLE with its model tier
visible in the name, so the list of open agents reads at a glance:
who is doing what, on which tier. Agent names cannot contain spaces
or brackets (harness constraint: letters, digits, `-`, `_` only), so
the tier marker is appended with a double hyphen:

    <role>--<tier>     e.g. advisor--opus, researcher--opus,
                            test-runner--haiku, pipeline-sitter--haiku

The role name does not need to be perfect — "the advisory guy" beats
an anonymous `agent-3`. The advisor teammate spawned by this skill is
canonically named `advisor--opus` (it would be `advisor--fable` once Fable
is restored to the judgment seat).

## Cost discipline

- One advisor teammate per session, lazily spawned.
- Batch result briefs; a brief is owed at unit-of-work boundaries, not
  on a timer.
- Each advisor call should be answerable in one shot from what you send
  plus what it can read — round-trips to fill gaps you could have
  stated up front are pure waste.
- When in doubt about whether a call is worth it, it usually is for
  triggers 2–4 and usually is not for anything resembling execution.
