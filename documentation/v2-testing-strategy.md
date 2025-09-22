# ML Agents v2 Testing Strategy

**Version:** 1.1
**Date:** 2025-09-17
**Purpose:** Testing approach for research platform reliability and non-deterministic response handling

## Overview

The ML Agents v2 testing strategy prioritizes research workflow validation while accommodating LLM response variability. Unlike traditional software testing focused on deterministic outputs, our approach validates reasoning patterns, evaluation accuracy, and platform reliability.

## Testing Philosophy

### Research Platform Requirements

- **Workflow Reliability**: Evaluation pipelines execute consistently
- **Data Integrity**: Results accurately captured and stored
- **Failure Transparency**: Error conditions clearly diagnosed
- **Pattern Validation**: Reasoning traces follow expected structures

### Non-Deterministic Response Handling

- **Structure over Content**: Validate response format rather than exact text
- **Pattern Recognition**: Check reasoning traces contain expected elements
- **Answer Extraction**: Verify clean answer separation from reasoning
- **Error Classification**: Ensure failure reasons properly categorized

## Test Categories

### 1. Unit Tests (Domain Layer)

**Focus**: Pure business logic validation

**Domain Entity Tests**:

```python
def test_evaluation_lifecycle_transitions():
    evaluation = Evaluation.create(agent_config, benchmark_id)
    assert evaluation.status == EvaluationStatus.PENDING

    evaluation.start_execution()
    assert evaluation.status == EvaluationStatus.RUNNING

    evaluation.complete_with_results(results)
    assert evaluation.status == EvaluationStatus.COMPLETED

def test_evaluation_business_rules():
    completed_evaluation = create_completed_evaluation()

    # Cannot modify completed evaluation
    with pytest.raises(BusinessRuleViolation):
        completed_evaluation.start_execution()
```

**Value Object Tests**:

```python
def test_agent_config_equality():
    config1 = AgentConfig(agent_type="cot", model="claude-3-sonnet")
    config2 = AgentConfig(agent_type="cot", model="claude-3-sonnet")

    assert config1.equals(config2)  # Value equality
    assert config1 is not config2   # Different instances

def test_failure_reason_categorization():
    timeout_failure = FailureReason.network_timeout("Request timed out")
    assert timeout_failure.category == FailureCategory.NETWORK_TIMEOUT
    assert timeout_failure.recoverable == True
```

**Domain Service Tests**:

```python
def test_reasoning_agent_factory():
    factory = ReasoningAgentServiceFactory()

    cot_agent = factory.create_service("chain_of_thought")
    assert cot_agent.get_agent_type() == "chain_of_thought"

    # Test invalid agent type
    with pytest.raises(UnsupportedAgentType):
        factory.create_service("unknown_agent")
```

### 2. Integration Tests (Application Services) ✅ IMPLEMENTED

**Focus**: Service coordination and external system integration

**Implemented Test Structure**:
```
tests/unit/application/
├── conftest.py              # Application layer fixtures and mocks
├── test_dtos.py            # DTO calculations and validation
├── test_error_mapper.py    # Error mapping between layers
├── test_evaluation_orchestrator.py  # Core orchestration workflows
└── test_integration.py     # Service coordination patterns
```

**Pragmatic Testing Approach**: High-value tests focusing on critical business workflows rather than exhaustive coverage.

**Orchestration Tests** (Implemented):

```python
async def test_execute_evaluation_basic_workflow(self, orchestrator, sample_evaluation):
    # Arrange
    mock_evaluation_repository.get_by_id.return_value = sample_evaluation
    mock_benchmark_repository.get_by_id.return_value = sample_benchmark
    mock_reasoning_agent.answer_question.return_value = sample_answer

    # Act
    await orchestrator.execute_evaluation(evaluation_id)

    # Assert - Verify question processing
    assert mock_reasoning_agent.answer_question.call_count == len(sample_benchmark.questions)

    # Verify final evaluation state
    final_evaluation = mock_evaluation_repository.update.call_args_list[-1][0][0]
    assert final_evaluation.status == "completed"
    assert final_evaluation.results is not None
```

**DTO Validation Tests** (Implemented):

```python
def test_progress_info_calculations(self, sample_progress_info):
    # Test completion percentage
    assert sample_progress_info.completion_percentage == 60.0

    # Test success rate
    assert sample_progress_info.success_rate == pytest.approx(83.33, rel=1e-2)

    # Test time estimates
    elapsed = sample_progress_info.elapsed_minutes
    assert 4.5 <= elapsed <= 5.5
```

