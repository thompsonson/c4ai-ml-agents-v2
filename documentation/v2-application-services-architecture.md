# Application Services Architecture

**Version:** 1.1
**Date:** 2025-09-28
**Purpose:** Define orchestration layer with individual question persistence patterns

## Architecture Overview

Application services orchestrate domain operations without containing business logic. They coordinate transactions, handle cross-aggregate operations, and translate between external APIs and domain concepts. With individual question persistence, services manage incremental saving and graceful interruption handling.

```mermaid
graph TD
    A[CLI Interface] --> B[Application Services]
    B --> C[Domain Layer]
    B --> D[Infrastructure Layer]

    C --> E[Evaluation Aggregate]
    C --> F[EvaluationQuestionResult Aggregate]
    C --> G[PreprocessedBenchmark Aggregate]
    C --> H[Domain Services]

    D --> I[Repositories]
    D --> J[External APIs]
    D --> K[Configuration]
```

## Bounded Context Mapping

```mermaid
graph LR
    subgraph "Core Research Context"
        A[Evaluation Management]
        B[Question Processing]
        C[Benchmark Processing]
        D[Results Analysis]
    end

    subgraph "Infrastructure Context"
        E[OpenRouter Integration]
        F[Database Persistence]
        G[Configuration Management]
    end

    subgraph "User Interface Context"
        H[CLI Commands]
        I[Progress Monitoring]
    end

    A --> E
    A --> F
    B --> F
    C --> F
    H --> A
    H --> B
    H --> C
    H --> D
```

## Application Service Interfaces

### EvaluationOrchestrator

Primary service coordinating evaluation lifecycle with incremental question persistence.

```python
class EvaluationOrchestrator:
    def __init__(
        self,
        evaluation_repo: EvaluationRepository,
        question_result_repo: EvaluationQuestionResultRepository,
        benchmark_repo: PreprocessedBenchmarkRepository,
        reasoning_service_factory: ReasoningAgentServiceFactory,
        config: ApplicationConfig
    ):
        pass

    def create_evaluation(
        self,
        agent_config: AgentConfig,
        benchmark_name: str
    ) -> EvaluationId:
        """Create new evaluation in pending state"""
        pass

    def execute_evaluation(self, evaluation_id: EvaluationId) -> None:
        """Execute evaluation with incremental question persistence"""
        pass

    def get_evaluation_status(self, evaluation_id: EvaluationId) -> EvaluationStatus:
        """Check current evaluation state"""
        pass

    def get_evaluation_results(self, evaluation_id: EvaluationId) -> EvaluationResults:
        """Retrieve completed evaluation results computed from question records"""
        pass

    def get_evaluation_progress(self, evaluation_id: EvaluationId) -> ProgressInfo:
        """Get real-time progress from saved question results"""
        pass

    def resume_evaluation(self, evaluation_id: EvaluationId) -> None:
        """Resume interrupted evaluation from last completed question"""
        pass
```

### BenchmarkProcessor

Handles benchmark preprocessing and management.

```python
class BenchmarkProcessor:
    def __init__(
        self,
        benchmark_repo: PreprocessedBenchmarkRepository,
        config: ApplicationConfig
    ):
        pass

    def preprocess_benchmark(
        self,
        raw_data: str,
        benchmark_name: str,
        description: str
    ) -> BenchmarkId:
        """Process raw benchmark data into standardized format"""
        pass

    def list_available_benchmarks(self) -> List[BenchmarkInfo]:
        """Get all preprocessed benchmarks"""
        pass

    def get_benchmark_details(self, benchmark_name: str) -> PreprocessedBenchmark:
        """Retrieve specific benchmark with questions"""
        pass
```

### ResultsAnalyzer

Provides analysis and reporting capabilities using individual question records.

```python
class ResultsAnalyzer:
    def __init__(
        self,
        evaluation_repo: EvaluationRepository,
        question_result_repo: EvaluationQuestionResultRepository,
        config: ApplicationConfig
    ):
        pass

    def get_evaluation_summary(self, evaluation_id: EvaluationId) -> EvaluationSummary:
        """Get high-level results summary computed from question records"""
        pass

    def export_detailed_results(
        self,
        evaluation_id: EvaluationId,
        format: ExportFormat
    ) -> str:
        """Export detailed results from individual question records"""
        pass

    def list_evaluations(
        self,
        filters: EvaluationFilters = None
    ) -> List[EvaluationInfo]:
        """List evaluations with computed summary statistics"""
        pass

    def analyze_question_patterns(
        self,
        evaluation_ids: List[EvaluationId]
    ) -> QuestionAnalysis:
        """Cross-evaluation question performance analysis"""
        pass
```

