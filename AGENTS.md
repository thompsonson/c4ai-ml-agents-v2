# Agent Development Guide

## Commands
- **Quality Gates**: `make quality-gates` (run before/after EVERY change - non-negotiable)
- **Single Test**: `uv run pytest tests/path/to/test_file.py::TestClass::test_method`
- **Test Suite**: `make test` (quality gates), `make bdd-tests` (features under development)
- **Type Check**: `make type-check` or `uv run mypy src/ml_agents_v2`
- **Lint**: `make lint` or `uv run ruff check --fix src/ tests/`
- **Format**: `make format` or `uv run black src/ tests/`

## Code Style
- **Imports**: `from __future__ import annotations` at top; use `TYPE_CHECKING` for circular dependencies; `from collections.abc` not `typing`
- **Types**: Full type hints required (`disallow_untyped_defs=true`); use `| None` not `Optional[]`; `dict[str, Any]` not `Dict`
- **Naming**: snake_case for functions/variables; PascalCase for classes; descriptive names (e.g., `evaluation_id` not `id`)
- **Dataclasses**: Use `@dataclass(frozen=True)` for immutability; entities and value objects are frozen
- **Docstrings**: Triple-quoted strings for modules/classes/methods; Args/Returns sections for complex methods
- **Error Handling**: Custom exceptions in `exceptions.py` files; inherit from base exceptions; include descriptive messages
- **Line Length**: 88 chars (black default)
- **No Comments**: Code should be self-documenting

## Architecture
- **Domain layer**: No external dependencies; pure business logic
- **Application layer**: Orchestration only; depends on domain interfaces
- **Infrastructure layer**: Implements domain interfaces; external integrations
- **CLI layer**: Uses application services; no direct domain/infrastructure access

## Key Patterns
- **Value Objects**: Immutable with value-based equality (e.g., AgentConfig)
- **Entities**: Frozen dataclasses with identity (e.g., Evaluation, EvaluationQuestionResult)
- **Repositories**: Domain interfaces in `domain/repositories/`, implementations in `infrastructure/database/repositories/`
- **Anti-Corruption Layer**: Domain LLMClient interface abstracts external APIs (OpenRouter, Instructor)
