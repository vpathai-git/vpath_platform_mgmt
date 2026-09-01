# Makefile for common project commands
# Run 'make help' to see available commands

.PHONY: help install install-dev test test-verbose format lint type-check check credentials scan clean run setup

# Default target
help:
	@echo "Available commands:"
	@echo "  make setup        - Initial project setup (venv + dependencies)"
	@echo "  make install      - Install project dependencies"
	@echo "  make install-dev  - Install project with dev dependencies"
	@echo "  make test         - Run tests"
	@echo "  make test-verbose - Run tests with verbose output"
	@echo "  make format       - Format code with black"
	@echo "  make lint         - Run linting with flake8"
	@echo "  make type-check   - Run type checking with mypy"
	@echo "  make check        - Run the FULL quality gate (credentials + format + lint + types + tests, same as CI)"
	@echo "  make credentials  - Fail if a credential value can reach a log, a console or a tracked file"
	@echo "  make scan         - Scan resolved dependencies against latest CVEs (Trivy; blocks CRITICAL/HIGH)"
	@echo "  make clean        - Remove build artifacts and caches"
	@echo "  make run          - Run the placeholder module"

# Setup virtual environment, install dependencies, activate git hooks
setup:
	python -m venv venv
	git config core.hooksPath githooks
	python scripts/scan_dependencies.py --verify-only
	@echo "Git pre-commit hook activated (runs 'make check'; bypass: --no-verify)."
	@echo "Virtual environment created. Activate it with:"
	@echo "  source venv/bin/activate  (Linux/Mac)"
	@echo "  venv\\Scripts\\activate     (Windows)"
	@echo "Then run: make install-dev"

# Install production dependencies
install:
	pip install -r requirements.txt
	pip install -e .

# Install development dependencies
install-dev:
	pip install -r requirements.txt
	pip install -e ".[dev]"

# Run tests
test:
	pytest tests/

# Run tests with verbose output
test-verbose:
	pytest tests/ -v -s

# Format code with black
format:
	black src/ tests/ config/ scripts/

# Lint code with flake8
lint:
	flake8 src/ tests/ config/ scripts/ --max-line-length=88 --extend-ignore=E203

# Type check with mypy
type-check:
	mypy src/ config/ scripts/

# Credential gate — no secret value may reach a console, a log or a tracked
# file. Runs first: it is the cheapest step and the one with the worst failure
# mode. Point it at another checkout with --root to audit that tree.
credentials:
	python3 scripts/check_no_logged_credentials.py

# Full quality gate — identical to CI; all steps must pass
check:
	uv lock --check
	python3 scripts/check_no_logged_credentials.py
	black --check src/ tests/ config/ scripts/
	flake8 src/ tests/ config/ scripts/ --max-line-length=88 --extend-ignore=E203 --max-complexity=10
	mypy src/ config/ scripts/
	pytest tests/ --cov --cov-report=term-missing --cov-fail-under=85

# Mandatory dependency CVE gate (network-bound; NOT part of make check)
scan:
	python3 scripts/scan_dependencies.py

# Clean build artifacts and caches
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf build/ dist/ htmlcov/ .coverage

# Run the placeholder module (requires: pip install -e .)
run:
	python -m vpath_platform_mgmt
