# Agent Workflow & Design-Principle Digest

Moved out of `CLAUDE.md` (2026-06-12) per the minimal-CLAUDE.md policy:
CLAUDE.md carries only per-session facts and hard rules; everything
situational lives behind a Must-Know-Map pointer. Read the section that
matches your task — none of this is loaded unless you come here.

## Thinking Modes

**Usage Guide:**
- No prefix: Simple, straightforward tasks
- `think`: Moderate complexity requiring analysis
- `think hard`: Complex problems needing deep consideration
- `ultrathink`: Architectural decisions with long-term impact

**Examples:**
```
Simple: "Fix the typo in line 42"
Think: "Refactor this function to be more testable"
Think hard: "Design a caching strategy for this API"
Ultrathink: "Architect a plugin system for extensibility"
```

## Context Management

### Session Best Practices
- Clear context after completing major features
- Use git worktrees for parallel development
- Take screenshots for visual validation
- Write tests before implementation

### Permission Management
- Use plan mode for exploration/design phases (read-only by design)
- Use `/permissions` to review or restrict tool access for careful sessions

## Working with Subagents

### When to Use Subagents
- **Testing Agent**: After implementation for comprehensive test generation
- **Refactoring Agent**: For code cleanup and optimization
- **Documentation Agent**: For creating user guides and API docs
- **Review Agent**: For code review and quality checks

For tiered delegation (Haiku fast lane / coordinator / Fable judgment),
context economy, and teammate naming, the `/fable-team` skill is the
authority.

### Subagent Invocation
```
"Spawn a testing agent to create comprehensive tests for [feature]"
"Use a refactoring agent to eliminate duplication in [module]"
"Create a documentation agent to write guides for [API]"
```

## Git Worktree Strategy

```bash
# Parallel feature development
git worktree add ../project-feature-a feature-a
git worktree add ../project-feature-b feature-b

# Hotfix while preserving context
git worktree add ../project-hotfix hotfix-branch
```

## Testing Strategy

### Test-First Development
1. **Write failing tests** that define desired behavior
2. **Implement minimal code** to make tests pass
3. **Refactor** while keeping tests green
4. **Add edge cases** and error conditions
5. **Document** complex test scenarios

### Test Organization
```python
tests/
├── unit/           # Fast, isolated tests
├── integration/    # Component interaction tests
├── e2e/           # End-to-end scenarios
└── fixtures/      # Shared test data
```

## Design-Principle Digest

The full references are `context/best_practices_short.md` (48 items) and
`context/GENERAL_BEST_PRACTICES_FOR_PYTHON_FRAMEWORKS.md`; these are the
headlines.

### Error Handling Patterns
- **Fail fast** - Validate inputs immediately
- **Specific exceptions** - Never catch bare Exception
- **Loud failures** - Always raise or log errors, never silent
- **Rich error messages** - Include context, expected vs actual

### State Management
- **No global state** - All configuration through class initialization
- **Immutable when possible** - Use `@dataclass(frozen=True)`
- **Explicit state transitions** - Use enums and methods, not flags

### API Design Principles
- **Flat is better** - Common operations accessible at top level
- **Rich returns** - Return objects with attributes, not tuples
- **Consistent naming** - dump/load for files, dumps/loads for strings
- **Progressive disclosure** - Simple things simple, complex things possible

### Security Considerations
- **Never log secrets** - Mask API keys, passwords, tokens
- **Validate all inputs** - Especially paths, URLs, user data
- **Secure defaults** - Require explicit opt-in for risky operations
- **No hardcoded credentials** - Use environment variables

### Performance Standards
- Profile before optimizing
- Lazy load expensive resources
- Provide batch operations where applicable
- Document any performance trade-offs

### Documentation Requirements
- Docstrings for all public APIs
- Type hints for all function signatures
- README must enable start in <5 minutes
- Examples for common use cases
