# Python Framework Best Practices — Condensed Principles

The 48 principles from `GENERAL_BEST_PRACTICES_FOR_PYTHON_FRAMEWORKS.md`, one
line each. These are design principles to internalize; for the operational
checklists (definition of done, commit, release), use `context/CHECKLIST.md`.
The minimalism ladder at the end (Decision 006) is an adopted addition, not
part of the mirrored 48.

## Part I: Foundation & Setup

**1. Project Structure**: Follow standard Python layout - `src/package/`, `tests/`, `docs/`, with `pyproject.toml` at root. Instant familiarity matters.

**2. Tooling Enforcement**: Run Black, Ruff/Flake8, mypy in CI. Use pre-commit hooks. Quality must be automatic, not optional.

## Part II: API Design

**3. Flat API**: Common tasks accessible via `import mylib; mylib.do_thing()` without navigating module hierarchies.

**4. Consistent Naming**: Use predictable patterns (`dump/load` for files, `dumps/loads` for strings) - users should guess function names correctly.

**5. No Boilerplate**: Simple functions for simple tasks. Don't force classes when `def process(data)` suffices. See pytest vs unittest.

**6. Self-Documentation**: Every public function needs docstrings with type hints. Control public API with `__all__`. Make `help()` useful.

**7. Pythonic Objects**: Implement `__len__`, `__getitem__`, `__repr__` to make objects work with `len()`, `[]`, and debugging naturally.

## Part III: Predictable Behavior

**8. Hide Complexity**: Users shouldn't handle encoding/decoding, session management, or retries manually. Abstract the plumbing.

**9. Rich Return Objects**: Return objects with `.status_code`, `.data` attributes, not tuples requiring position memory.

**10. Simple On-Ramp**: Provide one high-level function with sensible defaults before exposing complex configuration.

**11. Command-Query Separation**: Functions either change state OR return data, never both. No `list.pop()` patterns.

## Part IV: Robustness

**12. Design by Contract**: Validate inputs immediately (fail-fast), document what methods guarantee. Check preconditions aggressively.

**13. No Global Config**: Configuration via instantiation `Client(config=...)`, not global state. Allow multiple configurations simultaneously.

**14. Immutability**: Use `@dataclass(frozen=True)`. Objects that can't change are simpler to reason about and thread-safe.

**15. Composition Over Inheritance**: Hold references and delegate rather than inherit. Behavior changeable at runtime.

**16. Extensibility Points**: Provide Strategy/Adapter patterns for power users without complicating the main API.

## Part V: Documentation & Versioning

**17. Layer Documentation**: Provide Quickstart (5 min), Tutorials (30 min), How-to Guides (task-focused), API Reference (complete).

**18. Document Non-Goals**: Explicitly state what the library won't do and why it exists. Manage expectations.

**19. Semantic Versioning**: Breaking changes only in major versions. Use `DeprecationWarning` with clear migration path.

## Part VI: SDK Specifics

**20. Authentication Chain**: Check in order: explicit parameter → environment variable → config file. Never make users hunt for where to put credentials.

**21. Exception Hierarchy**: Specific errors (`RateLimitError`, `AuthenticationError`) not generic ones. Enable precise error handling.

**22. Network Resilience**: Default timeouts (never hang forever), automatic retries with exponential backoff for transient errors.

**23. Sync + Async**: Provide both `Client` and `AsyncClient` with identical APIs. Modern Python needs both.

**24. Include CLI**: Ship a command-line tool for quick testing and exploration without writing code.

## Part VII: Quality & Operations

**25. Performance**: Profile before optimizing. Provide benchmarks. Make speed/accuracy tradeoffs configurable.

**26. Community**: Clear CONTRIBUTING.md, issue templates, responsive maintenance builds trust.

**27. Handle Scale**: Abstract pagination with generators, support batch operations, enable streaming for large responses.

**28. Security First**: Never log secrets, validate all inputs, use secure defaults, run security scans in CI.

**29. Test Coverage**: Aim for 90%+. Every feature needs tests. Provide test fixtures/mocks for users testing their integrations.

**30. Dependency Hygiene**: Minimal core dependencies, use `extras_require` for optional features. Test on multiple Python versions.

**31. Observable**: Integrate with standard `logging`, make verbosity configurable, support distributed tracing if applicable.

## Part VIII: AI-Friendly Code

**32. Small Modules**: Keep files under 250 lines. AI context windows are limited; huge files are unprocessable.

**33. Linear Logic**: Main flows should read top-to-bottom without nested conditions. Hide complexity in well-named functions.

**34. Explicit Control Flow**: Direct function calls over event emitters. Static analysis must trace execution paths.

**35. Static Data Structures**: Use dataclasses/Pydantic models not dicts with magic string keys. Make structure visible.

**36. Formal State Machines**: When state is needed, use enums and explicit transitions, not ad-hoc boolean flags.

**37. No Runtime Patching**: Never monkeypatch in production code. What you see in source must be what executes.

**38. Fail Loudly**: Raise specific exceptions immediately. Silent failures make debugging impossible.

## Part IX: Core Philosophy

**39. Boring Over Clever**: If choosing between a clever one-liner and a simple loop, pick the one a junior dev understands.

**40. One Concept = One Place**: Each domain concept maps to exactly one module/class. No "God objects", no logic scattered across files.

**41. Design for Deletion**: Features should be removable by deleting one module and removing one integration point. Low coupling is mandatory.

## Part X: AI-Assisted Development Excellence

**42. Document Development Context**: Create `CLAUDE.md` files documenting bash commands, code style, testing instructions, and repository etiquette for consistent AI collaboration.

**43. Test-Driven Development First**: Write tests before implementation - AI can better understand requirements through tests and validate its own work.

**44. Progressive Thinking for Complexity**: Use graduated thinking modes for problems: simple tasks need no prefix, complex ones benefit from "think hard" or "ultrathink" directives.

**45. Visual Validation Loop**: For UI/visual work, take screenshots → implement → validate → iterate. AI needs visual feedback for accurate implementation.

**46. Permission-Aware Development**: Configure tool permissions appropriately - restrict system modifications in exploratory phases, enable for implementation.

**47. Context Management**: Clear context regularly in long sessions. Use git worktrees for parallel development without context pollution.

**48. Staged Task Execution**: Structure work as Explore → Plan → Implement → Validate. Each stage has different requirements and outputs.

## Adopted doctrine: the minimalism ladder (Decision 006)

Lazy-senior-dev minimalism, adopted from ponytail (MIT). The best code is the
code you never wrote. Before writing anything, climb DOWN the ladder and stop
at the first rung that works:

1. **Does it need to exist?** Skip the whole thing if not (YAGNI).
2. **Standard library?** Reach for stdlib before anything else.
3. **Native platform feature?** Prefer what the language/runtime already gives.
4. **Already an installed dependency?** Reuse it before adding a new one.
5. **One line?** Prefer the smallest expression that is still clear.
6. **Minimal necessary code** — only then, and no more.

Never simplify away: input validation at trust boundaries, error handling that
prevents data loss, security checks. "Write less" never cuts a guard.
Non-trivial logic still leaves one runnable regression check (see the test
hard rule in `CLAUDE.md`). Default intensity is judgment-applied, not
deletion-first extremism — use `/ponytail-audit` to hunt over-engineering on
demand.

## Health Check

The quick health-check questions moved to `context/CHECKLIST.md` (single
canonical checklist — no duplicates).