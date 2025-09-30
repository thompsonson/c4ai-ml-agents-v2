# ADR: Structured Exception Handling for Infrastructure JSON Serialization

**Status**: Accepted
**Date**: 2025-09-30
**Context**: Fix for mappingproxy JSON serialization error and broader untrusted data handling

## Problem Statement

The system encountered a JSON serialization error when persisting `EvaluationQuestionResult` entities to the database:

```
TypeError: Object of type mappingproxy is not JSON serializable
```

### Root Cause Analysis

1. **Immediate Issue**: `ReasoningTrace.metadata` field is converted to `MappingProxyType` for immutability in the domain layer, but `json.dumps()` cannot serialize this type in the infrastructure layer.

2. **Broader Context**: As a research platform, the system handles significant amounts of untrusted data:
   - LLM-generated responses and reasoning text
   - User-uploaded benchmark content
   - External API responses with varying structures
   - Experimental and potentially malformed data

3. **Current Risk**: Generic JSON serialization errors provide insufficient context for debugging and error recovery in a research environment.

## Decision

**Selected Approach**: Structured Exception Handling with Context

We will implement a custom `SerializationError` exception class that provides rich context about serialization failures, rather than relying on generic JSON errors or implementing data sanitization fallbacks.

### Rationale

1. **Research Platform Requirements**: Need detailed error context to understand and debug data quality issues from experimental LLM outputs and user content.

2. **Untrusted Data Reality**: All text fields (reasoning_text, question_text, technical_details, etc.) could contain problematic data, not just metadata.

3. **Operational Observability**: Structured exceptions enable better monitoring, logging, and error tracking in production.

4. **Clean Architecture Compliance**: Infrastructure layer handles serialization concerns without affecting domain logic or business rules.

5. **Graceful Failure**: System fails fast with actionable error messages rather than continuing with corrupted or incomplete data.

## Implementation Plan

### Phase 1: Core Infrastructure

#### 1.1 Create Structured Exception Class

**File**: `src/ml_agents_v2/infrastructure/database/exceptions.py`

```python
"""Database infrastructure exceptions."""

class SerializationError(Exception):
    """Raised when domain objects cannot be serialized for persistence.

    Provides structured context for debugging JSON serialization failures
    in the infrastructure layer when handling untrusted data from LLMs,
    user inputs, and external APIs.
    """

    def __init__(self, entity_type: str, entity_id: str, field_name: str, original_error: Exception):
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.field_name = field_name
        self.original_error = original_error

        super().__init__(
            f"Failed to serialize {field_name} for {entity_type} {entity_id}: {original_error}"
        )
```

#### 1.2 Apply to EvaluationQuestionResult Model

**File**: `src/ml_agents_v2/infrastructure/database/models/evaluation_question_result.py`

**Changes**:
1. Import the new exception class
2. Wrap reasoning_trace JSON serialization with error handling
3. Fix the immediate mappingproxy issue: `dict(question_result.reasoning_trace.metadata)`

```python
from ..exceptions import SerializationError

# In from_domain method:
try:
    reasoning_trace_json = json.dumps({
        "approach_type": question_result.reasoning_trace.approach_type,
        "reasoning_text": question_result.reasoning_trace.reasoning_text,
        "metadata": dict(question_result.reasoning_trace.metadata),  # Fix mappingproxy
    })
except (TypeError, ValueError, RecursionError) as e:
    raise SerializationError(
        entity_type="EvaluationQuestionResult",
        entity_id=str(question_result.id),
        field_name="reasoning_trace",
        original_error=e
    ) from e
```

### Phase 2: Comprehensive Coverage

#### 2.1 Apply to All Database Models

Extend structured exception handling to all models that perform JSON serialization:

- `EvaluationModel.from_domain()` - agent_config, results, failure_reason fields
- `BenchmarkModel.from_domain()` - questions, metadata fields
- Any future models with complex JSON fields

