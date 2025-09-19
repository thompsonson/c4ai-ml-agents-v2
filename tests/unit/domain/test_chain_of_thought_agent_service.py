"""Tests for ChainOfThoughtAgentService implementation."""

import pytest

from ml_agents_v2.core.domain.services.reasoning.chain_of_thought_agent_service import (
    ChainOfThoughtAgentService,
)
from ml_agents_v2.core.domain.services.reasoning.exceptions import (
    InvalidConfigurationError,
)
from ml_agents_v2.core.domain.value_objects.agent_config import AgentConfig
from ml_agents_v2.core.domain.value_objects.answer import Answer
from ml_agents_v2.core.domain.value_objects.question import Question


class TestChainOfThoughtAgentService:
    """Test suite for ChainOfThoughtAgentService implementation."""

    @pytest.fixture
    def service(self) -> ChainOfThoughtAgentService:
        """Create a ChainOfThoughtAgentService instance for testing."""
        return ChainOfThoughtAgentService()

    @pytest.fixture
    def valid_agent_config(self) -> AgentConfig:
        """Create a valid agent configuration for chain of thought agent."""
        return AgentConfig(
            agent_type="chain_of_thought",
            model_provider="openai",
            model_name="gpt-4",
            model_parameters={"temperature": 0.7, "max_tokens": 1000},
            agent_parameters={"timeout_seconds": 30},
        )

    @pytest.fixture
    def sample_question(self) -> Question:
        """Create a sample question for testing."""
        return Question(
            id="test-q1",
            text="Sample question for testing",
            expected_answer="Sample answer",
            metadata={"topic": "test"},
        )

    def test_service_initialization(self, service: ChainOfThoughtAgentService) -> None:
        """Test service initializes with correct configuration."""
        assert service.supports_agent_type("chain_of_thought") is True
        assert service.supports_agent_type("none") is False

        providers = service.get_supported_model_providers()
        assert "openai" in providers
        assert "anthropic" in providers
        assert "mock" in providers

    def test_supports_agent_type(self, service: ChainOfThoughtAgentService) -> None:
        """Test supports_agent_type method."""
        assert service.supports_agent_type("chain_of_thought") is True
        assert service.supports_agent_type("none") is False
        assert service.supports_agent_type("unknown") is False
        assert service.supports_agent_type("") is False

    def test_get_supported_model_providers(
        self, service: ChainOfThoughtAgentService
    ) -> None:
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
        self,
        service: ChainOfThoughtAgentService,
        valid_agent_config: AgentConfig,
    ) -> None:
        """Test validate_config with valid configuration."""
        assert service.validate_config(valid_agent_config) is True

    def test_validate_config_invalid_agent_type(
        self, service: ChainOfThoughtAgentService
    ) -> None:
        """Test validate_config with invalid agent type."""
        invalid_config = AgentConfig(
            agent_type="none",
            model_provider="openai",
            model_name="gpt-4",
            model_parameters={},
            agent_parameters={},
        )

        assert service.validate_config(invalid_config) is False

    def test_validate_config_invalid_provider(
        self, service: ChainOfThoughtAgentService
    ) -> None:
        """Test validate_config with invalid model provider."""
        invalid_config = AgentConfig(
            agent_type="chain_of_thought",
            model_provider="unsupported_provider",
            model_name="gpt-4",
            model_parameters={},
            agent_parameters={},
        )

        assert service.validate_config(invalid_config) is False

    @pytest.mark.asyncio
    async def test_answer_question_returns_valid_answer(
        self,
        service: ChainOfThoughtAgentService,
        sample_question: Question,
        valid_agent_config: AgentConfig,
    ) -> None:
        """Test that answering a question returns a valid Answer object."""
        result = await service.answer_question(sample_question, valid_agent_config)

        assert isinstance(result, Answer)
        assert isinstance(result.extracted_answer, str)
        assert len(result.extracted_answer) > 0
        assert result.reasoning_trace.approach_type == "chain_of_thought"
        assert isinstance(result.reasoning_trace.reasoning_text, str)
        assert len(result.reasoning_trace.reasoning_text) > 0
        assert result.confidence is not None
        assert isinstance(result.confidence, float)
        assert 0.0 <= result.confidence <= 1.0
        assert result.execution_time > 0
        assert result.token_usage.total_tokens > 0

    @pytest.mark.asyncio
    async def test_answer_question_invalid_config(
        self, service: ChainOfThoughtAgentService, sample_question: Question
    ) -> None:
        """Test answering question with invalid configuration raises error."""
        invalid_config = AgentConfig(
            agent_type="none",
            model_provider="openai",
            model_name="gpt-4",
            model_parameters={},
            agent_parameters={},
        )

        with pytest.raises(InvalidConfigurationError):
            await service.answer_question(sample_question, invalid_config)

    @pytest.mark.asyncio
    async def test_answer_question_token_usage(
        self,
        service: ChainOfThoughtAgentService,
        sample_question: Question,
        valid_agent_config: AgentConfig,
    ) -> None:
        """Test that token usage is properly calculated."""
        result = await service.answer_question(sample_question, valid_agent_config)

        token_usage = result.token_usage
        assert token_usage.prompt_tokens > 0
        assert token_usage.completion_tokens > 0
        assert (
            token_usage.total_tokens
            == token_usage.prompt_tokens + token_usage.completion_tokens
        )

    @pytest.mark.asyncio
    async def test_answer_question_execution_time(
        self,
        service: ChainOfThoughtAgentService,
        sample_question: Question,
        valid_agent_config: AgentConfig,
    ) -> None:
        """Test that execution time is measured."""
        result = await service.answer_question(sample_question, valid_agent_config)

        assert result.execution_time > 0
        assert result.execution_time < 30  # Should be reasonable for simulation

    @pytest.mark.asyncio
    async def test_answer_question_reasoning_trace_structure(
        self,
        service: ChainOfThoughtAgentService,
        sample_question: Question,
        valid_agent_config: AgentConfig,
    ) -> None:
        """Test that reasoning trace has correct structure for chain of thought."""
        result = await service.answer_question(sample_question, valid_agent_config)

        reasoning_trace = result.reasoning_trace
        assert reasoning_trace.approach_type == "chain_of_thought"
        assert len(reasoning_trace.reasoning_text) > 0
        assert isinstance(
            reasoning_trace.metadata, (dict, type(reasoning_trace.metadata))
        )
        assert "steps" in reasoning_trace.metadata
        assert isinstance(reasoning_trace.metadata["steps"], int)
        assert reasoning_trace.metadata["steps"] >= 1

    @pytest.mark.asyncio
    async def test_answer_question_confidence_provided(
        self,
        service: ChainOfThoughtAgentService,
        sample_question: Question,
        valid_agent_config: AgentConfig,
    ) -> None:
        """Test that confidence is provided for chain of thought answers."""
        result = await service.answer_question(sample_question, valid_agent_config)

        assert result.confidence is not None
        assert isinstance(result.confidence, float)
        assert 0.0 <= result.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_answer_question_different_model_providers(
        self, service: ChainOfThoughtAgentService, sample_question: Question
    ) -> None:
        """Test answering with different model providers."""
        providers = ["openai", "anthropic", "mock"]

        for provider in providers:
            config = AgentConfig(
                agent_type="chain_of_thought",
                model_provider=provider,
                model_name="test-model",
                model_parameters={},
                agent_parameters={},
            )

            result = await service.answer_question(sample_question, config)
            assert isinstance(result, Answer)
            assert result.reasoning_trace.approach_type == "chain_of_thought"

    @pytest.mark.asyncio
    async def test_multiple_questions_independence(
        self, service: ChainOfThoughtAgentService, valid_agent_config: AgentConfig
    ) -> None:
        """Test that multiple questions are answered independently."""
        questions = [
            Question(
                id="q1",
                text="First question",
                expected_answer="Answer 1",
                metadata={},
            ),
            Question(
                id="q2",
                text="Second question",
                expected_answer="Answer 2",
                metadata={},
            ),
        ]

        results = []
        for question in questions:
            result = await service.answer_question(question, valid_agent_config)
            results.append(result)

        assert len(results) == 2
        assert results[0].reasoning_trace.approach_type == "chain_of_thought"
        assert results[1].reasoning_trace.approach_type == "chain_of_thought"

        # Each should have execution times measured
        assert results[0].execution_time >= 0
        assert results[1].execution_time >= 0

    def test_service_immutability(self, service: ChainOfThoughtAgentService) -> None:
        """Test that service behavior is consistent across calls."""
        # Test that provider list is consistent
        providers1 = service.get_supported_model_providers()
        providers2 = service.get_supported_model_providers()
        assert providers1 == providers2

        # Test that agent type support is consistent
        assert service.supports_agent_type("chain_of_thought") is True
        assert service.supports_agent_type("chain_of_thought") is True

    def test_config_validation_edge_cases(
        self, service: ChainOfThoughtAgentService
    ) -> None:
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

        # Empty model provider
        empty_provider_config = AgentConfig(
            agent_type="chain_of_thought",
            model_provider="",
            model_name="gpt-4",
            model_parameters={},
            agent_parameters={},
        )
        assert service.validate_config(empty_provider_config) is False
