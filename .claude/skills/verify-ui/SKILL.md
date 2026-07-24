---
name: verify-ui
description: Evidence-driven UI verification with Playwright — screenshots read and described, per-requirement PASS/FAIL/INCONCLUSIVE verdicts, no soft passes. Use when you must defensibly answer "does this user-visible feature actually work" before declaring a change done.
---

Verify user-visible behavior by driving a real browser, capturing evidence,
and READING it. This skill exists because "the test passed" is not the same as
"the feature works" — green Playwright runs give false positives through stale
bundles, auth redirects, spinners, and empty states that still satisfy
string-match assertions.

For browser mechanics (launching servers, writing Playwright scripts,
reconnaissance of selectors), use the companion `webapp-testing` skill in this
project — it has the `with_server.py` helper and the recon-then-action pattern.
This skill adds the verification discipline on top.

## When to use

- The user asks "does feature X really work" and will act on the answer
- Verifying a fix to a user-visible flow before declaring it done
- Investigating a reported UX bug, where the question is "what does the user see"

## When NOT to use

- API-only contract checks → plain pytest
- Pure code review → don't open a browser
- The change isn't deployed/served yet → start the app first (see `webapp-testing`)

## Core rules

### 1. Screenshot the post-condition, not the attempt

Before running, audit the script: does each screenshot capture the state the
claim depends on? "The app loads tickets" is NOT proven by a screenshot of a
`Loading...` spinner. Wait for the post-condition
(`expect(locator).to_be_visible()`, `wait_for_function(...)`), THEN screenshot.
Anti-patterns to refuse:

- Screenshot immediately after `page.goto()` — captures pre-hydration state
- `time.sleep(1)` instead of waiting on the post-condition
- Screenshot of the login page when the claim is about behavior after login
- A final "everything OK" screenshot with no data actually rendered

Always use `full_page=True` — viewport-only screenshots hide errors below the fold.

### 2. Read EVERY screenshot — and describe it in words

A screenshot you didn't describe is not evidence — it's a file. Read every PNG
via the Read tool (not only the final one; intermediate screenshots are where
regressions hide). For each, write one factual description of what is literally
visible:

```
screenshots/03_after_login.png
  Visible: header reads "Projects"; yellow banner "No resources bound";
  empty table with columns Name | Owner | Status; "+ New" button disabled.
  Matches claim? NO — claim was "projects load". This shows an empty state.
```

Forbidden phrasings (they restate the test result instead of reading pixels):
"page loaded ok", "screenshot looks fine", "no errors visible", "as expected".
Required: what the user would actually see — header text, button states, error
banners verbatim, row counts, any spinner/overlay/modal.

### 3. The verdict ties to the worst screenshot

If any screenshot shows a broken, empty, or loading state relevant to the
claim, the verdict is FAIL even if pytest said PASSED. Report the worst
screenshot as the headline finding.

### 4. Three verdicts only: PASS / FAIL / INCONCLUSIVE

Every requirement being verified gets exactly one. There is no "PASS with
caveats" and no "mostly works". If the evidence at hand can't support PASS or
FAIL, the verdict is INCONCLUSIVE — and you write down the specific question
that must be answered to resolve it. Never guess.

```markdown
### R-3: After saving, the item appears in the list
- Evidence: 04_after_save.png, console log, POST /api/items → 201
- Verdict: PASS
- Rationale: PNG shows the list with the new row "Test item" at position 1;
  network log line 14 shows the 201 with the new id.
```

### 5. Fail-hard test code

- Every check is an `assert` or `expect()` — never print a warning and continue
- No `try/except: pass`, no retry loops that mask flakiness, no mocks of real
  services in an E2E claim
- Selector hygiene: prefer `[data-testid=...]`, then `get_by_role()`/
  `get_by_text()`; never bare tag or CSS-class selectors
- Extract visible text with `page.evaluate("() => document.body.innerText")`,
  not `page.content()` (raw HTML is unreliable for text matching)
- Capture console + network during the run:
  `page.on("console", ...)`, `page.on("response", ...)`

### 6. On failure: capture, one recovery, move on

When a step fails, immediately capture the full state — screenshot, DOM
(`page.content()`), console log, and the network events so far. Then make ONE
recovery attempt (`page.reload()`), capture again, and move on. Do not retry
the same step repeatedly, and do not freelance (clear cookies, re-login,
URL surgery) — that pollutes the evidence. Mark dependent requirements
INCONCLUSIVE with `blocked: <failed requirement>`.

### 7. Stateful features need the round trip

For features that persist state, a one-shot "I clicked it once" is incomplete:

1. Clean slate (reset the state)
2. Observe pre-state in the UI (screenshot)
3. Mutate via the UI (screenshot the post-condition)
4. Reload → persistence check (state survives)
5. Revert the mutation
6. Reload → restoration check (UI returns to step 2 — catches cached lies)

If steps 4-6 weren't run, report persistence/restoration as INCONCLUSIVE.

## Workflow

1. Put exploration scripts in a task folder (e.g. `ui_exploration/<task-name>/`)
   with a `screenshots/` subfolder — keep them self-contained, out of the main
   test suite, and gitignored if ad-hoc
2. Write the script (see `webapp-testing` for mechanics), numbered screenshots
   at every significant step: `01_landing.png`, `02_after_login.png`, ...
3. Run it; read every screenshot; describe each per Rule 2
4. Report: verdict per requirement, the evidence cited, what works, what's
   broken (with a 1-2 sentence root-cause hypothesis, not a fix), and any
   open questions
5. Iterate in place until the investigation is complete — modify the script,
   don't proliferate files
