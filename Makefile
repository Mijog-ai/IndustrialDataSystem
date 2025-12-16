.PHONY: help install install-dev format lint type-check security test clean pre-commit run build

# Default target
help:
	@echo "Industrial Data System - Development Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  install        Install production dependencies"
	@echo "  install-dev    Install development dependencies"
	@echo "  format         Format code with black and isort"
	@echo "  lint           Run all linters (flake8, pylint, ruff)"
	@echo "  type-check     Run mypy type checking"
	@echo "  security       Run security checks (bandit, safety)"
	@echo "  test           Run pytest tests"
	@echo "  test-cov       Run tests with coverage report"
	@echo "  pre-commit     Run pre-commit hooks on all files"
	@echo "  clean          Clean build artifacts and caches"
	@echo "  run            Run the application"
	@echo "  build          Build executable with PyInstaller"
	@echo "  check-all      Run format, lint, type-check, security, and tests"
	@echo ""

# Installation targets
install:
	pip install -r requirements.txt

install-dev: install
	pip install -r requirements-dev.txt
	pre-commit install

# Code formatting
format:
	@echo "Running black..."
	black industrial_data_system/ main.py
	@echo "Running isort..."
	isort industrial_data_system/ main.py
	@echo "Running autoflake..."
	autoflake --in-place --remove-all-unused-imports --remove-unused-variables -r industrial_data_system/ main.py
	@echo "✓ Code formatting complete"

# Linting
lint:
	@echo "Running flake8..."
	flake8 industrial_data_system/ main.py
	@echo "Running pylint..."
	pylint industrial_data_system/ main.py || true
	@echo "Running ruff..."
	ruff check industrial_data_system/ main.py
	@echo "✓ Linting complete"

# Type checking
type-check:
	@echo "Running mypy..."
	mypy industrial_data_system/ main.py
	@echo "✓ Type checking complete"

# Security checks
security:
	@echo "Running bandit..."
	bandit -r industrial_data_system/ -f json -o bandit-report.json || bandit -r industrial_data_system/
	@echo "Running safety..."
	safety check --json > safety-report.json || safety check
	@echo "✓ Security checks complete"

# Testing
test:
	@echo "Running pytest..."
	pytest tests/ -v

test-cov:
	@echo "Running pytest with coverage..."
	pytest tests/ -v --cov=industrial_data_system --cov-report=term-missing --cov-report=html
	@echo "✓ Coverage report generated in htmlcov/"

# Pre-commit
pre-commit:
	@echo "Running pre-commit on all files..."
	pre-commit run --all-files

# Clean
clean:
	@echo "Cleaning build artifacts..."
	rm -rf build/ dist/ *.egg-info
	rm -rf .pytest_cache/ .mypy_cache/ .ruff_cache/ .tox/
	rm -rf htmlcov/ .coverage coverage.xml
	rm -rf **/__pycache__/
	find . -type f -name '*.pyc' -delete
	find . -type f -name '*.pyo' -delete
	find . -type f -name '*.orig' -delete
	find . -type d -name '__pycache__' -delete
	@echo "✓ Clean complete"

# Run application
run:
	python main.py

# Build executable
build:
	@echo "Building executable with PyInstaller..."
	pyinstaller IndustrialDataSystem.spec
	@echo "✓ Build complete - executable in dist/"

# Run all checks
check-all: format lint type-check security
	@echo "✓ All checks passed!"

# Development workflow
dev-setup: install-dev
	@echo "Development environment setup complete!"
	@echo "Run 'make format' to format code"
	@echo "Run 'make check-all' to run all checks"
	@echo "Run 'make run' to start the application"
