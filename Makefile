.PHONY: help install test type-check format format-check lint clean dev-install quality-gates

# Default target
help:
	@echo "ML Agents v2 Development Commands"
	@echo ""
	@echo "Quality Gates (run before/after code changes):"
	@echo "  quality-gates    Run all quality checks (test + type-check + format-check + lint)"
	@echo "  test            Run pytest test suite"
	@echo "  type-check      Run mypy type checking"
	@echo "  format-check    Check code formatting with black"
	@echo "  lint            Run ruff linting"
	@echo ""
	@echo "Development:"
	@echo "  install         Install production dependencies"
	@echo "  dev-install     Install development dependencies"
	@echo "  format          Format code with black"
	@echo "  clean           Clean build artifacts"

# Installation
install:
	uv pip install -e .

dev-install:
	uv pip install -e ".[dev]"

# Quality Gates (Non-Negotiable)
quality-gates:
	@echo "Running quality gates..."
	@printf "🧪 Tests: "; \
	if uv run pytest -q >/dev/null 2>&1; then echo "OK"; else echo "FAILED"; uv run pytest -q; exit 1; fi
	@printf "🔍 Type check: "; \
	if uv run mypy src/ml_agents_v2 --no-error-summary >/dev/null 2>&1; then echo "OK"; else echo "FAILED"; uv run mypy src/ml_agents_v2; exit 1; fi
	@printf "📐 Format check: "; \
	if uv run black --quiet src/ tests/ >/dev/null 2>&1; then echo "OK"; else echo "FAILED"; uv run black $ --diff src/ tests/; exit 1; fi
	@printf "🔧 Lint: "; \
	if uv run ruff check --fix src/ tests/ >/dev/null 2>&1; then echo "OK"; else echo "FAILED"; uv run ruff check --fix src/ tests/; exit 1; fi
	@echo "✅ All quality gates passed!"

test:
	@echo "🧪 Running tests..."
	uv run pytest

type-check:
	@echo "🔍 Running type checks..."
	uv run mypy src/ml_agents_v2

format-check:
	@echo "📐 Checking code formatting..."
	uv run black --check --diff src/ tests/

lint:
	@echo "🔧 Running linter..."
	uv run ruff check src/ tests/

# Development helpers
format:
	@echo "🎨 Formatting code..."
	uv run black src/ tests/

# Clean up
clean:
	@echo "🧹 Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete