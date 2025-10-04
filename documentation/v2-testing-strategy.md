# ML Agents v2 Testing Strategy

**Version:** 1.2
**Date:** 2025-10-04
**Purpose:** Dual testing approach for research platform reliability and non-deterministic response handling

## Overview

ML Agents v2 employs a dual testing strategy that separates rapid development feedback from comprehensive behavior validation:

1. **Quality Gates**: Fast, focused checks ensuring code quality, type safety, and architectural integrity
2. **BDD Tests**: Comprehensive behavior-driven tests validating complete user workflows and system integration

This separation allows developers to iterate quickly with quality gates while maintaining thorough validation through BDD tests when needed.

## Testing Approaches

### Quality Gates (`make quality-gates`)

**Purpose**: Rapid validation of code quality and architectural patterns

**Components**:
- **Type checking** (mypy): Domain/infrastructure boundary enforcement
- **Code formatting** (black): Consistent style
- **Linting** (ruff): Code quality and best practices
- **Fast unit tests** (pytest subset): Critical domain logic only

**Execution**: < 30 seconds for complete suite

**When to run**:
- Before every commit (required)
- During active development (recommended)
- In CI/CD pipeline (automated)

**Coverage focus**:
- Domain entity invariants and business rules
- Value object equality and validation
- Factory pattern correct usage
- Interface contract compliance

### BDD Tests (`make bdd-tests`)

**Purpose**: Comprehensive behavior validation against specifications

**Components**:
- **Feature tests**: Complete user workflows from CLI to database
- **Integration tests**: Cross-layer service coordination
- **Error scenario tests**: Failure mode handling and recovery
- **Non-deterministic response tests**: LLM output pattern validation

**Execution**: 2-5 minutes for complete suite

**When to run**:
- Before pull requests (required)
- After architectural changes (required)
- When modifying user-facing features (recommended)
- Full regression validation (as needed)

**Coverage focus**:
- End-to-end evaluation workflows
- Multi-provider client integration
- Parser strategy selection
- Error translation across ACL boundaries

## Testing Philosophy

### Research Platform Requirements

The testing strategy ensures the platform reliably executes researcher workflows without validating LLM output quality:

- **Workflow Reliability**: Evaluation pipelines execute consistently from CLI to database
- **Data Integrity**: Responses captured and stored exactly as received from LLM
- **Failure Transparency**: API errors correctly translated to domain FailureReasons
- **Configuration Fidelity**: Agent configs (type, model, provider, strategy) applied correctly

**Important**: The system does not validate LLM response quality or reasoning correctness. It processes whatever the LLM returns according to the configured agent type and saves results for researcher analysis.

## Quality Gates Tests

**Focus**: Fast, isolated validation of code quality and domain logic correctness

**Characteristics**:
- No external dependencies (no API calls, no database)
- Execution time: < 30 seconds total
- Run before every commit
- Validates architectural patterns and business rules

### Domain Entity Business Rules

```python
def test_evaluation_lifecycle_transitions():
    """Evaluation must transition through valid states only"""
    evaluation = Evaluation.create(agent_config, benchmark_id)
    assert evaluation.status == EvaluationStatus.PENDING

    evaluation.start_execution()
    assert evaluation.status == EvaluationStatus.RUNNING

    evaluation.complete_with_results(results)
    assert evaluation.status == EvaluationStatus.COMPLETED

def test_evaluation_business_rules():
    """Cannot modify completed evaluation"""
    completed_evaluation = create_completed_evaluation()

    with pytest.raises(BusinessRuleViolation):
        completed_evaluation.start_execution()
```

### Value Object Validation

```python
def test_agent_config_equality():
    """AgentConfig uses value equality, not reference equality"""
    config1 = AgentConfig(agent_type="cot", model="claude-3-sonnet")
    config2 = AgentConfig(agent_type="cot", model="claude-3-sonnet")

    assert config1.equals(config2)  # Value equality
    assert config1 is not config2   # Different instances

def test_failure_reason_categorization():
    """FailureReason correctly categorizes error types"""
    timeout_failure = FailureReason.network_timeout("Request timed out")
    assert timeout_failure.category == "network_timeout"
    assert timeout_failure.recoverable == True
```

### Domain Service Factory Logic

```python
def test_reasoning_agent_factory():
    """ReasoningAgentServiceFactory returns correct agent implementations"""
    factory = ReasoningAgentServiceFactory()

    cot_agent = factory.create_service("chain_of_thought")
    assert cot_agent.get_agent_type() == "chain_of_thought"

    # Test invalid agent type
    with pytest.raises(UnsupportedAgentType):
        factory.create_service("unknown_agent")
```

## BDD Tests

**Focus**: Complete system behavior validation across all layers

