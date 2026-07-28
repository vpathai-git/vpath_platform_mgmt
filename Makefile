# Makefile for common project commands
# Run 'make help' to see available commands

.PHONY: help install install-dev test test-verbose format lint type-check check scan clean run setup \
        console console-install dist dist-python dist-console

# Where the Electron shell lives. It ships inside the package, so the console
# binary and the Python it drives are always the same version of one console.
CONSOLE_DIR := src/vpath_platform_mgmt/console/electron

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
	@echo "  make check        - Run the FULL quality gate (format + lint + types + tests, same as CI)"
	@echo "  make scan         - Scan resolved dependencies against latest CVEs (Trivy; blocks CRITICAL/HIGH)"
	@echo "  make clean        - Remove build artifacts and caches"
	@echo "  make run          - Run the placeholder module"
	@echo "  make console      - Run the management console from this checkout"
	@echo "  make console-install - Install the console shell's Node dependencies"
	@echo "  make dist         - Build BOTH distributables (Python wheel + console binary)"
	@echo "  make dist-python  - Build the Python wheel and sdist into dist/"
	@echo "  make dist-console - Build the console binary for THIS platform"

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

# Full quality gate — identical to CI; all steps must pass
check:
	black --check src/ tests/ config/ scripts/
	flake8 src/ tests/ config/ scripts/ --max-line-length=88 --extend-ignore=E203 --max-complexity=10
	mypy src/ config/ scripts/
	pytest tests/ --cov --cov-report=term-missing --cov-fail-under=85

# Mandatory dependency CVE gate (network-bound; NOT part of make check)
scan:
	python3 scripts/scan_dependencies.py

# --- the console -------------------------------------------------------------

# Install the shell's Node dependencies (needed once before console/dist-console)
console-install:
	cd $(CONSOLE_DIR) && npm install

# Run the console from this checkout: the shell puts src/ on PYTHONPATH itself,
# so nothing has to be installed first.
console:
	cd $(CONSOLE_DIR) && npm start

# --- distributables ----------------------------------------------------------

# Both halves. The console binary is a renderer: it needs an interpreter with
# this package installed, which is what the wheel is for.
dist: dist-python dist-console

# Python wheel + sdist into dist/. The type templates and the shell travel with
# them (see [tool.setuptools.package-data]).
dist-python:
	python -m build

# The console binary for the platform this runs on. electron-builder does not
# cross-compile Windows installers from Linux or vice versa; run this on each
# platform you want an artifact for. Output: $(CONSOLE_DIR)/dist/
dist-console:
	cd $(CONSOLE_DIR) && npm run dist

# Clean build artifacts and caches
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf build/ dist/ htmlcov/ .coverage
	rm -rf $(CONSOLE_DIR)/dist/

# Run the placeholder module (requires: pip install -e .)
run:
	python -m vpath_platform_mgmt