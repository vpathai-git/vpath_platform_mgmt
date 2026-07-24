---
name: fix-and-persist
description: Fix an issue durably — at the root, in the canonical location, swept across the codebase, gated by tests, and persisted in version control. Use when implementing a fix (especially after a /find-fix-for-good analysis), or whenever the user asks to "fix" something that must not come back.
---

Structured workflow for fixing an issue so it is durably integrated — not
patched on top, but addressed natively as if it was never an issue.

**No quickfixes. Ever.** Every fix that goes through this skill must be
production-grade. A quickfix that "works for now" becomes an outage next month.
The bar is: would you ship this fix to a user who runs the standard setup at
2 AM with no engineer on call?

## Arguments

The user describes the issue to fix. If a `/find-fix-for-good` analysis exists,
start from its recommended option.

## Workflow

### Phase 1: Understand

1. **Reproduce** — Confirm the issue exists. Show the error, log output, or
   broken behavior. Never fix what you haven't seen fail.
2. **Root-cause** — Trace to the exact file:line. Do NOT stop at symptoms. Ask:
   is this the root cause, or a downstream effect? Has this been worked around
   elsewhere? (Search for related patches, hacks, or TODO comments.)
3. **Scope** — What is affected? One module, several, the build, config, CI?
4. **Cross-platform** — If the fix touches file paths, subprocesses, or
   encodings: reason about BOTH macOS/Linux and Windows. Use `pathlib.Path`,
   `os.path.join()`, `encoding="utf-8"` — never hardcoded separators.

### Phase 2: Classify Ownership

Before designing the fix, decide WHO should own the concern:

| Layer | Owns | Fix goes here when... |
|-------|------|----------------------|
| **Shared library / framework code** | Behavior every module needs | Any new module would hit the same problem |
| **Configuration / schema** | Declared inputs, defaults, validation | The module forgot to declare something — or COULDN'T declare it (schema gap) |
| **Module code** | Business logic only | Only after ruling out the two above |

**The structural question:** "If I built a brand-new module following the
project conventions, would it have this same problem?"
- YES → the fix belongs in shared/framework code, not the module.
- Only if they forget to declare X → add validation or a sensible default.
- No, the module code is just wrong → fix the module.

If you're adding an `if name == "specific-thing"` special case, you're fixing
it in the wrong layer.

### Phase 3: Design

5. **Identify the canonical location** — config in `config/`, shared behavior
   in the shared package, build logic in the build files. If the fix is a patch
   to a random file that doesn't own the concern, STOP and redesign.
6. **Check architectural fit** — Is it consistent with how similar things are
   done elsewhere? Would someone reading this file for the first time
   understand why this is here? Would a new module automatically get this
   right, or would someone have to remember?
7. **Identify dependencies** — Does this fix invalidate caches, generated
   artifacts, or downstream steps? List everything that needs re-running.

### Phase 4: Implement

8. **Make the source change** — Edit the canonical file(s). The fix must be in
   version control so a fresh clone + standard setup applies it automatically.
   A manual command that patches the live system is NOT a fix.
9. **Sweep for the same pattern** — Search the ENTIRE codebase for the same
   anti-pattern before declaring done:
   ```bash
   grep -rn "<broken-pattern>" --include="*.py" --include="*.sh" --include="*.yml"
   ```
   Fix ALL instances, not just the one that triggered the failure. This is NOT
   optional — skipping it creates a whack-a-mole cycle where the same class of
   bug resurfaces one site at a time.
10. **Verify the fix live** — Run the previously-failing case. Show the output.

### Phase 5: Quality Gate (mandatory)

Every fix MUST pass all checks. A fix that fails any gate is NOT ready.

| # | Check | How | Fail means |
|---|-------|-----|-----------|
| 1 | **Syntax/static** | Run the project's lint + type check (`make check` or equivalent) | Fix introduced a new defect |
| 2 | **Unit** | Run ONLY the previously-failing test | Fix doesn't actually solve the problem |
| 3 | **Blast radius** | Run the FULL test suite | Fix broke something else |
| 4 | **Persistence** | Is the fix in version control AND applied by the standard setup path? | Band-aid that won't survive a fresh clone |
| 5 | **Cross-platform** | Paths/encoding/subprocess handled for macOS AND Windows? | Works here, breaks there |

### Phase 6: Regression Test

11. **Write a test that proves the fix** — It must fail if the fix is
    reverted, live in `tests/` where the suite collects it, and have a name
    that describes what it validates.
12. **Add a drift guard if the bug was structural** — a test that checks the
    INVARIANT, not the instance (e.g., "every module that declares X also has
    Y"), so the NEXT module can't reintroduce the bug.
13. **Verify the test runs in CI** — If it's not collected by the suite CI
    runs, it doesn't exist.

### Phase 7: Report

- **Issue:** one line
- **Root cause:** file:line and explanation
- **Ownership:** which layer owns the fix, and why there
- **Fix:** what changed, where
- **Sweep:** how many sibling instances were found and fixed
- **Test:** what regression guard was added
- **Confidence:** High/Medium/Low — and what would raise it if not High

## Critical Rules

1. **No fallbacks, no soft passes.** Never make a test less strict, never add
   `|| true`, never print WARNING and continue. Fail hard or fix it.
2. **The source change is the fix.** Live patches are transient verification
   steps, never the deliverable.
3. **One fix, all instances.** The sweep (step 9) is part of the definition of done.
4. **If uncertain, ask** — when the root cause is ambiguous, the fix touches
   shared infrastructure, or behavior others depend on might change.
