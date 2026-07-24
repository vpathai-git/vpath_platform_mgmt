---
name: find-fix-for-good
description: Analyze a bug or failing test to its true root cause, validate the regression hypothesis with git evidence, check for systemic patterns, and produce rated fix options. Use BEFORE coding when a fix was already applied once and the problem came back, when a failure looks like a symptom of something deeper, or when the user asks for a root-cause analysis. No shortcuts.
---

Rigorous root cause analysis and permanent fix design. This skill exists because
most bugs are fixed 3 times before they stay fixed. The first fix addresses the
symptom. The second fix addresses the cause. The third fix addresses why the
cause was possible. This skill jumps to the third fix.

**This is not a coding skill. This is a thinking skill.** The output is a root
cause document with rated fix options. Coding happens AFTER the analysis is
approved — then use `/fix-and-persist` to implement.

## When to Use

- Tests are failing and you need to understand WHY before touching code
- A fix was applied but the problem came back (circular fix pattern)
- You suspect the failing test is a symptom of something deeper

## When NOT to Use

- The fix is obvious and mechanical (typo, wrong port number, missing import)
- You already completed the analysis and need to implement → use `/fix-and-persist`

## Arguments

A description of the issue, a failing test name, or a path to an issue ticket.

---

## Phase 1: Understand What Is Failing

1. **Reproduce and observe.** Run the failing test/command live with maximum
   verbosity. Capture the EXACT error: assertion text, stack trace, HTTP status,
   process state. Collect volatile evidence NOW (logs, env state).
   Output: a precise description of WHAT fails, not WHY. Separate observation
   from interpretation.

2. **Trace the failure chain.** Map the failure backward through the layers:

   ```
   Test assertion fails
     ↑ because the function returned X instead of Y
       ↑ because component Z is in state S
         ↑ because configuration/code at FILE:LINE says ...
   ```

   Keep going until you reach a line of code, a config value, or a missing
   resource. If you stop at "the service is crashing" — you haven't gone deep
   enough. WHY is it crashing?

3. **State the proximate cause** in one sentence:
   > "The test fails because [exact technical cause] at [file:line or resource]"

   This is NOT the root cause yet. This is the trigger.

## Phase 2: The Regression Hypothesis

**Core axiom: if it worked before, something we changed broke it.**
"It was always broken, we just never hit it" is NOT acceptable without proof.
The burden of proof is on the analyst to either identify the specific change
that caused the regression, or prove with git evidence that it never worked
(newly added test, removed `xfail`, etc.).

1. **Find the last known good state.** `git log --oneline -20`, CI history,
   `.pytest_cache/v/cache/lastfailed`.
2. **Identify the breaking change.** `git log --oneline -- <file-or-dir>` and
   `git diff <last-good>..HEAD -- <file-or-dir>`. If the file hasn't changed
   but the test broke, the cause is INDIRECT — a dependency, an environment, or
   an ordering changed. Trace that chain.
3. **Validate the hypothesis.** State it:
   > "This broke because [change X] at [commit] caused [effect Y] which makes
   > [component Z] fail when [condition]"

   Check: does reverting (conceptually) fix it? Does the timeline match? Did
   other tests affected by the same change also break?

If no regression cause is found, classify with evidence: **new test** (never
passed), **environment drift**, or **latent bug** (existed but masked).

## Phase 3: Neuralgic Area Check

**Has this code area been fixed before?** Fix-break cycles indicate a structural
problem, not a code problem. Search `git log --oneline --all -- <file>` and any
issue/analysis docs for prior fixes to the same component.

| Pattern | Sign | Action |
|---------|------|--------|
| First occurrence | No prior fixes in this area | Proceed with fix |
| Second occurrence | One prior fix, different root cause | Fix + add regression guard test |
| Third+ occurrence | Multiple fixes, same area | **STOP. This is a design problem.** |

If this is a third+ occurrence: list ALL prior fixes, identify the common
thread, and design a redesign of the mechanism — not another patch.

## Phase 4: Systemic Analysis

**Is this a symptom of something bigger?** Ask:

1. If I fix this specific instance, can the same CLASS of error occur elsewhere?
2. Is there a missing abstraction that would prevent this entire category of bug?
3. Would a new developer adding a new module hit this same problem?

If YES to any: the root cause is architectural. Run a cross-cutting scan —
`grep -rn "<error-or-anti-pattern>"` across the codebase — and list ALL
instances. They are part of the fix scope.

**If a systemic issue is found: do NOT proceed to fix options.** Present the
systemic finding to the user and discuss the architectural approach first.
Don't apply a bandaid to a broken bone.

## Phase 5: Project Principles Check

Every fix must respect the project's principles (see `CLAUDE.md`). Disqualifiers
— any one of these rejects an option outright:

- Adds a fallback path, soft pass, `|| true`, or `try/except: pass` (silent degradation)
- Makes a test less strict to get it green — the test is correct, the code is wrong
- Introduces a hardcoded credential or masks a security failure
- Requires a manual step that won't survive a fresh clone + standard setup
- Fixes one instance of a pattern while leaving known siblings broken

## Phase 6: Fix Options and Evaluation

Produce 2-3 fix options. For each:

```markdown
### Option N: <title>
**What:** <one-line description>
**Where:** <file(s) and line(s)>
**How:** <brief technical approach>
**Pros / Cons:** ...
**Scope:** N file(s), M test(s) affected
**Risk:** Low / Medium / High — <why>
**Fixes cross-cutting instances:** Yes (N) / No
**Prevents recurrence:** Yes — <how> / No — <why not>
```

Rate each option 1-5 on: **Permanence** (30% — survives the next 10 clean
rebuilds), **Scope completeness** (25% — fixes ALL instances), **Right layer**
(20% — owned by the component responsible for the concern), **Simplicity**
(15% — fewer changed files, less blast radius), **Testability** (10% — a
regression guard can catch recurrence). Compute the weighted score and
recommend the highest-scoring option.

## Phase 7: Output Document

Write the analysis into a markdown document (issue ticket, `docs/`, or a path
the user names): what fails, failure chain, proximate cause, regression source,
fix history, systemic assessment, cross-cutting instances, the rated options
table, the recommendation, and the regression guard to add.

**The document IS the deliverable.** An undocumented fix is an invisible fix.

## Critical Rules

1. **Think before you type.** 80% analysis, 20% code. Writing code in Phase 1-5 means you started too early.
2. **The regression hypothesis is mandatory.** "It was always broken" requires proof.
3. **Three strikes = design problem.** Third fix in the same area → stop patching, redesign.
4. **Cross-cutting scan is not optional.** Same pattern elsewhere is part of the fix scope.
5. **No fix without a regression guard.** If you can't write a test that catches recurrence, the fix is incomplete.
6. **Systemic findings block implementation.** Discuss architecture first.
