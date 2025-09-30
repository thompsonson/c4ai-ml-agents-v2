# ML Agents v2 Domain Model

**Version:** 1.2
**Date:** 2025-09-28
**Status:** Updated for Individual Question Persistence

## Overview

This document defines the domain model for the ML Agents v2 reasoning research platform. The model follows Domain-Driven Design principles to create clear boundaries between business concepts and technical implementation.

## Domain Context

**Business Domain**: Reasoning Research Platform
**Core Purpose**: Evaluate the effectiveness of different AI reasoning approaches across various benchmarks

**Key Research Questions**:

1. Do all tasks benefit from reasoning?
2. Do different models show varying benefits from reasoning?
3. How do different reasoning approaches compare?
4. Is there a task-approach fit?

## Domain Entities

### Aggregate Roots

#### Evaluation

**Purpose**: Orchestrates the evaluation of an AgentConfig against a PreprocessedBenchmark

**Identity**: EvaluationId (unique identifier)

**Attributes**:

- `evaluation_id`: Unique identifier
- `agent_config`: Configuration for reasoning approach (Value Object)
- `preprocessed_benchmark_id`: Reference to benchmark data
- `status`: Evaluation lifecycle state (pending, running, completed, failed, interrupted)
- `created_at`: When evaluation was initiated
- `started_at`: When execution began
- `completed_at`: When execution finished
- `failure_reason`: Detailed failure information when status is 'failed'

**Business Rules**:

- Cannot be modified once status is 'completed' or 'failed'
- Must have valid AgentConfig and PreprocessedBenchmark reference
- Failure reason must be provided when status transitions to 'failed'
- Individual question results managed separately for incremental persistence

**Lifecycle States**:

```
pending → running → completed
              ↓         ↓
            failed  interrupted
```

**Methods**:

- `start_execution()`: Transition to running state
- `complete()`: Mark evaluation as completed (results computed from question records)
- `fail_with_reason(failure_reason: FailureReason)`: Mark as failed with specific reason
- `interrupt()`: Mark as interrupted, preserving partial progress
- `can_be_modified()`: Check if evaluation can be changed
- `get_progress()`: Compute current progress from saved question results

---

#### EvaluationQuestionResult (New Entity)

**Purpose**: Individual question-answer pair with complete processing details

**Identity**: Composite key (evaluation_id, question_id)

**Attributes**:

- `id`: Unique record identifier
- `evaluation_id`: Reference to parent evaluation
- `question_id`: Question identifier within benchmark
- `question_text`: Original question content
- `expected_answer`: Ground truth answer
- `actual_answer`: Agent's extracted answer
- `is_correct`: Correctness evaluation result
- `execution_time`: Processing duration in seconds
- `reasoning_trace`: Step-by-step reasoning documentation
- `error_message`: Failure description if processing failed
- `processed_at`: When question was completed

**Business Rules**:

- Immutable once created (represents completed processing)
- Must belong to existing evaluation
- Question ID must be unique within evaluation
- Processing time must be positive
- Error message required if processing failed

**Methods**:

- `is_successful()`: Check if question was processed without errors
- `matches_expected()`: Verify answer correctness

---

#### PreprocessedBenchmark

**Purpose**: Ready-to-evaluate dataset with standardized format

**Identity**: BenchmarkId (unique identifier)

**Attributes**:

- `benchmark_id`: Unique identifier
- `name`: Human-readable benchmark name (e.g., "BHEH Logical Reasoning")
- `description`: Benchmark description and purpose
- `questions`: Collection of standardized questions
- `metadata`: Additional benchmark information
- `created_at`: When preprocessing completed
- `question_count`: Total number of questions
- `format_version`: Data format version for compatibility

**Business Rules**:

- Immutable once preprocessing is complete
- All questions must follow standardized format
- Must have at least one question
- Name must be unique within system

**Methods**:

- `get_questions()`: Return all questions for evaluation
- `get_sample(size: int)`: Return random sample of questions
- `get_metadata()`: Return benchmark metadata

### Domain Services

#### ReasoningAgentService

**Purpose**: Defines business logic for specific reasoning approaches (None, Chain of Thought, etc.)

