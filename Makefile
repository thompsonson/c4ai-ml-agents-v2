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
quality-gates: test type-check format-check lint
	@echo "✅ All quality gates passed!"

test:
	@echo "🧪 Running tests..."
	pytest

type-check:
	@echo "🔍 Running type checks..."
	mypy src/ml_agents_v2

format-check:
	@echo "📐 Checking code formatting..."
	black --check --diff src/ tests/

lint:
	@echo "🔧 Running linter..."
	ruff check src/ tests/

# Development helpers
format:
	@echo "🎨 Formatting code..."
	black src/ tests/

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