**Characteristics**:
- Tests complete workflows from CLI to database
- Includes external system integration (mocked providers)
- Execution time: 2-5 minutes total
- Run before pull requests and after architectural changes
- Validates user-facing features and cross-layer coordination

### Complete Evaluation Workflows

```python
def test_complete_evaluation_workflow():
    """Given agent config, when running evaluation, then results saved to database"""
    runner = CliRunner()

    # Create evaluation via CLI
    create_result = runner.invoke(cli, [
        'evaluate', 'create',
        '--agent', 'cot',
        '--model', 'anthropic/claude-3-sonnet',
        '--benchmark', 'GPQA'
    ])
    assert create_result.exit_code == 0
    eval_id = extract_evaluation_id(create_result.output)

    # Run evaluation with mocked LLM responses
    with mock_llm_client_factory():
        run_result = runner.invoke(cli, ['evaluate', 'run', eval_id])
        assert run_result.exit_code == 0
        assert "Completed:" in run_result.output

    # Verify results persisted in database
    list_result = runner.invoke(cli, ['evaluate', 'list'])
    assert eval_id in list_result.output
```

### Multi-Provider Client Integration

```python
@patch.object(LLMClientFactory, 'create_client')
async def test_openrouter_provider_selection(mock_create_client, orchestrator):
    """Given OpenRouter provider, when executing evaluation, then OpenRouter client created"""

    mock_client = AsyncMock(spec=LLMClient)
    mock_client.chat_completion.return_value = LLMResponse(
        content='{"answer": "Paris"}',
        structured_data={"answer": "Paris"}
    )
    mock_create_client.return_value = mock_client

    agent_config = AgentConfig(
        agent_type="cot",
        model_name="anthropic/claude-3-sonnet",
        provider="openrouter"
    )

    await orchestrator.execute_evaluation(evaluation_id)

    # Verify factory called with OpenRouter provider
    mock_create_client.assert_called_with(
        model_name="anthropic/claude-3-sonnet",
        provider="openrouter",
        parsing_strategy="auto"
    )
```

### Parser Strategy Selection

```python
@patch.object(OpenRouterClient, 'chat_completion')
async def test_outlines_parser_uses_response_format(mock_chat):
    """Given PARSING_STRATEGY=outlines, when calling API, then uses response_format"""

    mock_chat.return_value = LLMResponse(
        content='{"answer": "Test"}',
        structured_data={"answer": "Test"}
    )

    # Create real factory with outlines strategy
    factory = LLMClientFactoryImpl(
        provider_configs={"openrouter": {"api_key": api_key, "base_url": base_url}},
        default_provider="openrouter",
        default_parsing_strategy="outlines"
    )
    client = factory.create_client(
        model_name="anthropic/claude-3-sonnet",
        provider="openrouter",
        parsing_strategy="outlines"
    )

    await client.chat_completion(messages, model="anthropic/claude-3-sonnet")

    # Verify Outlines uses response_format
    call_kwargs = mock_chat.call_args[1]
    assert 'response_format' in call_kwargs
    assert call_kwargs['response_format']['type'] == 'json_schema'
```

### Error Translation Across ACL Boundaries

```python
async def test_api_error_to_failure_reason_translation():
    """Given API error, when processing question, then FailureReason saved to database"""

    # Simulate rate limit error from OpenRouter
    with mock_rate_limit_error():
        runner = CliRunner()
        result = runner.invoke(cli, ['evaluate', 'run', evaluation_id])

    # Verify error translated to domain FailureReason
    evaluation = get_evaluation_from_db(evaluation_id)
    assert evaluation.status == "failed"
    assert evaluation.failure_reason.category == "rate_limit_exceeded"
    assert evaluation.failure_reason.recoverable == True
```

### Repository Persistence Integration

```python
def test_evaluation_question_result_persistence():
    """Given evaluation execution, when questions processed, then individual results saved"""

    repo = EvaluationQuestionResultRepositoryImpl(db_session)
    orchestrator = create_orchestrator_with_mocked_llm()

    # Execute evaluation
    await orchestrator.execute_evaluation(evaluation_id)

    # Verify individual question results persisted
    results = repo.get_by_evaluation_id(evaluation_id)
    assert len(results) == 10  # All questions saved
    assert all(r.is_correct is not None for r in results)
    assert all(r.execution_time > 0 for r in results)
```

## Test Data and Mocking

### Quality Gates Test Fixtures

**Focus**: Simple domain objects, no external dependencies