## Data Transfer Objects (DTOs)

Application services use DTOs to transfer data across layer boundaries while keeping domain entities encapsulated.

### EvaluationInfo

Summary information for evaluation listings and status displays.

```python
@dataclass(frozen=True)
class EvaluationInfo:
    evaluation_id: uuid.UUID
    agent_type: str
    model_name: str
    benchmark_name: str
    status: str
    accuracy: float | None                 # Computed from question results
    created_at: datetime
    completed_at: datetime | None
    total_questions: int | None            # From benchmark or completed questions
    correct_answers: int | None            # Computed from question results
    questions_processed: int               # Count of saved question results

    @property
    def is_completed(self) -> bool:
        return self.status == "completed"

    @property
    def accuracy_percentage(self) -> str:
        return f"{self.accuracy:.1f}%" if self.accuracy else "-"

    @property
    def progress_percentage(self) -> float:
        if self.total_questions and self.total_questions > 0:
            return (self.questions_processed / self.total_questions) * 100
        return 0.0

    @property
    def duration_minutes(self) -> float | None:
        if self.completed_at and self.created_at:
            return (self.completed_at - self.created_at).total_seconds() / 60
        return None
```

### ProgressInfo

Real-time progress tracking during evaluation execution.

```python
@dataclass(frozen=True)
class ProgressInfo:
    evaluation_id: uuid.UUID
    current_question: int                  # From saved question results count
    total_questions: int
    successful_answers: int                # From saved question results
    failed_questions: int                  # From saved question results with errors
    started_at: datetime
    last_updated: datetime                 # From most recent question result

    @property
    def completion_percentage(self) -> float:
        return (self.current_question / self.total_questions) * 100 if self.total_questions > 0 else 0.0

    @property
    def success_rate(self) -> float:
        answered = self.successful_answers + self.failed_questions
        return (self.successful_answers / answered) * 100 if answered > 0 else 0.0

    @property
    def estimated_remaining_minutes(self) -> float | None:
        elapsed = self.elapsed_minutes
        if elapsed > 0 and self.current_question > 0:
            time_per_question = elapsed / self.current_question
            remaining_questions = self.total_questions - self.current_question
            return time_per_question * remaining_questions
        return None

    @classmethod
    def from_question_results(
        cls,
        evaluation_id: uuid.UUID,
        evaluation: Evaluation,
        question_results: List[EvaluationQuestionResult],
        total_questions: int
    ) -> 'ProgressInfo':
        """Compute progress from saved question results"""
        successful = sum(1 for q in question_results if q.is_correct and not q.error_message)
        failed = sum(1 for q in question_results if q.error_message)
        last_updated = max((q.processed_at for q in question_results), default=evaluation.started_at)

        return cls(
            evaluation_id=evaluation_id,
            current_question=len(question_results),
            total_questions=total_questions,
            successful_answers=successful,
            failed_questions=failed,
            started_at=evaluation.started_at,
            last_updated=last_updated
        )
```

### ValidationResult

Immutable validation result aggregation across multiple validation steps.

```python
@dataclass(frozen=True)
class ValidationResult:
    is_valid: bool
    errors: List[str]
    warnings: List[str]

    @classmethod
    def success(cls, warnings: List[str] = None) -> "ValidationResult":
        return cls(is_valid=True, errors=[], warnings=warnings or [])

    @classmethod
    def failure(cls, errors: List[str], warnings: List[str] = None) -> "ValidationResult":
        return cls(is_valid=False, errors=errors, warnings=warnings or [])

    def combine(self, other: "ValidationResult") -> "ValidationResult":
        return ValidationResult(
            is_valid=self.is_valid and other.is_valid,
            errors=self.errors + other.errors,
            warnings=self.warnings + other.warnings,
        )
```

## Core Workflows with Sequence Diagrams

### 1. Create and Execute Evaluation with Incremental Persistence

