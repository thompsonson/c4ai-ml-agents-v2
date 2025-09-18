# ML Agents v2

A reasoning research platform built using Domain-Driven Design principles.

## Overview

ML Agents v2 is a complete architectural redesign for evaluating the effectiveness of different AI reasoning approaches across various benchmarks. It transitions from v1's Jupyter notebook prototype to a production-ready CLI application.

## Key Features

- **Domain-Driven Design** with clean architecture layers
- **CLI Application** for systematic evaluation workflows
- **Multiple Reasoning Approaches**: None (direct), Chain of Thought, and more
- **SQLite/PostgreSQL** persistence with migration support
- **OpenRouter Integration** for unified LLM provider access
- **Real-time Progress** tracking during evaluation execution

## Quick Start

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd ml-agents-v2

# Set up virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install development dependencies
make dev-install
```

### Configuration

Copy the example environment file and configure:

```bash
cp .env.example .env
# Edit .env with your OpenRouter API key and other settings
```

### Usage

```bash
# Check system health
ml-agents health

# List available benchmarks
ml-agents benchmark list

# Create an evaluation
ml-agents evaluate create --agent cot --model anthropic/claude-3-sonnet --benchmark GPQA

# Run the evaluation
ml-agents evaluate run eval_123

# List evaluations
ml-agents evaluate list
```

## Development

### Quality Gates

All code changes must pass quality gates:

```bash
make quality-gates  # Runs test + type-check + format-check + lint
```

### Architecture

- **Domain Layer**: Pure business logic (no external dependencies)
- **Application Layer**: Service orchestration
- **Infrastructure Layer**: External integrations (DB, APIs)
- **CLI Layer**: User interface

### Documentation

See the `documentation/` directory for complete architectural specifications:

- [Domain Model](documentation/v2-domain-model.md)
- [Project Structure](documentation/v2-project-structure.md)
- [Core Behaviors](documentation/v2-core-behaviour-definition.md)
- [CLI Design](documentation/v2-cli-design.md)
- [Infrastructure Requirements](documentation/v2-infrastructure-requirements.md)

## License

MIT