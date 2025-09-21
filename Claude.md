# ML Agents v2 - Claude Development Instructions

## Project Overview

ML Agents v2 is a reasoning research platform built using Domain-Driven Design principles. See [documentation/v2-domain-model.md](documentation/v2-domain-model.md) for complete architectural overview.

## Quality Gates Protocol (Non-Negotiable)

### Before ANY code changes:

```bash
make quality-gates
```

### After EVERY code change:

Re-run immediately. Fix failures before proceeding. Never skip quality gates.

### Failure Recovery:

STOP development when any check fails. Fix specific issue. Re-run full suite before continuing.

## Implementation Strategy

Follow **spec-driven development**: implementation flows from documented specifications.

### Reference Documentation:

- **Architecture**: [v2-project-structure.md](documentation/v2-project-structure.md)
- **Domain Design**: [v2-domain-model.md](documentation/v2-domain-model.md)
- **User Workflows**: [v2-core-behaviour-definition.md](documentation/v2-core-behaviour-definition.md)
- **CLI Interface**: [v2-cli-design.md](documentation/v2-cli-design.md)
- **Infrastructure**: [v2-infrastructure-requirements.md](documentation/v2-infrastructure-requirements.md)
- **Testing Strategy**: [v2-testing-strategy.md](documentation/v2-testing-strategy.md)
- **Implementation Phases**: [v2-task-tracker.md](documentation/v2-task-tracker.md)

### ATDD Workflow:

1. **Write failing test first** - describe expected behavior
2. **Implement minimal code** to pass test
3. **Refactor with test protection**
4. **Run quality gates** after each change

### Architecture Rules:

- **Domain layer**: No external dependencies
- **Application layer**: Depends only on domain interfaces
- **Infrastructure layer**: Implements domain interfaces
- **CLI layer**: Uses application services only

## Development Phases

Follow [v2-task-tracker.md](documentation/v2-task-tracker.md) for implementation order:

1. **Domain Layer** (Foundation) - Pure business logic
2. **Infrastructure Setup** - Database, APIs, configuration
3. **Application Services** - Orchestration and coordination
4. **CLI Interface** - User interaction
5. **Testing** - Comprehensive coverage

## Key Patterns

### Domain Entities:

See [v2-domain-model.md](documentation/v2-domain-model.md) for complete entity specifications.

### Repository Pattern:

Interfaces in domain layer, implementations in infrastructure. See [v2-data-model.md](documentation/v2-data-model.md).

### Error Handling:

OpenRouter errors → FailureReason value objects. See [v2-agents.md](documentation/v2-agents.md) for error categories.

### CLI Design:

Follow command structure in [v2-cli-design.md](documentation/v2-cli-design.md).

## Configuration

Agent defaults and environment variables defined in [v2-infrastructure-requirements.md](documentation/v2-infrastructure-requirements.md).

## Testing

Strategy and patterns detailed in [v2-testing-strategy.md](documentation/v2-testing-strategy.md).

---

All implementation details are in the referenced documentation files. Follow quality gates and ATDD workflow for consistent, reliable development.