The ReasoningAgentService contains pure domain logic for reasoning strategies including prompt engineering rules, response parsing patterns, and configuration validation. Implementation details are separated into infrastructure services that handle external API calls and structured output parsing.

**Domain Responsibilities:**

- Prompt strategy definition and template construction
- Response processing and answer extraction business rules
- Configuration validation against reasoning approach requirements
- Reasoning trace construction following domain patterns

**Interface**:

```python
class ReasoningAgentService:
    def get_prompt_strategy(self) -> PromptStrategy
    def process_question(self, question: Question, config: AgentConfig) -> str
    def process_response(self, raw_response: str, context: Dict[str, Any]) -> ReasoningResult
    def validate_config(self, config: AgentConfig) -> ValidationResult
    def get_agent_type(self) -> str
```

**Implementation Patterns**: See [Reasoning Domain Logic](v2-reasoning-domain-logic.md) for complete domain boundaries, business rule implementations, and infrastructure integration patterns.

---

#### LLMClient

**Purpose**: Domain interface for LLM interactions, ensuring complete isolation from external API implementations

The LLMClient interface defines what the domain needs from LLM providers without exposing any external API implementation details. This interface acts as an Anti-Corruption Layer boundary, ensuring that domain logic never depends on external system types or behavior.

**Domain Responsibilities:**

- Provide consistent LLM interaction interface regardless of provider
- Return standardized domain types (ParsedResponse) only
- Abstract away external API complexity and type variations
- Enable testing with domain-focused mock implementations

**Interface**:

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class LLMClient(ABC):
    """Domain interface for LLM interactions.

    Infrastructure implementations must translate all external API responses
    to domain ParsedResponse objects, ensuring no external types leak into
    domain or application layers.
    """

    @abstractmethod
    async def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> ParsedResponse:
        """Execute chat completion and return domain ParsedResponse.

        Args:
            model: Model identifier (e.g., "gpt-4", "claude-3-sonnet")
            messages: Conversation messages in standard format
            **kwargs: Model-specific parameters (temperature, max_tokens, etc.)

        Returns:
            ParsedResponse: Domain value object with standardized token usage

        Raises:
            Domain exceptions only - never external API exceptions
        """
        pass
```

**Anti-Corruption Layer Principle**: Infrastructure implementations of this interface MUST translate all external API responses, errors, and types to domain equivalents immediately upon receipt. The domain layer should never import or depend on external LLM provider types.

**Testing Benefits**: Domain logic can be tested with simple mock implementations that return known ParsedResponse objects, without requiring external API access or complex mocking of provider-specific types.

### Value Objects

#### AgentConfig

**Purpose**: Configuration that determines which ReasoningAgent to use and how

This is a value object because configurations are reusable and shareable across evaluations. Two AgentConfig instances with identical attributes represent the same conceptual configuration, regardless of when or where they were created. The non-deterministic nature of LLM outputs means the same configuration can produce different results, but that variation belongs in the EvaluationResults, not the configuration itself.

**Attributes**:

- `agent_type`: Type of reasoning agent (None, CoT, PoT, etc.)
- `model_provider`: LLM provider (Anthropic, OpenRouter, Cohere, etc.)
- `model_name`: Specific model identifier
- `model_parameters`: Model-specific parameters (temperature, max_tokens, etc.)
- `agent_parameters`: Agent-specific parameters

**Business Rules**:

- Must specify valid agent_type from available implementations
- Model parameters must be compatible with selected provider
- Reasoning parameters must be valid for selected agent type

**Methods**:

- `get_reasoning_agent_service()`: Factory method for service
- `validate_configuration()`: Ensure configuration is valid
- `to_dict()`: Serialize for storage/comparison
- `equals(other: AgentConfig)`: Value-based equality comparison

**Immutable**: Yes

---

#### Question

**Purpose**: Standardized input data from benchmark

**Attributes**:

- `id`: Question identifier within benchmark
- `text`: Question content
- `expected_answer`: Ground truth answer
- `metadata`: Additional question information (difficulty, category, etc.)

**Immutable**: Yes

---

#### Answer

**Purpose**: Response from reasoning agent with trace information

**Attributes**:

- `extracted_answer`: Clean, final answer
- `reasoning_trace`: Step-by-step reasoning process
- `execution_time`: Time taken to generate answer
- `raw_response`: Full model response text

**Immutable**: Yes

---

#### EvaluationResults (Computed Value Object)

**Purpose**: Complete evaluation outcomes and metrics computed from individual question results

**Attributes**:

- `total_questions`: Number of questions evaluated
- `correct_answers`: Number of correctly answered questions
- `accuracy`: Percentage accuracy (correct/total)
- `average_execution_time`: Mean time per question
- `total_tokens`: Total token consumption
- `error_count`: Number of failed questions
- `detailed_results`: Per-question results
- `summary_statistics`: Additional metrics

**Immutable**: Yes

**Computation Pattern**:

```python
@classmethod
def from_question_results(cls, question_results: List[EvaluationQuestionResult]) -> 'EvaluationResults':
    """Compute evaluation results from individual question records"""
    total_questions = len(question_results)
    correct_answers = sum(1 for q in question_results if q.is_correct)

    return cls(
        total_questions=total_questions,
        correct_answers=correct_answers,
        accuracy=correct_answers / total_questions if total_questions > 0 else 0.0,
        average_execution_time=sum(q.execution_time for q in question_results) / total_questions,
        error_count=sum(1 for q in question_results if q.error_message),
        detailed_results=[q.to_question_result() for q in question_results],
        summary_statistics={}
    )
