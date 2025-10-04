# ML Agents v2 Data Model Specification

**Version:** 1.1
**Date:** 2025-09-28
**Purpose:** Define data structures for individual question-answer persistence

## Core Data Entities

### Evaluation (Aggregate Root)

```python
Evaluation {
    evaluation_id: UUID                    # Primary key
    agent_config: AgentConfig              # Embedded value object
    preprocessed_benchmark_id: UUID        # Foreign key reference
    status: EvaluationStatus               # Enum: pending, running, completed, failed, interrupted
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    failure_reason: FailureReason | None   # Complex object when failed
}
```

**Storage Decisions:**

- `agent_config`: Store as JSON to preserve value object semantics
- `failure_reason`: Store as JSON with category field extracted for querying
- **Results removed**: Now computed dynamically from question results table

### EvaluationQuestionResult (New Entity)

```python
EvaluationQuestionResult {
    id: UUID                               # Primary key
    evaluation_id: UUID                    # Foreign key to evaluations
    question_id: str                       # Question identifier within benchmark
    question_text: str                     # Question content
    expected_answer: str                   # Ground truth answer
    actual_answer: str                     # Agent's extracted answer
    is_correct: bool                       # Correctness evaluation
    execution_time: float                  # Seconds taken to process
    reasoning_trace_json: str              # ReasoningTrace object as JSON
    error_message: str | None              # If question processing failed
    processed_at: datetime                 # When question was completed
}
```

**Storage Decisions:**

- One row per question-answer pair for incremental persistence
- Preserve complex objects (ReasoningTrace) as JSON
- Enable graceful interruption and resume capabilities

### PreprocessedBenchmark (Aggregate Root)

```python
PreprocessedBenchmark {
    benchmark_id: UUID                     # Primary key
    name: str                              # Unique constraint
    description: str
    questions: List[Question]              # Stored as JSON array
    metadata: Dict[str, Any]               # JSON object
    created_at: datetime
    question_count: int                    # Derived field for performance
    format_version: str                    # For evolution support
}
```

**Storage Decisions:**

- `questions`: JSON array for benchmark definition
- Individual question results stored separately in evaluation_question_results

## Value Objects

### AgentConfig

```python
AgentConfig {
    agent_type: str                        # none, cot, pot, etc.
    model_provider: str                    # openrouter
    model_name: str                        # claude-3-sonnet, gpt-4, etc.
    model_parameters: Dict[str, Any]       # temperature, max_tokens, etc.
    agent_parameters: Dict[str, Any]       # agent-specific config
}
```

**Storage Strategy:** Embedded JSON in evaluations table with hash for deduplication queries

### Question

```python
Question {
    id: str                                # Question identifier within benchmark
    text: str                              # Question content
    expected_answer: str                   # Ground truth
    metadata: Dict[str, Any]               # Optional: difficulty, category, etc.
}
```

### EvaluationResults (Computed Value Object)

```python
EvaluationResults {
    total_questions: int                   # Computed from question results
    correct_answers: int                   # Computed from question results
    accuracy: float                        # Computed field
    average_execution_time: float          # Computed from question results
    error_count: int                       # Computed from question results
    detailed_results: List[QuestionResult] # Loaded from question results table
    summary_statistics: Dict[str, Any]     # Additional computed metrics
}
```

**Computation Pattern:**

```python
@classmethod
def from_database(cls, evaluation_id: UUID, question_repo: QuestionResultRepository) -> 'EvaluationResults':
    """Compute evaluation results from individual question records"""
    question_results = question_repo.get_by_evaluation_id(evaluation_id)

    return cls(
        total_questions=len(question_results),
        correct_answers=sum(1 for q in question_results if q.is_correct),
        accuracy=correct_answers / total_questions if total_questions > 0 else 0.0,
        average_execution_time=sum(q.execution_time for q in question_results) / total_questions,
        error_count=sum(1 for q in question_results if q.error_message),
        detailed_results=question_results,
        summary_statistics={}
    )
```

### FailureReason

```python
FailureReason {
    category: FailureCategory              # Enum for querying
    description: str                       # Human-readable
    technical_details: str                 # Raw error info
    occurred_at: datetime
    recoverable: bool                      # Whether retry might work
}

FailureCategory = Enum[
    "parsing_error",
    "token_limit_exceeded",
    "content_guardrail",
    "model_refusal",
    "network_timeout",
    "unknown"
]
```

## Data Relationships and Constraints

### Primary Relationships

- `Evaluation` â†' `PreprocessedBenchmark` (many-to-one)
- `Evaluation` â†' `EvaluationQuestionResult` (one-to-many)
- `Evaluation` contains `AgentConfig` (embedded)
- `Evaluation` contains `FailureReason` (embedded when failed)
- `EvaluationResults` computed from `EvaluationQuestionResult` records

### Key Constraints

1. **Evaluation Status Logic:**

   - `failure_reason` must be NULL unless `status = 'failed'`
   - `started_at` must be NULL if `status = 'pending'`
   - `completed_at` must be NULL unless `status IN ('completed', 'failed', 'interrupted')`

2. **Question Result Integrity:**

   - `(evaluation_id, question_id)` must be unique
   - `evaluation_id` must reference existing evaluation
   - `processed_at` must be after evaluation `started_at`

3. **AgentConfig Validation:**

   - `model_parameters` must be valid JSON object
   - `agent_parameters` must be valid JSON object
   - `agent_type` must be in supported types list