**Error Handling Integration** (Implemented):

```python
async def test_evaluation_execution_with_external_service_error(self, orchestrator):
    # Simulate OpenRouter API failure
    openrouter_error = Exception("503 Service Unavailable")
    mock_reasoning_agent.answer_question.side_effect = openrouter_error

    # Should raise EvaluationExecutionError due to failures
    with pytest.raises(EvaluationExecutionError):
        await orchestrator.execute_evaluation(evaluation_id)
```

**Repository Tests**:

```python
def test_evaluation_repository_persistence():
    repo = EvaluationRepositoryImpl(db_session)

    evaluation = Evaluation.create(agent_config, benchmark_id)
    repo.save(evaluation)

    retrieved = repo.get_by_id(evaluation.evaluation_id)
    assert retrieved.agent_config.equals(evaluation.agent_config)
```

**OpenRouter Integration Tests**:

```python
async def test_openrouter_error_mapping():
    client = OpenRouterClient(test_config)
    mapper = OpenRouterErrorMapper()

    rate_limit_error = RateLimitError("Rate limit exceeded")
    failure_reason = mapper.map_to_failure_reason(rate_limit_error)

    assert failure_reason.category == FailureCategory.RATE_LIMIT_EXCEEDED
    assert failure_reason.recoverable == True
```

### 3. Acceptance Tests (End-to-End) ✅ IMPLEMENTED

**Focus**: Complete user workflows and CLI interface

**Implemented Test Structure**:
```
tests/acceptance/
├── test_cli_basic.py           # Basic CLI functionality and help
├── test_health_command.py      # Health check command testing
├── test_benchmark_commands.py  # Benchmark list/show commands
└── test_evaluate_commands.py   # Comprehensive evaluate command testing
```

**CLI Testing Coverage**: 11 comprehensive test scenarios covering create/run/list workflows, error handling, filtering, and integration patterns.

**Research Workflow Tests**:

```python
def test_complete_evaluation_workflow():
    """Test researcher journey from creation to results"""
    runner = CliRunner()

    # Create evaluation
    create_result = runner.invoke(cli, [
        'evaluate', 'create',
        '--agent', 'cot',
        '--model', 'anthropic/claude-3-sonnet',
        '--benchmark', 'GPQA'
    ])
    assert create_result.exit_code == 0

    eval_id = extract_evaluation_id(create_result.output)

    # Run evaluation
    with mock_openrouter_responses():
        run_result = runner.invoke(cli, ['evaluate', 'run', eval_id])
        assert run_result.exit_code == 0
        assert "Completed:" in run_result.output

    # List evaluations
    list_result = runner.invoke(cli, ['evaluate', 'list'])
    assert eval_id in list_result.output
```

**CLI Error Handling Tests**:

```python
def test_cli_authentication_failure():
    with mock_authentication_failure():
        runner = CliRunner()
        result = runner.invoke(cli, ['evaluate', 'run', 'eval_123'])

        assert result.exit_code == 4  # Authentication error code
        assert "authentication failed" in result.output.lower()
```

## Non-Deterministic Response Testing

### Reasoning Pattern Validation

```python
def test_chain_of_thought_pattern():
    """Validate CoT responses contain reasoning steps"""
    cot_agent = ChainOfThoughtAgent(mock_client)

    answer = await cot_agent.process_question(question, config)

    # Validate reasoning structure
    assert answer.reasoning_trace.approach_type == "chain_of_thought"
    assert len(answer.reasoning_trace.reasoning_text) > 0

    # Check for reasoning indicators
    reasoning_text = answer.reasoning_trace.reasoning_text.lower()
    reasoning_indicators = ["step", "first", "then", "therefore"]
    assert any(indicator in reasoning_text for indicator in reasoning_indicators)

def test_none_agent_pattern():
    """Validate None approach has empty reasoning"""
    none_agent = NoneAgent(mock_client)

    answer = await none_agent.process_question(question, config)

    assert answer.reasoning_trace.approach_type == "none"
    assert answer.reasoning_trace.reasoning_text == ""
```

### Answer Extraction Testing