```

**Methods**:

- `calculate_accuracy()`: Compute accuracy percentage
- `get_performance_summary()`: Summary statistics
- `export_detailed_csv()`: Export for analysis

---

#### ReasoningTrace

**Purpose**: Reasoning documentation

**Attributes**:

- `approach_type`: Type of reasoning used ("None" or "ChainOfThought")
- `reasoning_text`: The reasoning content (empty for "None", step-by-step text for "ChainOfThought")
- `metadata`: Additional trace information

**Immutable**: Yes

**Notes**:

- For "None" approach: `reasoning_text` is empty string
- For "ChainOfThought" approach: `reasoning_text` contains the model's reasoning steps

---

#### FailureReason

**Purpose**: Detailed categorization of evaluation failures

Understanding why evaluations fail is crucial for researchers to improve their approaches and identify systematic issues.

**Attributes**:

- `category`: Type of failure (parsing_error, token_limit_exceeded, content_guardrail, model_refusal, network_timeout, rate_limit_exceeded, credit_limit_exceeded, authentication_error, unknown)
- `description`: Human-readable failure description
- `technical_details`: Raw error information for debugging
- `occurred_at`: When the failure occurred
- `recoverable`: Whether this failure type might succeed on retry

**Subtypes**:

- `StructuredOutputParsingFailure`: Model response doesn't match expected format
- `TokenLimitExceeded`: Request exceeded model's token capacity
- `ContentGuardrailTriggered`: Model safety systems prevented response
- `ModelRefusal`: Model explicitly declined to answer
- `NetworkTimeout`: Communication failure with model provider
- `RateLimitExceeded`: API rate limit reached, retry after delay
- `CreditLimitExceeded`: Insufficient API credits or budget
- `AuthenticationError`: Invalid API key or authentication failure
- `UnknownFailure`: Unexpected error not fitting other categories

**Immutable**: Yes

**Methods**:

- `is_recoverable()`: Whether retry might succeed
- `get_category_description()`: Human-friendly explanation of failure type

---


#### ParsedResponse

**Purpose**: Standardized representation of structured LLM responses

Provides a clean boundary between external API response formats and domain processing, ensuring consistent handling regardless of underlying LLM provider implementation details.

**Attributes**:

- `content`: Raw text content from the LLM response
- `structured_data`: Parsed structured output (when using structured output modes)

**Business Rules**:

- Content must not be empty for successful responses
- Structured data is optional (None for text-only responses)
- Immutable once created

**Methods**:

```python
@dataclass(frozen=True)
class ParsedResponse:
    content: str
    structured_data: dict | None = None

    def __post_init__(self) -> None:
        """Validate response content."""
        if not self.content or not self.content.strip():
            raise ValueError("Response content cannot be empty")

    def has_structured_data(self) -> bool:
        """Check if response includes parsed structured output."""
        return self.structured_data is not None

    def get_content_length(self) -> int:
        """Get character count of response content."""
        return len(self.content)