```python
@pytest.fixture
def sample_agent_config():
    """Domain value object for testing business rules"""
    return AgentConfig(
        agent_type="chain_of_thought",
        model_name="anthropic/claude-3-sonnet",
        model_parameters={"temperature": 1.0, "max_tokens": 1000}
    )

@pytest.fixture
def sample_evaluation():
    """Domain entity for testing state transitions"""
    return Evaluation.create(
        agent_config=sample_agent_config(),
        preprocessed_benchmark_id=uuid4()
    )

@pytest.fixture
def sample_questions():
    """Value objects for testing domain logic"""
    return [
        Question(id="1", text="What is 2+2?", expected_answer="4"),
        Question(id="2", text="Capital of France?", expected_answer="Paris")
    ]
```

### BDD Test Fixtures

**Focus**: Integration fixtures with mocked external systems

```python
@pytest.fixture
def test_database():
    """In-memory database for integration testing"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine)
    Base.metadata.drop_all(engine)

@pytest.fixture
def mock_llm_client_factory():
    """Factory returning mocked LLM clients"""
    with patch.object(LLMClientFactory, 'create_client') as mock:
        mock_client = AsyncMock(spec=LLMClient)
        mock_client.chat_completion.return_value = LLMResponse(
            content='{"answer": "Paris"}',
            structured_data={"answer": "Paris"}
        )
        mock.return_value = mock_client
        yield mock

@pytest.fixture
def orchestrator_with_mocks(test_database, mock_llm_client_factory):
    """Fully configured orchestrator for workflow testing"""
    return EvaluationOrchestrator(
        evaluation_repository=EvaluationRepositoryImpl(test_database),
        question_result_repository=QuestionResultRepositoryImpl(test_database),
        llm_client_factory=mock_llm_client_factory,
        domain_service_registry=create_domain_service_registry()
    )
```

### LLM Client Factory Mocking Strategy

**Mock at Factory Level**: Mock `LLMClientFactory.create_client()` to return controlled clients while testing orchestration logic.

```python
# Mock LLMClientFactory to return controlled client implementations
@patch.object(LLMClientFactory, 'create_client')
async def test_multi_provider_orchestration(mock_create_client, orchestrator):
    """Test evaluation orchestration with factory-created clients"""

    # Arrange - Mock factory returns client with controlled responses
    mock_client = AsyncMock(spec=LLMClient)
    mock_client.chat_completion.return_value = LLMResponse(
        content='{"answer": "Paris"}',
        structured_data={"answer": "Paris"},
        has_structured_data=lambda: True
    )
    mock_create_client.return_value = mock_client

    # Act - Orchestrator uses factory to create client based on agent config
    result = await orchestrator.execute_evaluation(evaluation_id)

    # Assert - Verify factory was called with correct parameters
    mock_create_client.assert_called_once_with(
        model_name="anthropic/claude-3-sonnet",
        provider="openrouter",
        parsing_strategy="auto"
    )
    assert result.status == "completed"
```

**For Provider-Specific Testing**: Mock at provider client level to test provider integration:

```python
@patch.object(OpenRouterClient, 'chat_completion')
async def test_openrouter_provider_integration(mock_chat):
    """Test OpenRouter-specific client behavior"""

    mock_chat.return_value = LLMResponse(
        content='{"answer": "Paris"}',
        structured_data={"answer": "Paris"}
    )

    # Test with real factory, mocked provider
    factory = LLMClientFactoryImpl(
        provider_configs={"openrouter": {"api_key": "test-key", "base_url": "https://test.com"}},
        default_provider="openrouter"
    )
    client = factory.create_client(
        model_name="anthropic/claude-3-sonnet",
        provider="openrouter",
        parsing_strategy="outlines"
    )

    result = await client.chat_completion(messages, model="anthropic/claude-3-sonnet")

    # Verify provider-specific behavior
    assert mock_chat.called
    call_kwargs = mock_chat.call_args[1]
    assert 'response_format' in call_kwargs  # Outlines strategy
```

**Key Principles**:
- **Mock at Factory Boundary**: Mock `LLMClientFactory.create_client()` for orchestration tests
- **Mock at Provider Boundary**: Mock provider clients (OpenRouterClient, etc.) for integration tests
- **Test Real Logic**: Factory selection logic, parsing strategy application, error handling
- **Verify Configuration**: Test that model/provider/strategy combinations work correctly

### Structured Output Parsing Testing

**BDD Tests for Parser Behavior**: Focus on testing parsing strategy selection and error handling behavior rather than implementation details.