```python
def test_answer_extraction_patterns():
    """Test various answer formats are properly extracted"""
    test_cases = [
        ("The answer is 42", "42"),
        ("Therefore, the result is 3.14", "3.14"),
        ("Answer: Paris", "Paris"),
        ("42", "42"),  # Already clean
    ]

    for raw_response, expected_clean in test_cases:
        extracted = extract_answer(raw_response)
        assert extracted == expected_clean
```

## Test Data and Mocking

### Essential Fixtures

```python
@pytest.fixture
def sample_agent_config():
    return AgentConfig(
        agent_type="chain_of_thought",
        model_name="anthropic/claude-3-sonnet",
        model_parameters={"temperature": 1.0, "max_tokens": 1000}
    )

@pytest.fixture
def sample_benchmark():
    questions = [
        Question(id="1", text="What is 2+2?", expected_answer="4"),
        Question(id="2", text="Capital of France?", expected_answer="Paris")
    ]
    return PreprocessedBenchmark.create("TEST_BENCHMARK", questions)

@pytest.fixture
def test_database():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine)
    Base.metadata.drop_all(engine)
```

### OpenRouter Mocking Strategy

```python
class MockOpenRouterClient:
    def __init__(self, response_patterns=None):
        self.response_patterns = response_patterns or {}
        self.call_count = 0

    async def chat_completion(self, model, messages, **kwargs):
        self.call_count += 1

        # Return realistic but deterministic responses
        user_message = messages[-1]["content"]
        if "2+2" in user_message:
            return {"choices": [{"message": {"content": "2+2 equals 4"}}]}

        return {"choices": [{"message": {"content": "Mock response"}}]}
```

## Error Testing Patterns

### Failure Injection Testing

```python
def test_database_failure_recovery():
    """Test evaluation handling when database becomes unavailable"""

    with database_failure_injection():
        with pytest.raises(DatabaseUnavailableError):
            await orchestrator.execute_evaluation(eval_id)

def test_network_resilience():
    """Test handling of network failure modes"""
    failure_modes = ["connection_timeout", "read_timeout", "dns_failure"]

    for failure_mode in failure_modes:
        with network_failure_injection(failure_mode):
            result = await reasoning_agent.process_question(question)

            assert isinstance(result, FailureReason)
            assert result.category == FailureCategory.NETWORK_TIMEOUT
```

## Testing Tools

### Core Framework

- **pytest**: Primary testing framework
- **pytest-asyncio**: Async test support
- **pytest-mock**: Mocking utilities
- **click.testing**: CLI testing utilities
- **responses**: HTTP request mocking

### Custom Utilities

```python
class EvaluationFactory:
    @staticmethod
    def create_completed_evaluation(accuracy=0.95):
        # Create realistic evaluation with results

    @staticmethod
    def create_failed_evaluation(failure_type="network_timeout"):
        # Create evaluation with specific failure type
```

## Test Execution Strategy

### Test Categories

- **Unit Tests**: Fast, isolated tests (< 30 seconds total)
- **Integration Tests**: Service coordination and database tests
- **Acceptance Tests**: End-to-end CLI workflows

### Coverage Goals

- Domain Layer: 95% minimum ✅ (achieved with comprehensive unit tests)
- Application Services: 90% minimum ✅ (achieved with pragmatic high-value testing)
- Infrastructure Layer: 80% minimum ✅ (achieved with repository and integration tests)
- Overall Project: 90% target ✅ (427 tests passing across all layers)

### Current Testing Status

**Test Results**: 427 tests passing with full quality gate compliance:
- ✅ **pytest**: All tests passing
- ✅ **mypy**: Type checking clean
- ✅ **black**: Code formatting compliant
- ✅ **ruff**: Linting passed

**Implementation Notes**:
- **Pragmatic Approach**: Focused on high-value scenarios for application services rather than exhaustive coverage
- **Async Testing**: Proper AsyncMock usage for evaluation execution workflows
- **Integration Patterns**: Service coordination testing with mocked external dependencies
- **Error Handling**: Comprehensive error mapping and failure scenario testing

## See Also

- **[Core Behaviors](v2-core-behaviour-definition.md)** - User workflows requiring test validation
- **[Application Services Architecture](v2-application-services-architecture.md)** - Service coordination patterns to test
- **[Agents](v2-agents.md)** - Reasoning agent testing requirements
- **[Project Structure](v2-project-structure.md)** - Test organization framework
- **[CLI Design](v2-cli-design.md)** - Command interface testing requirements

---

_This testing strategy provides focused coverage while accommodating the unique challenges of testing a research platform with non-deterministic LLM responses._