```

**Immutable**: Yes

**Domain Rationale**: Abstracts away external API response format variations, providing a consistent interface for domain logic regardless of whether the response came from OpenAI, Anthropic, or other providers.

## Domain Relationships

```
Evaluation (Aggregate Root)
├── AgentConfig (Value Object)
│   └─→ ReasoningAgentService (Domain Service)
│       └─→ Question → Answer (Value Objects)
├─→ PreprocessedBenchmark (Reference)
│   └── Questions (Value Objects)
├─→ EvaluationQuestionResult (Entities, one-to-many)
│   ├── Question data (embedded)
│   ├── Answer data (embedded)
│   └── ReasoningTrace (Value Object)
├── EvaluationResults (Computed Value Object)
└── FailureReason (Value Object, when failed)
```

### Relationship Rules

1. **Evaluation contains AgentConfig**: 1:1 relationship, but AgentConfig can be reused across multiple evaluations
2. **Evaluation references PreprocessedBenchmark**: 1:1 relationship, benchmark exists independently
3. **Evaluation → EvaluationQuestionResult**: 1:many relationship, question results saved incrementally
4. **AgentConfig specifies ReasoningAgentService**: Configuration determines which service implementation to use
5. **ReasoningAgentService processes Questions**: Service is stateless, processes questions individually
6. **EvaluationResults computed from EvaluationQuestionResult**: Results aggregated from individual records
7. **FailureReason provides failure context**: Only present when evaluation fails, explains what went wrong

## Bounded Context Boundaries

### Core Domain

- **Entities**: Evaluation, EvaluationQuestionResult, PreprocessedBenchmark
- **Services**: ReasoningAgentService
- **Value Objects**: AgentConfig, Question, Answer, EvaluationResults, ReasoningTrace, FailureReason

### Supporting Domains

- **Infrastructure**: Database persistence, API clients, file system
- **Application**: CLI commands, orchestration services
- **Reasoning Implementations**: Concrete reasoning agent services

## Domain Events (Future Consideration)

Potential domain events for future implementation:

- `EvaluationStarted`
- `EvaluationCompleted`
- `EvaluationFailed`
- `EvaluationInterrupted`
- `QuestionProcessed`
- `BenchmarkPreprocessed`

## Invariants and Business Rules

### System-Wide Invariants

1. All evaluations must have unique identifiers
2. PreprocessedBenchmarks are immutable after creation
3. EvaluationQuestionResults are immutable once created
4. AgentConfigs must be valid for their specified reasoning approach
5. Failed evaluations must have a FailureReason

### Evaluation Invariants

1. Cannot modify evaluation once completed or failed
2. Status transitions must follow defined lifecycle
3. FailureReason is required when status is 'failed'
4. Question results can only be added during 'running' status

### EvaluationQuestionResult Invariants

1. Must belong to existing evaluation
2. Question ID must be unique within evaluation
3. Cannot be modified once created
4. Processing time must be positive
5. Error message required if processing failed

### PreprocessedBenchmark Invariants

1. Must contain at least one question
2. All questions must have expected answers
3. Benchmark names must be unique
4. Cannot be modified after creation

### AgentConfig Invariants (Value Object)

1. All required fields must be present
2. Model parameters must be valid for the specified provider
3. Reasoning parameters must be compatible with agent type
4. Equality is determined by attribute values, not identity

## Repository Interfaces

```python
class EvaluationRepository:
    def save(self, evaluation: Evaluation) -> None
    def get_by_id(self, evaluation_id: EvaluationId) -> Evaluation
    def get_by_status(self, status: EvaluationStatus) -> List[Evaluation]
    def get_by_agent_config(self, config: AgentConfig) -> List[Evaluation]
    def get_all(self) -> List[Evaluation]