```mermaid
sequenceDiagram
    participant CLI
    participant Orchestrator
    participant EvalRepo
    participant QuestionRepo
    participant BenchRepo
    participant ReasoningService
    participant OpenRouter

    Note over CLI, OpenRouter: Transaction Boundary 1: Evaluation Creation
    CLI->>Orchestrator: create_evaluation(agent_config, benchmark_name)
    Orchestrator->>BenchRepo: get_by_name(benchmark_name)
    BenchRepo-->>Orchestrator: PreprocessedBenchmark
    Orchestrator->>Orchestrator: validate_agent_config()
    Orchestrator->>EvalRepo: save(new Evaluation(pending))
    EvalRepo-->>Orchestrator: evaluation_id
    Orchestrator-->>CLI: evaluation_id

    Note over CLI, OpenRouter: Transaction Boundary 2: Evaluation Execution
    CLI->>Orchestrator: execute_evaluation(evaluation_id)
    Orchestrator->>EvalRepo: get_by_id(evaluation_id)
    EvalRepo-->>Orchestrator: Evaluation
    Orchestrator->>Orchestrator: transition_to_running()
    Orchestrator->>EvalRepo: save(Evaluation)

    loop For each question
        Note over CLI, OpenRouter: Transaction Boundary 3: Individual Question Processing
        Orchestrator->>ReasoningService: process_question(question, agent_config)
        ReasoningService->>OpenRouter: API call
        alt Success
            OpenRouter-->>ReasoningService: response
            ReasoningService-->>Orchestrator: Answer
            Orchestrator->>Orchestrator: create_question_result(question, answer)
            Orchestrator->>QuestionRepo: save(EvaluationQuestionResult)
        else Failure
            OpenRouter-->>ReasoningService: error
            ReasoningService-->>Orchestrator: FailureReason
            Orchestrator->>Orchestrator: create_question_result_with_error(question, error)
            Orchestrator->>QuestionRepo: save(EvaluationQuestionResult with error)
        end

        Note over CLI: Progress: 42/150 (28%) - 38 correct, 4 errors
    end

    Note over CLI, OpenRouter: Transaction Boundary 4: Evaluation Completion
    Orchestrator->>Orchestrator: transition_to_completed()
    Orchestrator->>EvalRepo: save(Evaluation)
    Orchestrator-->>CLI: success
```

### 2. Graceful Interruption and Resume

```mermaid
sequenceDiagram
    participant CLI
    participant Orchestrator
    participant EvalRepo
    participant QuestionRepo
    participant User

    Note over CLI, User: Evaluation Running - Processing Questions
    CLI->>Orchestrator: execute_evaluation(evaluation_id)

    loop Processing Questions
        Orchestrator->>QuestionRepo: save(question_result)
        Note over CLI: Progress: 89/150 (59%) - 82 correct, 7 errors
    end

    Note over CLI, User: User Interruption (Ctrl+C)
    User->>CLI: Ctrl+C
    CLI->>Orchestrator: interrupt_evaluation(evaluation_id)
    Orchestrator->>Orchestrator: transition_to_interrupted()
    Orchestrator->>EvalRepo: save(Evaluation)
    CLI-->>User: Evaluation interrupted. 89/150 questions completed.

    Note over CLI, User: Later - Resume Evaluation
    CLI->>Orchestrator: resume_evaluation(evaluation_id)
    Orchestrator->>QuestionRepo: get_by_evaluation_id(evaluation_id)
    QuestionRepo-->>Orchestrator: List[completed_questions]
    Orchestrator->>Orchestrator: find_next_unprocessed_question()

    loop Continue from where left off
        Note over CLI: Progress: 90/150 (60%) - Resuming from question 90
        Orchestrator->>QuestionRepo: save(question_result)
    end
```

### 3. Real-time Progress with Saved Results

```mermaid
sequenceDiagram
    participant CLI
    participant Orchestrator
    participant QuestionRepo

    Note over CLI, QuestionRepo: During Evaluation Execution
    CLI->>Orchestrator: get_evaluation_progress(evaluation_id)
    Orchestrator->>QuestionRepo: get_by_evaluation_id(evaluation_id)
    QuestionRepo-->>Orchestrator: List[saved_question_results]
    Orchestrator->>Orchestrator: compute_progress_from_results()
    Orchestrator-->>CLI: ProgressInfo(42/150, 38 correct, 4 errors)

    Note over CLI: Display: "Progress: 42/150 (28%) - 38 correct (90.5%), 4 errors"
```

