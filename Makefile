.PHONY: help install install-dev format lint check test security quality clean pre-commit

help:  ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install production dependencies
	pip install -r requirements.txt

install-dev:  ## Install development dependencies
	pip install -r requirements-dev.txt
	pre-commit install

format:  ## Format code with black and isort
	@echo "Running black..."
	black .
	@echo "Running isort..."
	isort .
	@echo "✅ Code formatting complete!"

lint:  ## Run all linters
	@echo "Running flake8..."
	flake8 .
	@echo "Running pylint..."
	pylint industrial_data_system
	@echo "✅ Linting complete!"

typecheck:  ## Run type checking with mypy
	@echo "Running mypy..."
	mypy .
	@echo "✅ Type checking complete!"

check:  ## Check code formatting and style (no modifications)
	@echo "Checking black formatting..."
	black --check .
	@echo "Checking isort..."
	isort --check-only .
	@echo "Running flake8..."
	flake8 .
	@echo "Running mypy..."
	mypy .
	@echo "✅ All checks passed!"

test:  ## Run tests with coverage
	@echo "Running tests..."
	pytest --cov=industrial_data_system --cov-report=term-missing --cov-report=html
	@echo "✅ Tests complete! Coverage report: htmlcov/index.html"

security:  ## Run security checks
	@echo "Running bandit security scan..."
	bandit -r industrial_data_system
	@echo "Running safety check..."
	safety check --full-report || true
	@echo "✅ Security scan complete!"

quality: format lint typecheck  ## Run all code quality checks and fix issues
	@echo "✅ All quality checks complete!"

pre-commit:  ## Run pre-commit hooks on all files
	pre-commit run --all-files

pre-commit-update:  ## Update pre-commit hooks
	pre-commit autoupdate

clean:  ## Clean up temporary files and caches
	@echo "Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	@echo "✅ Cleanup complete!"

build:  ## Build application with PyInstaller
	@echo "Building application..."
	pyinstaller IndustrialDataSystem.spec
	@echo "✅ Build complete!"

all: clean install-dev quality test security  ## Run everything
	@echo "✅ All tasks complete!"
