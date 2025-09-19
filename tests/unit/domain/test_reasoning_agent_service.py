"""Tests for ReasoningAgentService abstract interface."""

import pytest

from ml_agents_v2.core.domain.services.reasoning.reasoning_agent_service import (
    ReasoningAgentService,
)
from ml_agents_v2.core.domain.value_objects.agent_config import AgentConfig
from ml_agents_v2.core.domain.value_objects.answer import Answer, TokenUsage
from ml_agents_v2.core.domain.value_objects.question import Question
from ml_agents_v2.core.domain.value_objects.reasoning_trace import ReasoningTrace


class MockReasoningAgentService(ReasoningAgentService):
    """Mock implementation of ReasoningAgentService for testing."""

    def __init__(
        self,
        supported_agent_type: str = "none",
        supported_providers: list[str] | None = None,
        config_validation_result: bool = True,
    ) -> None:
        """Initialize mock service with configurable behavior."""
        self.supported_agent_type = supported_agent_type
        self.supported_providers = supported_providers or ["mock"]
        self.config_validation_result = config_validation_result

    async def answer_question(
        self, question: Question, agent_config: AgentConfig
    ) -> Answer:
        """Mock answer_question implementation."""
        # Use empty reasoning text for "none" type, actual text for others
        reasoning_text = "" if self.supported_agent_type == "none" else "Mock reasoning"

        reasoning_trace = ReasoningTrace(
            approach_type=self.supported_agent_type,
            reasoning_text=reasoning_text,
            metadata={"mock": True},
        )

        token_usage = TokenUsage(
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
        )

        return Answer(
            extracted_answer="Mock answer",
            reasoning_trace=reasoning_trace,
            confidence=0.8,
            execution_time=1.0,
            token_usage=token_usage,
            raw_response="Mock raw response",
        )

    def supports_agent_type(self, agent_type: str) -> bool:
        """Mock supports_agent_type implementation."""
        return agent_type == self.supported_agent_type

    def get_supported_model_providers(self) -> list[str]:
        """Mock get_supported_model_providers implementation."""
        return self.supported_providers.copy()

    def validate_config(self, agent_config: AgentConfig) -> bool:
        """Mock validate_config implementation."""
        return self.config_validation_result