```python
# Test factory-based parser selection
@patch.object(LLMClientFactory, 'create_client')
async def test_outlines_parser_selection(mock_create_client):
    """Given PARSING_STRATEGY=outlines, when creating client, then uses Outlines parser"""

    mock_client = AsyncMock(spec=LLMClient)
    mock_client.chat_completion.return_value = LLMResponse(
        content='{"answer": "Test answer"}',
        structured_data={"answer": "Test answer"}
    )
    mock_create_client.return_value = mock_client

    with patch.dict(os.environ, {'PARSING_STRATEGY': 'outlines'}):
        config = get_config()
        orchestrator = create_orchestrator_with_factory(config)

        result = await orchestrator.execute_evaluation(eval_id)

    # Verify factory was called with outlines strategy
    mock_create_client.assert_called_with(
        model_name=ANY,
        provider="openrouter",
        parsing_strategy="outlines"
    )

@patch.object(OpenRouterClient, 'chat_completion')
async def test_marvin_strategy_uses_internal_agent_type(mock_chat):
    """Given MarvinClient, when calling API, then uses _internal_agent_type"""

    mock_chat.return_value = LLMResponse(
        content='Direct response',
        structured_data={"answer": "Test answer"}
    )

    # Create real factory to test Marvin parser integration
    factory = LLMClientFactoryImpl(
        provider_configs={"openrouter": {"api_key": "test-key", "base_url": "https://test.com"}},
        default_provider="openrouter",
        default_parsing_strategy="marvin"
    )
    client = factory.create_client(
        model_name="anthropic/claude-3-sonnet",
        provider="openrouter",
        parsing_strategy="marvin"
    )

    await client.chat_completion(messages, model="anthropic/claude-3-sonnet")

    # Verify MarvinClient behavior (uses _internal_agent_type)
    call_kwargs = mock_chat.call_args[1]
    assert '_internal_agent_type' in call_kwargs
    assert 'response_format' not in call_kwargs

# Test error translation across the ACL boundary
@patch.object(OpenRouterClient, 'chat_completion')
async def test_parser_exception_translation_to_failure_reason(mock_chat):
    """Given parser fails, when execute_reasoning, then returns FailureReason"""

    # Simulate API returning empty content (causes parsing failure)
    mock_chat.return_value = LLMResponse(
        content="",
        structured_data=None,
        has_structured_data=lambda: False
    )

    result = await reasoning_service.execute_reasoning(domain_service, question, config)

    # Verify ACL translation
    assert isinstance(result, FailureReason)
    assert result.category == "parsing_error"
    assert "failed at" in result.description
```

**What NOT to Mock**:
- ❌ `LLMClientFactory.create_client()` logic (test real factory when possible)
- ❌ Parser selection based on strategy configuration
- ❌ Environment variable configuration loading
- ❌ Error translation from `ParserException` to `FailureReason`

**What TO Mock**:
- ✅ `LLMClientFactory.create_client()` return value for orchestration tests
- ✅ Provider clients (`OpenRouterClient.chat_completion()`) for integration tests
- ✅ Database operations
- ✅ File system operations

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

### Dual Execution Modes

**Quality Gates (`make quality-gates`)**:
- **Execution time**: < 30 seconds total
- **When to run**: Before every commit (required), during active development
- **Components**:
  - mypy (type checking)
  - black (formatting)
  - ruff (linting)
  - pytest -m unit (domain layer only)
- **Focus**: Code quality, architectural patterns, domain logic

**BDD Tests (`make bdd-tests`)**:
- **Execution time**: 2-5 minutes total
- **When to run**: Before pull requests (required), after architectural changes
- **Components**:
  - pytest (all integration and acceptance tests)
  - Complete workflow validation
  - Cross-layer integration
- **Focus**: System behavior, user workflows, data persistence

### Coverage Goals

**Quality Gates Coverage**:
- Domain entities: 95% minimum (business rules, state transitions)
- Domain services: 90% minimum (factory logic, validation)
- Value objects: 100% (equality, categorization, validation)

**BDD Tests Coverage**:
- Application orchestration: 90% minimum (workflow coordination)
- Infrastructure integration: 80% minimum (repository, API clients)
- CLI commands: 95% minimum (user-facing features)

**Overall**: 90% project coverage target with dual approach ensuring both code quality and behavior validation

### Current Testing Status

- ✅ **Quality Gates**: Passing (mypy, black, ruff, domain unit tests)
- ⚠️ **BDD Tests**: 4/8 failing (requires factory architecture implementation)
- 📋 **Action Required**: Implement LLMClientFactory to fix BDD test failures

## See Also

- **[Core Behaviors](v2-core-behaviour-definition.md)** - User workflows requiring test validation
- **[Application Services Architecture](v2-application-services-architecture.md)** - Service coordination patterns to test
- **[Reasoning Domain Logic](v2-reasoning-domain-logic.md)** - Domain logic patterns requiring validation
- **[Project Structure](v2-project-structure.md)** - Test organization framework
- **[CLI Design](v2-cli-design.md)** - Command interface testing requirements

---

_This testing strategy provides focused coverage while accommodating the unique challenges of testing a research platform with non-deterministic LLM responses._