## Transaction Boundaries

### 1. Evaluation Creation Transaction

- **Scope:** Validate config → Create evaluation entity → Persist
- **Rollback Triggers:** Invalid agent config, duplicate evaluation, benchmark not found
- **Isolation:** Read committed (concurrent creations allowed)

### 2. Individual Question Processing Transaction

- **Scope:** Process single question → Create question result → Save immediately
- **Rollback Triggers:** Critical system errors (not LLM failures)
- **Isolation:** Per-question isolation, evaluation can continue if individual questions fail
- **Benefits:** No data loss on interruption, incremental progress tracking

### 3. Evaluation State Transition Transaction

- **Scope:** Update evaluation status (running → completed/interrupted/failed)
- **Rollback Triggers:** Concurrent modification
- **Isolation:** Optimistic locking on evaluation record

### 4. Benchmark Creation Transaction

- **Scope:** Parse raw data → Validate questions → Create benchmark
- **Rollback Triggers:** Invalid format, duplicate name, parsing errors
- **Isolation:** Exclusive lock on benchmark name

## Error Handling Strategy

### Error Categories and Propagation

```mermaid
flowchart TD
    A[External API Error] --> B{Error Type}

    B -->|Network| C[FailureReason: network_timeout]
    B -->|Rate Limit| D[FailureReason: rate_limit]
    B -->|Auth| E[FailureReason: authentication]
    B -->|Parsing| F[FailureReason: parsing_error]

    C --> G[Question Level Handling]
    D --> G
    E --> H[Evaluation Level Handling]
    F --> G

    G --> I[Save Question Result with Error]
    I --> J[Continue with Next Question]

    H --> K[Fail Evaluation Immediately]
```

### Failure Recovery Patterns

1. **Question-Level Failures:** Save question result with error, continue evaluation
2. **Configuration Failures:** Fail fast during creation
3. **Infrastructure Failures:** Retry with exponential backoff
4. **Business Logic Failures:** Immediate failure with detailed context
5. **Interruption Handling:** Save partial progress, enable resume

## Cross-Service Communication

### Service Dependencies

```mermaid
graph TD
    A[EvaluationOrchestrator] --> B[BenchmarkProcessor]
    A --> C[ResultsAnalyzer]
    A --> D[ReasoningAgentServiceFactory]

    A --> E[EvaluationRepository]
    A --> F[EvaluationQuestionResultRepository]
    C --> E
    C --> F
    B --> G[BenchmarkRepository]

    D --> H[OpenRouterClient]
    D --> I[ConfigurationService]
```

### Interface Contracts

- **Repository Interfaces:** Domain-driven, infrastructure-agnostic
- **External Service Interfaces:** Abstracted behind domain services
- **Configuration Interfaces:** Environment-aware, validation included
- **Question Result Interfaces:** Incremental persistence with immediate consistency

## Concurrency and Performance

### Async Operation Patterns

- **Evaluation Execution:** Synchronous processing with incremental persistence
- **Question Processing:** Sequential with immediate saving per question
- **Results Retrieval:** Computed from saved question records
- **Progress Tracking:** Real-time computation from database

### Resource Management

- **Connection Pooling:** OpenRouter API connections
- **Rate Limiting:** Built into OpenRouter client
- **Memory Management:** Stream question results for large evaluations
- **Database Efficiency:** Individual question persistence optimized for research workflows

## Validation Layers

### Input Validation

```python
@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str]
    warnings: List[str]
```

1. **CLI Layer:** Basic input sanitization and format validation
2. **Application Layer:** Business rule validation and cross-aggregate checks
3. **Domain Layer:** Entity invariants and value object constraints
4. **Infrastructure Layer:** Data persistence validation

## Configuration Management Integration

### Application Configuration Structure

```python
@dataclass
class ApplicationConfig:
    database_url: str
    openrouter_api_key: str
    openrouter_base_url: str
    max_concurrent_evaluations: int
    question_timeout_seconds: int
    retry_attempts: int
    log_level: str
    # New: Question persistence settings
    question_batch_size: int = 1          # Save immediately for research
    progress_update_interval: int = 10    # Update progress every N questions
```

