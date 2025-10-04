# Project Structure

**Version:** 1.0
**Date:** 2025-09-17
**Purpose:** Define codebase organization following DDD principles

## Directory Structure

```
ml_agents_v2/
├── pyproject.toml              # uv project configuration
├── uv.lock                     # Dependency lockfile
├── .env.example                # Environment template
├── .gitignore                  # Git exclusions
├── README.md                   # Project documentation
├── alembic.ini                 # Database migration config
├── alembic/                    # Migration scripts
│   └── versions/
├── src/
│   └── ml_agents_v2/
│       ├── __init__.py
│       ├── main.py             # CLI entry point
│       ├── config/
│       │   ├── __init__.py
│       │   └── application_config.py
│       ├── core/
│       │   ├── __init__.py
│       │   ├── domain/         # Domain layer (business logic)
│       │   │   ├── __init__.py
│       │   │   ├── entities/
│       │   │   │   ├── __init__.py
│       │   │   │   ├── evaluation.py
│       │   │   │   └── preprocessed_benchmark.py
│       │   │   ├── value_objects/
│       │   │   │   ├── __init__.py
│       │   │   │   ├── agent_config.py
│       │   │   │   ├── question.py
│       │   │   │   ├── answer.py
│       │   │   │   ├── evaluation_results.py
│       │   │   │   ├── reasoning_trace.py
│       │   │   │   └── failure_reason.py
│       │   │   ├── services/
│       │   │   │   ├── __init__.py
│       │   │   │   ├── reasoning_agent_service.py
│       │   │   │   ├── reasoning_agent_factory.py
│       │   │   │   └── reasoning/
│       │   │   │       ├── __init__.py
│       │   │   │       ├── none_agent.py
│       │   │   │       └── chain_of_thought_agent.py
│       │   │   └── repositories/
│       │   │       ├── __init__.py
│       │   │       ├── evaluation_repository.py
│       │   │       └── benchmark_repository.py
│       │   └── application/    # Application services
│       │       ├── __init__.py
│       │       ├── services/
│       │       │   ├── __init__.py
│       │       │   ├── evaluation_orchestrator.py
│       │       │   └── benchmark_processor.py
│       │       └── dto/
│       │           ├── __init__.py
│       │           ├── evaluation_info.py
│       │           └── progress_info.py
│       ├── infrastructure/     # Infrastructure layer
│       │   ├── __init__.py
│       │   ├── database/
│       │   │   ├── __init__.py
│       │   │   ├── base.py     # SQLAlchemy base configuration
│       │   │   ├── session_manager.py  # Database session management
│       │   │   ├── models/     # SQLAlchemy models
│       │   │   │   ├── __init__.py
│       │   │   │   ├── evaluation.py
│       │   │   │   └── benchmark.py
│       │   │   ├── repositories/
│       │   │   │   ├── __init__.py
│       │   │   │   ├── evaluation_repository_impl.py
│       │   │   │   └── benchmark_repository_impl.py
│       │   │   └── migrations/
│       │   │       ├── env.py
│       │   │       ├── script.py.mako
│       │   │       └── versions/
│       │   ├── providers/        # LLM provider implementations
│       │   │   ├── __init__.py
│       │   │   ├── openrouter/
│       │   │   │   ├── __init__.py
│       │   │   │   ├── client.py
│       │   │   │   └── error_mapper.py
│       │   │   ├── openai/
│       │   │   │   ├── __init__.py
│       │   │   │   ├── client.py
│       │   │   │   └── error_mapper.py
│       │   │   ├── anthropic/
│       │   │   │   ├── __init__.py
│       │   │   │   ├── client.py
│       │   │   │   └── error_mapper.py
│       │   │   └── litellm/
│       │   │       ├── __init__.py
│       │   │       ├── client.py
│       │   │       └── error_mapper.py
│       │   ├── parsers/          # Parsing strategy implementations
│       │   │   ├── __init__.py
│       │   │   ├── marvin/
│       │   │   │   ├── __init__.py
│       │   │   │   └── client.py
│       │   │   ├── outlines/
│       │   │   │   ├── __init__.py
│       │   │   │   └── client.py
│       │   │   ├── langchain/
│       │   │   │   ├── __init__.py
│       │   │   │   └── client.py
│       │   │   └── instructor/
│       │   │       ├── __init__.py
│       │   │       └── client.py
│       │   ├── factories/        # Factory implementations
│       │   │   ├── __init__.py
│       │   │   ├── llm_client_factory.py
│       │   │   └── model_capabilities.py
│       │   ├── models/           # Infrastructure Pydantic models
│       │   │   ├── __init__.py
│       │   │   ├── base_reasoning_output.py
│       │   │   ├── direct_answer_output.py
│       │   │   └── chain_of_thought_output.py
│       │   ├── container.py      # Dependency injection
│       │   ├── health.py         # Health check service
│       │   ├── reasoning_service.py  # Infrastructure reasoning service
│       │   └── logging_config.py  # Structured logging setup
│       └── cli/                # CLI interface
│           ├── __init__.py
│           ├── main.py         # Click command groups
│           ├── commands/
│           │   ├── __init__.py
│           │   ├── evaluate.py
│           │   ├── benchmark.py
│           │   └── health.py
│           └── utils/
│               ├── __init__.py
│               ├── formatting.py
│               ├── progress.py
│               └── error_handling.py
└── tests/
    ├── __init__.py
    ├── conftest.py             # Pytest configuration
    ├── fixtures/               # Test data
    │   ├── benchmarks/
    │   └── evaluations/
    ├── unit/                   # Unit tests
    │   ├── domain/
    │   ├── application/
    │   ├── infrastructure/
    │   └── cli/
    ├── integration/            # Integration tests
    │   ├── database/
    │   ├── providers/          # Provider integration tests
    │   │   ├── openrouter/
    │   │   ├── openai/
    │   │   ├── anthropic/
    │   │   └── litellm/
    │   ├── parsers/            # Parser strategy integration tests
    │   │   ├── marvin/
    │   │   ├── outlines/
    │   │   ├── langchain/
    │   │   └── instructor/
    │   ├── factories/          # Factory integration tests
    │   └── cli/
    └── acceptance/             # End-to-end tests
        └── test_evaluation_workflow.py
```

