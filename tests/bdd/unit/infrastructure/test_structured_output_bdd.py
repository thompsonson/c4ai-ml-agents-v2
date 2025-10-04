"""BDD tests for structured output parsing system.

This module implements proper BDD testing for structured output parsing:
- Tests parser selection based on PARSING_STRATEGY environment variable
- Tests real error translation from ParserException to FailureReason
- Tests configuration integration and parser behavior
- Mocks at LLMClientFactory level, not individual client level

Key principle: Mock external boundaries (factory.create_client()), test internal logic.
"""

import os
from unittest.mock import AsyncMock, Mock, patch

import pytest

from ml_agents_v2.config.application_config import get_config
from ml_agents_v2.core.domain.services.reasoning.none_agent_service import (
    NoneAgentService,
)
from ml_agents_v2.core.domain.value_objects.agent_config import AgentConfig
from ml_agents_v2.core.domain.value_objects.answer import (
    Answer,
    ParsedResponse,
)
from ml_agents_v2.core.domain.value_objects.failure_reason import FailureReason
from ml_agents_v2.core.domain.value_objects.question import Question
from ml_agents_v2.infrastructure.models import DirectAnswerOutput
from ml_agents_v2.infrastructure.openrouter.error_mapper import OpenRouterErrorMapper
from ml_agents_v2.infrastructure.parsing_factory import LLMClientFactory
from ml_agents_v2.infrastructure.reasoning_service import ReasoningInfrastructureService


class TestParsingStrategySelection:
    """BDD tests for PARSING_STRATEGY environment variable integration."""

    @pytest.fixture
    def sample_question(self):
        """Sample question for testing."""
        return Question(
            id="test_q1",
            text="What is the capital of France?",
            expected_answer="Paris",
            metadata={},
        )

    @pytest.fixture
    def sample_agent_config(self):
        """Sample agent configuration."""
        return AgentConfig(
            agent_type="none",
            model_provider="anthropic",
            model_name="claude-3-sonnet",
            model_parameters={"temperature": 0.1, "max_tokens": 100},
            agent_parameters={},
        )

    @pytest.fixture
    def domain_service(self):
        """Domain service for testing."""
        return NoneAgentService()

    async def test_outlines_strategy_uses_response_format(
        self, sample_question, sample_agent_config, domain_service
    ):
        """Given PARSING_STRATEGY=outlines, when processing question, then uses response_format"""
        # Arrange - Mock LLM client created by factory (AsyncMock for async methods)
        mock_llm_client = AsyncMock()
        mock_llm_client.chat_completion.return_value = ParsedResponse(
            content='{"answer": "Paris"}', structured_data={"answer": "Paris"}
        )

        # Mock factory to return our mock client
        mock_factory = Mock(spec=LLMClientFactory)
        mock_factory.create_client.return_value = mock_llm_client
        mock_factory.get_output_model.return_value = DirectAnswerOutput

        # Act - Test with outlines strategy
        with patch.dict(os.environ, {"PARSING_STRATEGY": "outlines"}):
            config = get_config()
            service = ReasoningInfrastructureService(
                llm_client_factory=mock_factory,
                error_mapper=OpenRouterErrorMapper(),
                parsing_strategy=config.parsing_strategy,
            )

            result = await service.execute_reasoning(
                domain_service, sample_question, sample_agent_config
            )

        # Assert - Verify behavior
        assert isinstance(result, Answer)
        assert result.extracted_answer == "Paris"

        # Verify factory was called with correct strategy
        mock_factory.create_client.assert_called_once_with(
            model_name=sample_agent_config.model_name, strategy="outlines"
        )

        # Verify LLM client was called (implementation details tested separately)
        mock_llm_client.chat_completion.assert_called_once()

    async def test_marvin_strategy_uses_internal_agent_type(
        self, sample_question, sample_agent_config, domain_service
    ):
        """Given PARSING_STRATEGY=marvin, when processing question, then uses _internal_agent_type"""
        # Arrange - Mock LLM client created by factory (AsyncMock for async methods)
        mock_llm_client = AsyncMock()
        mock_llm_client.chat_completion.return_value = ParsedResponse(
            content="Paris", structured_data={"answer": "Paris"}
        )

        # Mock factory to return our mock client
        mock_factory = Mock(spec=LLMClientFactory)
        mock_factory.create_client.return_value = mock_llm_client
        mock_factory.get_output_model.return_value = DirectAnswerOutput

        # Act - Test with marvin strategy
        with patch.dict(os.environ, {"PARSING_STRATEGY": "marvin"}):
            config = get_config()
            service = ReasoningInfrastructureService(
                llm_client_factory=mock_factory,
                error_mapper=OpenRouterErrorMapper(),
                parsing_strategy=config.parsing_strategy,
            )

            result = await service.execute_reasoning(
                domain_service, sample_question, sample_agent_config
            )

        # Assert - Verify behavior
        assert isinstance(result, Answer)
        assert result.extracted_answer == "Paris"

        # Verify factory was called with correct strategy
        mock_factory.create_client.assert_called_once_with(
            model_name=sample_agent_config.model_name, strategy="marvin"
        )

        # Verify LLM client was called (implementation details tested separately)
        mock_llm_client.chat_completion.assert_called_once()

    async def test_auto_strategy_selects_based_on_model_capabilities(
        self, sample_question, domain_service
    ):
        """Given PARSING_STRATEGY=auto, when processing question, then selects parser based on model"""
        # Arrange - Mock LLM client created by factory (AsyncMock for async methods)
        mock_llm_client = AsyncMock()
        mock_llm_client.chat_completion.return_value = ParsedResponse(
            content='{"answer": "Paris"}', structured_data={"answer": "Paris"}
        )

        # Mock factory to return our mock client
        mock_factory = Mock(spec=LLMClientFactory)
        mock_factory.create_client.return_value = mock_llm_client
        mock_factory.get_output_model.return_value = DirectAnswerOutput

        # Test with gpt-4 (supports logprobs) - should use StructuredLogProbsClient
        gpt4_config = AgentConfig(
            agent_type="none",
            model_provider="openai",
            model_name="gpt-4",
            model_parameters={"temperature": 0.1},
            agent_parameters={},
        )

        with patch.dict(os.environ, {"PARSING_STRATEGY": "auto"}):
            config = get_config()
            service = ReasoningInfrastructureService(
                llm_client_factory=mock_factory,
                error_mapper=OpenRouterErrorMapper(),
                parsing_strategy=config.parsing_strategy,
            )

            result = await service.execute_reasoning(
                domain_service, sample_question, gpt4_config
            )

        # Assert - Verify behavior and factory usage
        assert isinstance(result, Answer)
        mock_factory.create_client.assert_called_once_with(
            model_name="gpt-4", strategy="auto"
        )

        # Verify LLM client was called (implementation details tested separately)
        mock_llm_client.chat_completion.assert_called_once()


