# Contributing Guidelines

Thank you for your interest in contributing to this project! This document provides guidelines and instructions for contributing.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/yourusername/project.git`
3. Create a branch: `git checkout -b feature/your-feature-name`
4. Make your changes
5. Run the full quality gate: `make check`
6. Commit changes: `git commit -m "feat: add your meaningful change"`
7. Push to your fork: `git push origin feature/your-feature-name`
8. Create a Pull Request

## Development Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
make install-dev

# Run the full quality gate (formatting + lint + types + tests, same as CI)
make check

# Individual steps
make test     # tests only
make format   # apply black formatting
make lint     # flake8 only
```

## Code Style

- Follow PEP 8 Python style guide
- Use Black for code formatting (run `make format`)
- Use meaningful variable and function names
- Add type hints where appropriate
- Keep functions small and focused
- Write docstrings for all public functions and classes

## Testing

- Write tests for all new functionality
- Ensure all tests pass before submitting PR
- Aim for high test coverage
- Use pytest for testing

## Commit Messages

This project uses [Conventional Commits](https://www.conventionalcommits.org/)
(the `/careful-commit` skill enforces this format):

- Prefix: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`, `build:`, `ci:`
- First line: imperative mood, max ~72 characters
- One logical, independently revertable change per commit
- Body (optional, after a blank line) explains the WHY, not the what

Example:
```
feat: add user authentication

Sessions were previously unauthenticated, which blocked the multi-user
roadmap. Adds login/logout with hashed passwords and session management.
```

## Versioning and Changelog

This project follows [Semantic Versioning](https://semver.org/): breaking
changes bump MAJOR, features bump MINOR, fixes bump PATCH. Every user-facing
change adds a line to `CHANGELOG.md` under `[Unreleased]`. The release gate is
defined in `context/CHECKLIST.md` (Gate 3).

## Pull Request Process

1. Work through `context/CHECKLIST.md` Gate 1 (definition of done) and Gate 2 (commit hygiene)
2. Update README.md and `CHANGELOG.md` if the change is user-facing
3. Ensure CI is green
4. Request review from maintainers

## Questions?

Feel free to open an issue for any questions or concerns.