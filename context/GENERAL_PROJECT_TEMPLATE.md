# VPath Project Template Guidelines

All VPath projects must follow these conventions:

## Naming Convention
- **Project names**: Must start with `vpath_` prefix (e.g., `vpath_analytics`, `vpath_data_processor`)
- **Module names**: Must start with `vpath_` prefix (e.g., `vpath_core`, `vpath_utils`)
- **Package names in pyproject.toml**: Use hyphens instead of underscores (e.g., `vpath-analytics`)

## Project Structure
Every VPath project should include:
```
vpath_<project_name>/
   src/                   # Source code (src layout, no src/__init__.py)
      vpath_<module>/     # Main module (with vpath_ prefix)
   tests/                 # Test files
   config/                # Configuration files
   context/               # Best-practice docs, checklist, AI context
   scripts/               # Utility scripts
   .claude/skills/        # Installed Claude Code skills
   .codex/hooks.json      # Codex Stop hook adapter for completion chime
   .codex/skills -> .claude/skills
   .github/workflows/     # CI (strict gate: black + flake8 + mypy + pytest)
   pyproject.toml         # Package metadata + ALL tool config (source of truth)
   requirements.txt       # Runtime dependency mirror of pyproject
   Makefile               # Common commands (make check = full quality gate)
   AGENTS.md              # Shared repository governance for coding agents
   CLAUDE.md              # Claude Code adapter; imports AGENTS.md
   CHANGELOG.md           # Keep-a-Changelog format, SemVer policy
   CONTRIBUTING.md        # Contribution rules (conventional commits)
   .gitignore             # Git ignore rules
   .env.example           # Environment variables template
   README.md              # Project documentation
   LICENSE.TXT            # License file
```

`docs/`, `data/` and `logs/` are created on demand by `scripts/init_project.py`.

## Essential Files

### README.md
- Clear project description
- Quick start guide
- Installation instructions
- Usage examples
- Project structure overview

### pyproject.toml (single source of truth)
- Project name with `vpath-` prefix; version per Semantic Versioning
- Package discovery from `src/`
- Development dependencies in `[project.optional-dependencies] dev`
- Console scripts under `[project.scripts]`
- All tool configuration (black, isort, mypy, pytest, coverage)

### requirements.txt
- Mirror of `[project.dependencies]` for quick `pip install -r` — pyproject is canonical

### Makefile
Standard commands:
- `make setup` - Create virtual environment
- `make install` - Install dependencies
- `make install-dev` - Install with dev dependencies
- `make test` - Run tests
- `make format` - Format code
- `make lint` - Run linting
- `make check` - Full quality gate (format + lint + types + tests, same as CI)
- `make clean` - Clean artifacts
- `make run` - Run main module

### Agent governance
- `AGENTS.md` is the shared source of truth for project rules and pointers.
- `CLAUDE.md` imports `AGENTS.md` and carries only Claude-specific mechanics.
- `.codex/hooks.json` is the Codex adapter for the completion chime only.
- `.codex/skills` is a symlink to `.claude/skills`; Codex and Claude reuse the
  same shipped skills.
- `scripts/assets/completion-chime.sh` is the shared completion sound hook
  asset; Claude installs it globally by opt-in, Codex wires it project-locally.
- Tool-specific adapters must not duplicate or contradict `AGENTS.md`.

### .gitignore
- Python-specific ignores
- Virtual environment directories
- IDE files
- Build artifacts
- Environment files

### tests/
- Simple test structure
- `conftest.py` for pytest configuration
- Test files prefixed with `test_`
- Tests import the installed package (`vpath_<module>`), never via `src.`

## Placeholder Module
Each template includes `vpath_hello_world` as a minimal placeholder that:
- Simply prints "hello world"
- Demonstrates basic module structure
- Should be replaced with actual project code
- Can be run with `vpath-hello` (after installation) or `python -m vpath_hello_world`
- Includes `__main__.py` for direct module execution

## Configuration
- Use `config/settings.py` for configuration management
- Support environment variables via `.env` files (python-dotenv)
- Provide `.env.example` template

## Development Workflow
1. Clone/create project
2. Run `make setup` to create virtual environment
3. Activate virtual environment
4. Run `make install-dev` to install dependencies
5. Replace `vpath_hello_world` with actual code
6. Run `make check` to verify the full quality gate

## Best Practices
- Keep modules simple and focused; files under 250 lines
- Type hints on all public functions
- Write clear docstrings
- Follow PEP 8 style guide; Black for formatting
- Keep dependencies minimal
- Semantic Versioning + CHANGELOG.md for every user-facing change
- The single operational checklist lives in `context/CHECKLIST.md`