class TestReasoningAgentService:
    """Test suite for ReasoningAgentService abstract interface."""

    @pytest.fixture
    def mock_service(self) -> MockReasoningAgentService:
        """Create a mock reasoning agent service for testing."""
        return MockReasoningAgentService()

    @pytest.fixture
    def sample_question(self) -> Question:
        """Create a sample question for testing."""
        return Question(
            id="test-q1",
            text="What is 2+2?",
            expected_answer="4",
            metadata={"difficulty": "easy"},
        )

    @pytest.fixture
    def sample_agent_config(self) -> AgentConfig:
        """Create a sample agent configuration for testing."""
        return AgentConfig(
            agent_type="none",
            model_provider="mock",
            model_name="test-model",
            model_parameters={"temperature": 0.7},
            agent_parameters={"timeout": 30},
        )

    @pytest.mark.asyncio
    async def test_answer_question_interface(
        self,
        mock_service: MockReasoningAgentService,
        sample_question: Question,
        sample_agent_config: AgentConfig,
    ) -> None:
        """Test answer_question interface method."""
        result = await mock_service.answer_question(
            sample_question, sample_agent_config
        )

        assert isinstance(result, Answer)
        assert result.extracted_answer == "Mock answer"
        assert result.reasoning_trace.approach_type == "none"
        assert result.confidence == 0.8
        assert result.execution_time == 1.0
        assert isinstance(result.token_usage, TokenUsage)

    def test_supports_agent_type_interface(
        self, mock_service: MockReasoningAgentService
    ) -> None:
        """Test supports_agent_type interface method."""
        assert mock_service.supports_agent_type("none") is True
        assert mock_service.supports_agent_type("unknown") is False

    def test_get_supported_model_providers_interface(
        self, mock_service: MockReasoningAgentService
    ) -> None:
        """Test get_supported_model_providers interface method."""
        providers = mock_service.get_supported_model_providers()

        assert isinstance(providers, list)
        assert "mock" in providers
        assert len(providers) == 1

    def test_validate_config_interface(
        self,
        mock_service: MockReasoningAgentService,
        sample_agent_config: AgentConfig,
    ) -> None:
        """Test validate_config interface method."""
        result = mock_service.validate_config(sample_agent_config)

        assert isinstance(result, bool)
        assert result is True

    def test_abstract_interface_compliance(self) -> None:
        """Test that ReasoningAgentService is properly abstract."""
        # Should not be able to instantiate abstract class directly
        with pytest.raises(TypeError):
            ReasoningAgentService()  # type: ignore

    def test_interface_method_signatures(self) -> None:
        """Test that the interface has all required method signatures."""
        # Verify all required methods exist
        required_methods = [
            "answer_question",
            "supports_agent_type",
            "get_supported_model_providers",
            "validate_config",
        ]

        for method_name in required_methods:
            assert hasattr(ReasoningAgentService, method_name)
            method = getattr(ReasoningAgentService, method_name)
            assert callable(method)

    def test_mock_service_configuration_flexibility(self) -> None:
        """Test mock service can be configured for different scenarios."""
        # Test different agent types
        none_service = MockReasoningAgentService(supported_agent_type="none")
        cot_service = MockReasoningAgentService(supported_agent_type="chain_of_thought")

        assert none_service.supports_agent_type("none") is True
        assert none_service.supports_agent_type("chain_of_thought") is False
        assert cot_service.supports_agent_type("chain_of_thought") is True
        assert cot_service.supports_agent_type("none") is False

        # Test different providers
        openai_service = MockReasoningAgentService(
            supported_providers=["openai", "mock"]
        )
        anthropic_service = MockReasoningAgentService(supported_providers=["anthropic"])

        assert "openai" in openai_service.get_supported_model_providers()
        assert "mock" in openai_service.get_supported_model_providers()
        assert "anthropic" not in openai_service.get_supported_model_providers()
        assert "anthropic" in anthropic_service.get_supported_model_providers()
        assert "openai" not in anthropic_service.get_supported_model_providers()

        # Test config validation behavior
        valid_service = MockReasoningAgentService(config_validation_result=True)
        invalid_service = MockReasoningAgentService(config_validation_result=False)

        sample_config = AgentConfig(
            agent_type="none",
            model_provider="test",
            model_name="test",
            model_parameters={},
            agent_parameters={},
        )

        assert valid_service.validate_config(sample_config) is True
        assert invalid_service.validate_config(sample_config) is False

    @pytest.mark.asyncio
    async def test_answer_question_return_type_validation(
        self,
        mock_service: MockReasoningAgentService,
        sample_question: Question,
        sample_agent_config: AgentConfig,
    ) -> None:
        """Test that answer_question returns properly structured Answer."""
        result = await mock_service.answer_question(
            sample_question, sample_agent_config
        )

        # Verify all Answer fields are present and correctly typed
        assert hasattr(result, "extracted_answer")
        assert isinstance(result.extracted_answer, str)
        assert len(result.extracted_answer) > 0

        assert hasattr(result, "reasoning_trace")
        assert isinstance(result.reasoning_trace, ReasoningTrace)

        assert hasattr(result, "confidence")
        assert result.confidence is None or isinstance(result.confidence, float)

        assert hasattr(result, "execution_time")
        assert isinstance(result.execution_time, (int, float))
        assert result.execution_time >= 0

        assert hasattr(result, "token_usage")
        assert isinstance(result.token_usage, TokenUsage)

        assert hasattr(result, "raw_response")
        assert isinstance(result.raw_response, str)

    def test_provider_list_immutability(
        self, mock_service: MockReasoningAgentService
    ) -> None:
        """Test that get_supported_model_providers returns a copy."""
        providers1 = mock_service.get_supported_model_providers()
        providers2 = mock_service.get_supported_model_providers()

        # Should return copies, not the same list
        assert providers1 == providers2
        assert providers1 is not providers2

        # Modifying returned list shouldn't affect service
        providers1.append("new_provider")
        providers3 = mock_service.get_supported_model_providers()
        assert "new_provider" not in providers3

    def test_multiple_mock_service_instances(self) -> None:
        """Test that multiple mock service instances work independently."""
        service1 = MockReasoningAgentService(
            supported_agent_type="none",
            supported_providers=["openai"],
            config_validation_result=True,
        )

        service2 = MockReasoningAgentService(
            supported_agent_type="chain_of_thought",
            supported_providers=["anthropic"],
            config_validation_result=False,
        )

        # Verify independence
        assert service1.supports_agent_type("none") is True
        assert service1.supports_agent_type("chain_of_thought") is False
        assert service2.supports_agent_type("none") is False
        assert service2.supports_agent_type("chain_of_thought") is True

        assert service1.get_supported_model_providers() == ["openai"]
        assert service2.get_supported_model_providers() == ["anthropic"]

        config = AgentConfig(
            agent_type="none",
            model_provider="test",
            model_name="test",
            model_parameters={},
            agent_parameters={},
        )

        assert service1.validate_config(config) is True
        assert service2.validate_config(config) is False