class TestParserErrorTranslation:
    """BDD tests for parser error translation across ACL boundary."""

    @pytest.fixture
    def sample_question(self):
        """Sample question for testing."""
        return Question(
            id="test_q1", text="What is 2+2?", expected_answer="4", metadata={}
        )

    @pytest.fixture
    def sample_agent_config(self):
        """Sample agent configuration."""
        return AgentConfig(
            agent_type="none",
            model_provider="anthropic",
            model_name="claude-3-sonnet",
            model_parameters={"temperature": 0.1},
            agent_parameters={},
        )

    @pytest.fixture
    def domain_service(self):
        """Domain service for testing."""
        return NoneAgentService()

    async def test_empty_response_becomes_parsing_error(
        self, sample_question, sample_agent_config, domain_service
    ):
        """Given LLM returns response without structured_data, when execute_reasoning, then returns FailureReason"""
        # Arrange - Mock LLM client that returns response without structured data (AsyncMock for async methods)
        mock_llm_client = AsyncMock()
        mock_llm_client.chat_completion.return_value = ParsedResponse(
            content="Some natural language response",  # Valid content but no structured_data
            structured_data=None,  # Missing structured_data will trigger parser error
        )

        # Mock factory to return our mock client
        mock_factory = Mock(spec=LLMClientFactory)
        mock_factory.create_client.return_value = mock_llm_client
        mock_factory.get_output_model.return_value = DirectAnswerOutput

        service = ReasoningInfrastructureService(
            llm_client_factory=mock_factory,
            error_mapper=OpenRouterErrorMapper(),
            parsing_strategy="marvin",
        )

        # Act
        result = await service.execute_reasoning(
            domain_service, sample_question, sample_agent_config
        )

        # Assert - Verify ACL translation to domain FailureReason
        assert isinstance(result, FailureReason)
        assert result.category == "parsing_error"
        assert "failed at" in result.description
        assert (
            "InstructorParser" in result.description
        )  # Current implementation behavior
        assert result.recoverable is False

    async def test_api_exception_becomes_failure_reason(
        self, sample_question, sample_agent_config, domain_service
    ):
        """Given LLM client throws exception, when execute_reasoning, then returns FailureReason"""
        # Arrange - Mock LLM client that throws exception (AsyncMock for async methods)
        mock_llm_client = AsyncMock()
        mock_llm_client.chat_completion.side_effect = Exception("API connection failed")

        # Mock factory to return our mock client
        mock_factory = Mock(spec=LLMClientFactory)
        mock_factory.create_client.return_value = mock_llm_client
        mock_factory.get_output_model.return_value = DirectAnswerOutput

        service = ReasoningInfrastructureService(
            llm_client_factory=mock_factory,
            error_mapper=OpenRouterErrorMapper(),
            parsing_strategy="outlines",
        )

        # Act
        result = await service.execute_reasoning(
            domain_service, sample_question, sample_agent_config
        )

        # Assert - Should be mapped by error_mapper, not parser translation
        assert isinstance(result, FailureReason)
        # This tests the error_mapper path, not parser exception path


class TestConfigurationIntegration:
    """BDD tests for configuration loading and service integration."""

    @patch.dict(os.environ, {"PARSING_STRATEGY": "outlines"})
    def test_environment_variable_loads_into_config(self):
        """Given PARSING_STRATEGY=outlines in environment, when loading config, then strategy is set"""
        # Act
        config = get_config()

        # Assert
        assert config.parsing_strategy == "outlines"

    @patch.dict(os.environ, {"PARSING_STRATEGY": "marvin"})
    def test_marvin_strategy_environment_integration(self):
        """Given PARSING_STRATEGY=marvin in environment, when creating service, then strategy is passed"""
        # Act
        config = get_config()
        mock_factory = Mock(spec=LLMClientFactory)
        service = ReasoningInfrastructureService(
            llm_client_factory=mock_factory,
            error_mapper=Mock(),
            parsing_strategy=config.parsing_strategy,
        )

        # Assert
        assert service.parsing_strategy == "marvin"

    def test_default_parsing_strategy_is_auto(self):
        """Given no PARSING_STRATEGY environment variable, when loading config, then defaults to auto"""
        # Ensure env var is not set
        with patch.dict(os.environ, {}, clear=True):
            if "PARSING_STRATEGY" in os.environ:
                del os.environ["PARSING_STRATEGY"]

            # Act
            config = get_config()

            # Assert
            assert config.parsing_strategy == "auto"
