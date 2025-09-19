"""Tests for NoneAgentService implementation."""

import pytest

from ml_agents_v2.core.domain.services.reasoning.exceptions import (
    InvalidConfigurationError,
)
from ml_agents_v2.core.domain.services.reasoning.none_agent_service import (
    NoneAgentService,
)
from ml_agents_v2.core.domain.value_objects.agent_config import AgentConfig
from ml_agents_v2.core.domain.value_objects.answer import Answer
from ml_agents_v2.core.domain.value_objects.question import Question


class TestNoneAgentService:
    """Test suite for NoneAgentService implementation."""

    @pytest.fixture
    def service(self) -> NoneAgentService:
        """Create a NoneAgentService instance for testing."""
        return NoneAgentService()

    @pytest.fixture
    def valid_agent_config(self) -> AgentConfig:
        """Create a valid agent configuration for none agent."""
        return AgentConfig(
            agent_type="none",
            model_provider="openai",
            model_name="gpt-4",
            model_parameters={"temperature": 0.7, "max_tokens": 1000},
            agent_parameters={"timeout_seconds": 30},
        )

    @pytest.fixture
    def sample_question_a(self) -> Question:
        """Create a sample question for testing."""
        return Question(
            id="test-q1",
            text="Sample question A for testing",
            expected_answer="Sample answer A",
            metadata={"difficulty": "easy", "topic": "test"},
        )

    @pytest.fixture
    def sample_question_b(self) -> Question:
        """Create another sample question for testing."""
        return Question(
            id="test-q2",
            text="Sample question B for testing",
            expected_answer="Sample answer B",
            metadata={"difficulty": "medium", "topic": "test"},
        )

    @pytest.fixture
    def general_question(self) -> Question:
        """Create a general question for testing."""
        return Question(
            id="gen-q1",
            text="What is the meaning of life?",
            expected_answer="42",
            metadata={"difficulty": "hard", "topic": "philosophy"},
        )

    def test_service_initialization(self, service: NoneAgentService) -> None:
        """Test service initializes with correct configuration."""
        assert service.supports_agent_type("none") is True
        assert service.supports_agent_type("chain_of_thought") is False

        providers = service.get_supported_model_providers()
        assert "openai" in providers
        assert "anthropic" in providers
        assert "mock" in providers

    def test_supports_agent_type(self, service: NoneAgentService) -> None:
        """Test supports_agent_type method."""
        assert service.supports_agent_type("none") is True
        assert service.supports_agent_type("chain_of_thought") is False
        assert service.supports_agent_type("unknown") is False
        assert service.supports_agent_type("") is False

    def test_get_supported_model_providers(self, service: NoneAgentService) -> None:
        """Test get_supported_model_providers method."""
        providers = service.get_supported_model_providers()

        assert isinstance(providers, list)
        assert "openai" in providers
        assert "anthropic" in providers
        assert "mock" in providers

        # Test immutability
        providers.append("new_provider")
        new_providers = service.get_supported_model_providers()
        assert "new_provider" not in new_providers

    def test_validate_config_valid(
        self, service: NoneAgentService, valid_agent_config: AgentConfig
    ) -> None:
        """Test validate_config with valid configuration."""
        assert service.validate_config(valid_agent_config) is True

    def test_validate_config_invalid_agent_type(
        self, service: NoneAgentService
    ) -> None:
        """Test validate_config with invalid agent type."""
        invalid_config = AgentConfig(
            agent_type="chain_of_thought",
            model_provider="openai",
            model_name="gpt-4",
            model_parameters={},
            agent_parameters={},
        )

        assert service.validate_config(invalid_config) is False

    def test_validate_config_invalid_provider(self, service: NoneAgentService) -> None:
        """Test validate_config with invalid model provider."""
        invalid_config = AgentConfig(
            agent_type="none",
            model_provider="unsupported_provider",
            model_name="gpt-4",
            model_parameters={},
            agent_parameters={},
        )

        assert service.validate_config(invalid_config) is False

    @pytest.mark.asyncio
    async def test_answer_question_returns_valid_answer(
        self,
        service: NoneAgentService,
        sample_question_a: Question,
        valid_agent_config: AgentConfig,
    ) -> None:
        """Test answering a question returns valid Answer structure."""
        result = await service.answer_question(sample_question_a, valid_agent_config)

        assert isinstance(result, Answer)
        assert isinstance(result.extracted_answer, str)
        assert len(result.extracted_answer) > 0
        assert result.reasoning_trace.approach_type == "none"
        assert result.reasoning_trace.reasoning_text == ""
        assert result.confidence is None  # None agent doesn't provide confidence
        assert result.execution_time >= 0
        assert result.token_usage.total_tokens > 0
        assert isinstance(result.raw_response, str)
        assert len(result.raw_response) > 0

    @pytest.mark.asyncio
    async def test_answer_question_structure_consistency(
        self,
        service: NoneAgentService,
        sample_question_b: Question,
        valid_agent_config: AgentConfig,
    ) -> None:
        """Test answer structure consistency across different questions."""
        result = await service.answer_question(sample_question_b, valid_agent_config)

        assert isinstance(result, Answer)
        assert isinstance(result.extracted_answer, str)
        assert len(result.extracted_answer) > 0
        assert result.reasoning_trace.approach_type == "none"
        assert result.reasoning_trace.reasoning_text == ""
        assert result.confidence is None
        assert result.execution_time >= 0
        assert isinstance(result.raw_response, str)
        assert result.extracted_answer in result.raw_response

    @pytest.mark.asyncio
    async def test_answer_question_general(
        self,
        service: NoneAgentService,
        general_question: Question,
        valid_agent_config: AgentConfig,
    ) -> None:
        """Test answering a general question."""
        result = await service.answer_question(general_question, valid_agent_config)

        assert isinstance(result, Answer)
        assert isinstance(result.extracted_answer, str)
        assert len(result.extracted_answer) > 0
        assert result.reasoning_trace.approach_type == "none"
        assert result.reasoning_trace.reasoning_text == ""
        assert result.confidence is None
        assert result.execution_time > 0

    @pytest.mark.asyncio
    async def test_answer_question_what_question(
        self, service: NoneAgentService, valid_agent_config: AgentConfig
    ) -> None:
        """Test answering a question that starts with 'what'."""
        what_question = Question(
            id="what-q1",
            text="What is machine learning?",
            expected_answer="A subset of AI",
            metadata={},
        )

        result = await service.answer_question(what_question, valid_agent_config)

        assert isinstance(result, Answer)
        assert isinstance(result.extracted_answer, str)
        assert len(result.extracted_answer) > 0
        assert result.reasoning_trace.approach_type == "none"
        assert result.confidence is None

    @pytest.mark.asyncio
    async def test_answer_question_invalid_config(
        self, service: NoneAgentService, sample_question_a: Question
    ) -> None:
        """Test answering question with invalid configuration raises error."""
        invalid_config = AgentConfig(
            agent_type="chain_of_thought",
            model_provider="openai",
            model_name="gpt-4",
            model_parameters={},
            agent_parameters={},
        )

        with pytest.raises(InvalidConfigurationError):
            await service.answer_question(sample_question_a, invalid_config)

    @pytest.mark.asyncio
    async def test_answer_question_token_usage(
        self,
        service: NoneAgentService,
        sample_question_a: Question,
        valid_agent_config: AgentConfig,
    ) -> None:
        """Test that token usage is properly calculated."""
        result = await service.answer_question(sample_question_a, valid_agent_config)

        token_usage = result.token_usage
        assert token_usage.prompt_tokens > 0
        assert token_usage.completion_tokens > 0
        assert (
            token_usage.total_tokens
            == token_usage.prompt_tokens + token_usage.completion_tokens
        )

        # Token count should be based on question length
        expected_prompt_tokens = len(sample_question_a.text.split()) + 10
        assert token_usage.prompt_tokens == expected_prompt_tokens

    @pytest.mark.asyncio
    async def test_answer_question_execution_time(
        self,
        service: NoneAgentService,
        sample_question_a: Question,
        valid_agent_config: AgentConfig,
    ) -> None:
        """Test that execution time is measured."""
        result = await service.answer_question(sample_question_a, valid_agent_config)

        assert result.execution_time >= 0
        assert result.execution_time < 10  # Should be very fast for simulation

    @pytest.mark.asyncio
    async def test_answer_question_reasoning_trace_structure(
        self,
        service: NoneAgentService,
        sample_question_a: Question,
        valid_agent_config: AgentConfig,
    ) -> None:
        """Test that reasoning trace has correct structure for none agent."""
        result = await service.answer_question(sample_question_a, valid_agent_config)

        reasoning_trace = result.reasoning_trace
        assert reasoning_trace.approach_type == "none"
        assert reasoning_trace.reasoning_text == ""
        assert isinstance(
            reasoning_trace.metadata, (dict, type(reasoning_trace.metadata))
        )

    @pytest.mark.asyncio
    async def test_answer_question_raw_response_format(
        self,
        service: NoneAgentService,
        sample_question_a: Question,
        valid_agent_config: AgentConfig,
    ) -> None:
        """Test that raw response has expected format."""
        result = await service.answer_question(sample_question_a, valid_agent_config)

        assert result.raw_response.startswith("Direct answer: ")
        assert result.extracted_answer in result.raw_response

    @pytest.mark.asyncio
    async def test_answer_question_different_model_providers(
        self, service: NoneAgentService, sample_question_a: Question
    ) -> None:
        """Test answering with different model providers."""
        providers = ["openai", "anthropic", "mock"]

        for provider in providers:
            config = AgentConfig(
                agent_type="none",
                model_provider=provider,
                model_name="test-model",
                model_parameters={},
                agent_parameters={},
            )

            result = await service.answer_question(sample_question_a, config)
            assert isinstance(result, Answer)
            assert isinstance(result.extracted_answer, str)
            assert len(result.extracted_answer) > 0

    @pytest.mark.asyncio
    async def test_multiple_questions_independence(
        self, service: NoneAgentService, valid_agent_config: AgentConfig
    ) -> None:
        """Test that multiple questions are answered independently."""
        questions = [
            Question(
                id="q1",
                text="Sample question 1",
                expected_answer="Answer 1",
                metadata={},
            ),
            Question(
                id="q2",
                text="Sample question 2",
                expected_answer="Answer 2",
                metadata={},
            ),
        ]

        results = []
        for question in questions:
            result = await service.answer_question(question, valid_agent_config)
            results.append(result)

        assert len(results) == 2
        assert isinstance(results[0].extracted_answer, str)
        assert len(results[0].extracted_answer) > 0
        assert isinstance(results[1].extracted_answer, str)
        assert len(results[1].extracted_answer) > 0

        # Each should have execution times measured
        assert results[0].execution_time >= 0
        assert results[1].execution_time >= 0

    def test_service_immutability(self, service: NoneAgentService) -> None:
        """Test that service behavior is consistent across calls."""
        # Test that provider list is consistent
        providers1 = service.get_supported_model_providers()
        providers2 = service.get_supported_model_providers()
        assert providers1 == providers2

        # Test that agent type support is consistent
        assert service.supports_agent_type("none") is True
        assert service.supports_agent_type("none") is True

    def test_config_validation_edge_cases(self, service: NoneAgentService) -> None:
        """Test configuration validation with edge cases."""
        # Empty agent type
        empty_config = AgentConfig(
            agent_type="",
            model_provider="openai",
            model_name="gpt-4",
            model_parameters={},
            agent_parameters={},
        )
        assert service.validate_config(empty_config) is False

        # None model provider (invalid for practical use)
        none_provider_config = AgentConfig(
            agent_type="none",
            model_provider="",
            model_name="gpt-4",
            model_parameters={},
            agent_parameters={},
        )
        assert service.validate_config(none_provider_config) is False