4. **Benchmark Integrity:**
   - `name` must be unique across all benchmarks
   - `question_count` must equal `len(questions)`
   - All questions must have non-empty `text` and `expected_answer`

## Database Schema

### Core Tables

```sql
-- Evaluations table (simplified)
CREATE TABLE evaluations (
    evaluation_id UUID PRIMARY KEY,
    agent_config_json TEXT NOT NULL,
    preprocessed_benchmark_id UUID NOT NULL REFERENCES preprocessed_benchmarks(benchmark_id),
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'running', 'completed', 'failed', 'interrupted')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    failure_reason_json TEXT
);

-- New question results table
CREATE TABLE evaluation_question_results (
    id UUID PRIMARY KEY,
    evaluation_id UUID NOT NULL REFERENCES evaluations(evaluation_id) ON DELETE CASCADE,
    question_id VARCHAR(50) NOT NULL,
    question_text TEXT NOT NULL,
    expected_answer TEXT NOT NULL,
    actual_answer TEXT NOT NULL,
    is_correct BOOLEAN NOT NULL,
    execution_time FLOAT NOT NULL,
    reasoning_trace_json TEXT,
    error_message TEXT,
    processed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(evaluation_id, question_id)
);

-- Preprocessed benchmarks table (unchanged)
CREATE TABLE preprocessed_benchmarks (
    benchmark_id UUID PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT NOT NULL,
    questions_json TEXT NOT NULL,
    metadata_json TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    question_count INTEGER NOT NULL,
    format_version VARCHAR(20) NOT NULL
);
```

## Indexing Strategy

### Performance-Critical Queries

```sql
-- Find evaluations by status
CREATE INDEX idx_evaluations_status ON evaluations(status);

-- Find evaluations by benchmark
CREATE INDEX idx_evaluations_benchmark ON evaluations(preprocessed_benchmark_id);

-- Find benchmarks by name
CREATE UNIQUE INDEX idx_benchmarks_name ON preprocessed_benchmarks(name);

-- Query evaluations by agent configuration similarity
CREATE INDEX idx_evaluations_agent_hash ON evaluations(agent_config_hash);

-- NEW: Question results by evaluation (most common query)
CREATE INDEX idx_question_results_evaluation ON evaluation_question_results(evaluation_id);

-- NEW: Question results by correctness for analytics
CREATE INDEX idx_question_results_correctness ON evaluation_question_results(is_correct);

-- NEW: Question results by processing time
CREATE INDEX idx_question_results_processed_at ON evaluation_question_results(processed_at);
```

### JSON Field Indexing (SQLite 3.45+ / PostgreSQL)

```sql
-- Index failure categories for filtering
CREATE INDEX idx_evaluations_failure_category
ON evaluations(json_extract(failure_reason_json, '$.category'));

-- Index agent types for analysis
CREATE INDEX idx_evaluations_agent_type
ON evaluations(json_extract(agent_config_json, '$.agent_type'));

```

## Data Size Estimates

### Typical Object Sizes

- `AgentConfig`: ~200-500 bytes (JSON)
- `EvaluationQuestionResult`: ~1-5KB per record (depends on reasoning length)
- `ReasoningTrace`: ~500-3000 bytes (depends on approach)

### Storage Projections

- 1000 evaluations with 150 questions each = 150,000 question result records
- Average 2KB per question result = ~300MB for question results
- Evaluation metadata: 1000 × 1KB = ~1MB
- Benchmark data: 50 × 10MB = ~500MB
- **Total: ~800MB for substantial research dataset**

### Performance Characteristics

- Individual question insert: ~1ms
- Evaluation summary computation: ~10-50ms (depending on question count)
- Cross-evaluation analytics: ~100-500ms (with proper indexing)

## Migration and Evolution Strategy

### Schema Versioning

- `format_version` field in benchmarks supports data migration
- JSON fields provide flexibility for adding new attributes
- Individual question records enable granular data evolution

### Backward Compatibility

- New reasoning approaches add to existing enums
- Additional metrics extend JSON objects without breaking existing queries
- Agent config evolution through versioned parameter schemas

## Data Integrity Patterns

### Transactional Boundaries

- **Question Processing**: Individual question result as single transaction
- **Evaluation State Updates**: Separate transaction for status changes
- **Summary Computation**: Read-only aggregation queries

### Validation Layers

1. **Domain Level:** Entity and value object invariants
2. **Application Level:** Cross-aggregate consistency
3. **Database Level:** Constraints and foreign keys
4. **API Level:** Input validation and sanitization

## Benefits of Individual Question Persistence

### Incremental Progress

- Save each question result immediately upon completion
- No data loss on evaluation interruption or system crashes
- Resume evaluations from exact stopping point

### Real-time Analytics

- Track evaluation progress with actual saved results
- Compute running accuracy during evaluation execution
- Enable early stopping based on interim performance

### Cross-evaluation Analysis

- Compare question-level performance across different agents
- Analyze question difficulty patterns across models
- Identify systematic failure modes in reasoning approaches

### Research Workflow Enhancement

- Partial evaluation results have independent research value
- Question-level error analysis for debugging reasoning approaches
- Flexible evaluation scheduling and resource management

## See Also

- **[Domain Model](v2-domain-model.md)** - Business entity definitions implemented in this data model
- **[Infrastructure Requirements](v2-infrastructure-requirements.md)** - Database technology and configuration details
- **[Application Services Architecture](v2-application-services-architecture.md)** - Service patterns using this data model
- **[Project Structure](v2-project-structure.md)** - Repository implementation organization