### 12-Factor Compliance

- **Environment Variables:** All external dependencies configurable
- **No Hardcoded Values:** All settings externalized
- **Environment Parity:** Same config structure across dev/staging/prod

---

## Implementation Checklist

- [x] Define application service interfaces
- [x] Implement transaction boundary management per question (TransactionManager)
- [x] Create error mapping from external APIs to domain failures (ApplicationErrorMapper)
- [x] Set up incremental question persistence patterns (EvaluationOrchestrator)
- [x] Implement validation pipeline across all layers (ValidationResult DTOs)
- [x] Configure logging and monitoring integration
- [x] Create configuration management system
- [x] Set up repository dependency injection (dependency injection container)
- [x] Add QuestionResultRepository integration
- [x] Implement interruption and resume capabilities
- [x] Create real-time progress tracking from saved results

## Testing Implementation

The application services layer includes comprehensive high-value testing focusing on critical business workflows and incremental persistence patterns.

### Test Structure

```
tests/unit/application/
├── conftest.py              # Application layer fixtures and mocks
├── test_dtos.py            # DTO property calculations and validation
├── test_error_mapper.py    # External API error mapping
├── test_evaluation_orchestrator.py  # Core orchestration workflows
├── test_question_persistence.py    # Individual question saving patterns
└── test_integration.py     # Service coordination and end-to-end flows
```

### Testing Approach

**Pragmatic Testing Strategy**: Focus on high-value scenarios including incremental persistence patterns:

- **Critical Business Workflows**: Evaluation creation, execution, and completion
- **Incremental Persistence**: Individual question saving and retrieval
- **Interruption Handling**: Graceful interruption and resume capabilities
- **Error Handling**: External service failures, validation errors, network issues
- **Integration Points**: Service coordination, repository interactions, async operations
- **DTO Calculations**: Progress tracking, accuracy percentages, time estimates

### Key Test Examples

**Incremental Question Persistence Testing**:

```python
async def test_evaluation_execution_saves_each_question(self, orchestrator, sample_evaluation):
    # Setup
    questions = sample_benchmark.questions
    mock_reasoning_agent.answer_question.return_value = sample_answer

    # Execute
    await orchestrator.execute_evaluation(evaluation_id)

    # Verify each question was saved individually
    assert mock_question_result_repository.save.call_count == len(questions)

    # Verify evaluation completed successfully
    final_evaluation = mock_evaluation_repository.save.call_args_list[-1][0][0]
    assert final_evaluation.status == "completed"
```

**Interruption and Resume Testing**:

```python
async def test_evaluation_resume_from_interruption(self, orchestrator):
    # Setup interrupted evaluation with partial results
    partial_results = [create_question_result(i) for i in range(50)]
    mock_question_result_repository.get_by_evaluation_id.return_value = partial_results

    # Resume
    await orchestrator.resume_evaluation(evaluation_id)

    # Verify it continues from question 51
    remaining_calls = mock_reasoning_agent.answer_question.call_count
    assert remaining_calls == 100  # 150 total - 50 completed
```

**Progress Tracking Testing**:

```python
def test_progress_info_from_saved_results(self, sample_question_results):
    progress = ProgressInfo.from_question_results(
        evaluation_id, evaluation, sample_question_results, total_questions=150
    )

    assert progress.current_question == 42
    assert progress.completion_percentage == 28.0
    assert progress.success_rate == pytest.approx(90.5, rel=1e-2)
```

### Test Results

- **389+ tests passing** across domain, application, and infrastructure layers
- **Quality gates passing**: pytest, mypy, black, ruff
- **Incremental persistence coverage**: Question-level transaction testing
- **Integration coverage**: End-to-end workflow validation with individual question persistence

## See Also

- **[Domain Model](v2-domain-model.md)** - Business entities coordinated by these application services
- **[Core Behaviors](v2-core-behaviour-definition.md)** - User workflows orchestrated by these services
- **[Infrastructure Requirements](v2-infrastructure-requirements.md)** - External system integrations used by services
- **[Data Model](v2-data-model.md)** - Persistence patterns implemented by repositories
- **[Project Structure](v2-project-structure.md)** - Service layer organization and dependencies