## Layer Dependencies

```
CLI → Application → Domain ← Infrastructure
```

**Dependency Rules:**

- CLI depends on Application services
- Application depends on Domain interfaces
- Infrastructure implements Domain interfaces
- Domain has no external dependencies

## Package Responsibilities

### `core/domain/`

Pure business logic with no external dependencies.

**entities/**: Aggregate roots with business rules and lifecycle management
**value_objects/**: Immutable objects representing domain concepts
**services/**: Stateless domain operations including reasoning agent implementations
**repositories/**: Interfaces for data persistence

**reasoning/**: Concrete reasoning agent implementations containing pure domain business logic:

- Prompt engineering strategies and template construction (domain logic)
- Response parsing and answer extraction business rules (domain logic)
- Reasoning trace construction and validation patterns (domain logic)
- Agent-specific configuration validation rules (domain logic)
- NO external API calls or infrastructure concerns

See [Reasoning Domain Logic](v2-reasoning-domain-logic.md) for complete implementation patterns and domain boundaries.

### `core/application/`

Orchestrates domain operations and external interactions.

**services/**: Coordinate domain entities and infrastructure
**dto/**: Data transfer objects for application boundaries

### `infrastructure/`

External system integrations and technical implementations with multi-provider support.

**database/**: SQLAlchemy models and repository implementations
**providers/**: LLM provider implementations (OpenRouter, OpenAI, Anthropic, LiteLLM)
**parsers/**: Parsing strategy implementations (Marvin, Outlines, LangChain, Instructor)
**factories/**: Factory implementations for provider and parser selection
**models/**: Infrastructure Pydantic models for structured output
**container.py**: Dependency injection configuration with factory pattern
**reasoning_service.py**: Infrastructure reasoning service orchestrating providers and parsers

### `cli/`

User interface and command handling.

**commands/**: Click command implementations
**utils/**: CLI formatting and error handling

## Import Conventions

```python
# Domain imports (no external dependencies)
from ml_agents_v2.core.domain.entities import Evaluation
from ml_agents_v2.core.domain.value_objects import AgentConfig

# Application imports
from ml_agents_v2.core.application.services import EvaluationOrchestrator

# Infrastructure imports
from ml_agents_v2.infrastructure.database.models import EvaluationModel
from ml_agents_v2.infrastructure.openrouter import OpenRouterClient

# CLI imports
from ml_agents_v2.cli.commands import evaluate
```

## Configuration Management

### Environment Files

- `.env` - Local development (not committed)
- `.env.example` - Template with dummy values
- `.env.test` - Test environment configuration

### Config Loading

```python
# config/application_config.py
from pydantic_settings import BaseSettings

class ApplicationConfig(BaseSettings):
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
```

## Database Organization

### Migration Scripts

```
src/ml_agents_v2/infrastructure/database/migrations/versions/
└── 8312ef6ff4bf_initial_schema_with_evaluations_and_.py
```

### Model Mapping

- Domain entities → SQLAlchemy models in `infrastructure/database/models/`
  - `Evaluation` entity → `models/evaluation.py`
  - `PreprocessedBenchmark` entity → `models/benchmark.py`
- Repository interfaces → Implementations in `infrastructure/database/repositories/`
- Database session management → `infrastructure/database/session_manager.py`

## Entry Points

### CLI Entry Point

```python
# main.py
from ml_agents_v2.cli.main import cli

if __name__ == "__main__":
    cli()
```

### Package Entry Point

```toml
# pyproject.toml
[project.scripts]
ml-agents = "ml_agents_v2.cli.main:cli"
```

## Development Tools

### Code Quality

- **black**: Code formatting
- **ruff**: Linting and import sorting
- **mypy**: Type checking

### Testing

- **pytest**: Test framework
- **pytest-asyncio**: Async test support
- **pytest-mock**: Mocking utilities
- **click.testing**: CLI testing

### Build Tools

- **uv**: Package management and virtual environments
- **alembic**: Database migrations

## See Also

- **[Domain Model](v2-domain-model.md)** - Business entities organized in the domain layer
- **[Reasoning Domain Logic](v2-reasoning-domain-logic.md)** - Reasoning agent implementation patterns and domain boundaries
- **[Infrastructure Requirements](v2-infrastructure-requirements.md)** - Technology dependencies and setup requirements
- **[Application Services Architecture](v2-application-services-architecture.md)** - Service layer coordination patterns
- **[CLI Design](v2-cli-design.md)** - CLI implementation structure and organization
- **[Testing Strategy](v2-testing-strategy.md)** - Test organization following this project structure