#### 2.2 Consistent Error Handling Pattern

For each JSON serialization point:
```python
try:
    field_json = json.dumps(data_structure)
except (TypeError, ValueError, RecursionError) as e:
    raise SerializationError(
        entity_type="EntityName",
        entity_id=str(entity.id),
        field_name="field_name",
        original_error=e
    ) from e
```

### Phase 3: Testing and Validation

#### 3.1 Test-Driven Development

**File**: `tests/unit/infrastructure/test_database_models.py`

Add comprehensive test coverage:

1. **Failing Test First**: Reproduce the original mappingproxy error
2. **Happy Path Tests**: Verify successful serialization after fix
3. **Error Condition Tests**: Test SerializationError with various bad data
4. **Context Validation**: Verify exception contains correct entity/field information

```python
def test_evaluation_question_result_mappingproxy_serialization_error(self):
    """Test that SerializationError is raised with proper context for mappingproxy metadata."""

def test_evaluation_question_result_serialization_various_bad_data(self):
    """Test SerializationError handling for different types of problematic data."""

def test_serialization_error_context_information(self):
    """Verify SerializationError provides correct entity and field context."""
```

#### 3.2 Quality Gates

- All existing tests must continue passing
- New tests must cover both success and failure scenarios
- Run `make quality-gates` to ensure no regressions
- Verify error messages provide actionable debugging information

### Phase 4: Monitoring and Observability

#### 4.1 Structured Logging

Ensure SerializationError instances are properly logged with structured context:

```python
logger.error(
    "Database serialization failed",
    extra={
        "entity_type": error.entity_type,
        "entity_id": error.entity_id,
        "field_name": error.field_name,
        "original_error_type": type(error.original_error).__name__,
        "original_error_message": str(error.original_error),
    }
)
```

#### 4.2 Error Recovery Guidance

Document common SerializationError scenarios and resolution steps for operators.

## Benefits

1. **Immediate Fix**: Resolves the mappingproxy JSON serialization error
2. **Rich Debugging Context**: Detailed error information for research platform troubleshooting
3. **Proactive Protection**: Guards against future serialization issues from untrusted data
4. **Clean Architecture**: Infrastructure concerns remain in infrastructure layer
5. **Operational Excellence**: Better monitoring and error tracking capabilities
6. **Research Platform Alignment**: Robust handling of experimental and varying data quality

## Risks and Mitigations

### Risk: Performance Impact
**Mitigation**: JSON serialization error handling only activates on failures, no performance impact on success path.

### Risk: Exception Handling Complexity
**Mitigation**: Consistent pattern across all models, simple try/catch with structured context.

### Risk: Incomplete Coverage
**Mitigation**: Systematic review of all `json.dumps()` calls in infrastructure layer during implementation.

## Alternative Approaches Considered

1. **Simple Fix Only**: Just convert mappingproxy to dict - rejected due to broader untrusted data concerns
2. **Data Sanitization with Fallback**: Sanitize bad data and continue - rejected as it could hide data quality issues important for research
3. **Domain Layer Validation**: Add JSON serialization validation to domain objects - rejected as violation of Clean Architecture separation of concerns

## Implementation Timeline

- **Phase 1**: Core infrastructure and immediate fix - 1 day
- **Phase 2**: Comprehensive model coverage - 1 day
- **Phase 3**: Testing and validation - 1 day
- **Phase 4**: Monitoring and documentation - 0.5 day

**Total**: 3.5 days

## Success Criteria

1. ✅ Original mappingproxy error is resolved
2. ✅ All existing functionality continues working
3. ✅ New SerializationError provides actionable debugging context
4. ✅ Comprehensive test coverage for both success and failure scenarios
5. ✅ Quality gates pass without regressions
6. ✅ Infrastructure layer properly handles all untrusted data serialization

---

**Decision Makers**: Development Team
**Stakeholders**: Research Platform Users, Operations Team