class EvaluationQuestionResultRepository:
    def save(self, question_result: EvaluationQuestionResult) -> None
    def get_by_evaluation_id(self, evaluation_id: EvaluationId) -> List[EvaluationQuestionResult]
    def get_by_id(self, question_result_id: UUID) -> EvaluationQuestionResult
    def count_by_evaluation_id(self, evaluation_id: EvaluationId) -> int
    def get_progress(self, evaluation_id: EvaluationId) -> ProgressInfo
    def exists(self, evaluation_id: EvaluationId, question_id: str) -> bool

class PreprocessedBenchmarkRepository:
    def save(self, benchmark: PreprocessedBenchmark) -> None
    def get_by_id(self, benchmark_id: BenchmarkId) -> PreprocessedBenchmark
    def get_by_name(self, name: str) -> PreprocessedBenchmark
    def get_all() -> List[PreprocessedBenchmark]
```

## Factory Patterns

### ReasoningAgentServiceFactory

```python
class ReasoningAgentServiceFactory:
    def create_service(self, agent_type: str) -> ReasoningAgentService
    def get_available_types(self) -> List[str]
    def validate_agent_type(self, agent_type: str) -> bool
```

## Domain Model Evolution

### Version 1.2 (Current)

- Core aggregates: Evaluation, EvaluationQuestionResult, PreprocessedBenchmark
- Individual question persistence for incremental saving
- AgentConfig as reusable value object
- Rich failure taxonomy with FailureReason
- Computed EvaluationResults from question records
- 8+ reasoning approaches planned
- SQLite persistence
- CLI interface

### Future Considerations

- Domain events for real-time monitoring
- PreprocessedBenchmark versioning to support benchmark evolution
- Experiment batching and scheduling
- Advanced metrics and reporting
- Multi-user access and permissions
- Resume capability for interrupted evaluations

---

## Implementation Notes

### Technology Alignment

- **Language**: Python 3.9+
- **Persistence**: SQLite for development, extensible to PostgreSQL
- **API Integration**: Multiple LLM providers (Anthropic, OpenRouter, Cohere)
- **Testing**: pytest with domain-focused test structure

### File Organization

Domain model classes should be organized by aggregate:

- `core/domain/evaluation/` - Evaluation aggregate
- `core/domain/question_result/` - EvaluationQuestionResult aggregate
- `core/domain/benchmark/` - PreprocessedBenchmark aggregate
- `core/domain/value_objects/` - Shared value objects
- `core/domain/services/` - Domain service interfaces

### Validation Strategy

- Domain entities validate their own state
- Repository implementations handle persistence validation
- Application services coordinate cross-aggregate validation
- Value objects are immutable and validate on construction
- AgentConfig equality based on value comparison, not identity

### Key Design Rationale

**Individual Question Persistence**: Each question-answer pair is saved immediately upon completion, enabling graceful interruption handling and incremental progress tracking. This design recognizes that partial evaluation results have independent research value.

**Computed EvaluationResults**: Rather than storing results as JSON, they're computed from individual question records. This ensures consistency and enables real-time progress monitoring while maintaining the familiar EvaluationResults interface.

**AgentConfig as Value Object**: This design decision reflects that configurations are conceptual templates that can be shared and reused. Multiple researchers can use the same reasoning approach configuration, and the system recognizes these as the same thing rather than separate entities.

**Rich Failure Taxonomy**: Research platforms must help users understand why experiments fail. Generic "failed" status provides little actionable information, while specific failure categories help researchers identify whether issues stem from configuration problems, infrastructure limitations, or model behavior.

---

## See Also

- **[Data Model](v2-data-model.md)** - Database schema implementation of these domain entities
- **[Application Services Architecture](v2-application-services-architecture.md)** - Service coordination patterns using these domain concepts
- **[Ubiquitous Language](v2-ubiquitous-language.md)** - Shared vocabulary definitions for domain terms
- **[Core Behaviors](v2-core-behaviour-definition.md)** - User workflows that manipulate these domain entities
- **[Reasoning Domain Logic](v2-reasoning-domain-logic.md)** - Detailed reasoning agent business logic and implementation patterns

---

_This domain model serves as the foundation for all v2 implementation decisions and should be referenced when making architectural choices._
