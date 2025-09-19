"""Tests for ReasoningAgentFactory."""

import pytest

from ml_agents_v2.core.domain.services.reasoning.exceptions import (
    InvalidConfigurationError,
)
from ml_agents_v2.core.domain.services.reasoning.reasoning_agent_factory import (
    ReasoningAgentFactory,
)
from ml_agents_v2.core.domain.services.reasoning.reasoning_agent_service import (
    ReasoningAgentService,
)
from ml_agents_v2.core.domain.value_objects.agent_config import AgentConfig
from ml_agents_v2.core.domain.value_objects.answer import Answer, TokenUsage
from ml_agents_v2.core.domain.value_objects.question import Question
from ml_agents_v2.core.domain.value_objects.reasoning_trace import ReasoningTrace


class MockAgentService(ReasoningAgentService):
    """Mock agent service for testing factory."""

    def __init__(
        self,
        agent_type: str,
        supported_providers: list[str] | None = None,
        validation_result: bool = True,
    ) -> None:
        """Initialize mock agent service."""
        self.agent_type = agent_type
        self.supported_providers = supported_providers or ["mock"]
        self.validation_result = validation_result

    async def answer_question(
        self, question: Question, agent_config: AgentConfig
    ) -> Answer:
        """Mock answer implementation."""
        reasoning_trace = ReasoningTrace(
            approach_type=self.agent_type,
            reasoning_text=f"Mock reasoning for {self.agent_type}",
            metadata={"mock": True},
        )

        token_usage = TokenUsage(
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
        )

        return Answer(
            extracted_answer=f"Mock answer from {self.agent_type}",
            reasoning_trace=reasoning_trace,
            confidence=0.8,
            execution_time=1.0,
            token_usage=token_usage,
            raw_response=f"Mock raw response from {self.agent_type}",
        )

    def supports_agent_type(self, agent_type: str) -> bool:
        """Check if agent type is supported."""
        return agent_type == self.agent_type

    def get_supported_model_providers(self) -> list[str]:
        """Get supported model providers."""
        return self.supported_providers.copy()

    def validate_config(self, agent_config: AgentConfig) -> bool:
        """Validate agent configuration."""
        return self.validation_result


class TestReasoningAgentFactory:
    """Test suite for ReasoningAgentFactory."""

    @pytest.fixture
    def factory(self) -> ReasoningAgentFactory:
        """Create a fresh factory for testing."""
        return ReasoningAgentFactory()

    @pytest.fixture
    def mock_none_service_class(self) -> type[MockAgentService]:
        """Create mock none agent service class."""

        class MockNoneService(MockAgentService):
            def __init__(self) -> None:
                super().__init__("none", ["openai", "anthropic", "mock"])

        return MockNoneService

    @pytest.fixture
    def mock_cot_service_class(self) -> type[MockAgentService]:
        """Create mock chain of thought agent service class."""

        class MockCoTService(MockAgentService):
            def __init__(self) -> None:
                super().__init__("chain_of_thought", ["openai", "anthropic"])

        return MockCoTService

    @pytest.fixture
    def sample_agent_config(self) -> AgentConfig:
        """Create sample agent configuration."""
        return AgentConfig(
            agent_type="none",
            model_provider="openai",
            model_name="gpt-4",
            model_parameters={"temperature": 0.7},
            agent_parameters={},
        )

    def test_factory_initialization(self, factory: ReasoningAgentFactory) -> None:
        """Test factory initializes with empty registry."""
        assert factory.get_supported_agent_types() == []
        assert factory.is_agent_type_supported("none") is False
        assert factory.is_agent_type_supported("chain_of_thought") is False

    def test_register_service(
        self,
        factory: ReasoningAgentFactory,
        mock_none_service_class: type[MockAgentService],
    ) -> None:
        """Test registering a service with the factory."""
        factory.register_service("none", mock_none_service_class)

        assert factory.is_agent_type_supported("none") is True
        assert "none" in factory.get_supported_agent_types()

    def test_register_service_duplicate_agent_type(
        self,
        factory: ReasoningAgentFactory,
        mock_none_service_class: type[MockAgentService],
    ) -> None:
        """Test registering duplicate agent type raises error."""
        factory.register_service("none", mock_none_service_class)

        with pytest.raises(ValueError, match="already registered"):
            factory.register_service("none", mock_none_service_class)

    def test_register_multiple_services(
        self,
        factory: ReasoningAgentFactory,
        mock_none_service_class: type[MockAgentService],
        mock_cot_service_class: type[MockAgentService],
    ) -> None:
        """Test registering multiple different services."""
        factory.register_service("none", mock_none_service_class)
        factory.register_service("chain_of_thought", mock_cot_service_class)

        supported_types = factory.get_supported_agent_types()
        assert len(supported_types) == 2
        assert "none" in supported_types
        assert "chain_of_thought" in supported_types

    def test_create_service_valid_config(
        self,
        factory: ReasoningAgentFactory,
        mock_none_service_class: type[MockAgentService],
        sample_agent_config: AgentConfig,
    ) -> None:
        """Test creating service with valid configuration."""
        factory.register_service("none", mock_none_service_class)

        service = factory.create_service(sample_agent_config)

        assert isinstance(service, ReasoningAgentService)
        assert service.supports_agent_type("none") is True

    def test_create_service_unsupported_agent_type(
        self,
        factory: ReasoningAgentFactory,
        sample_agent_config: AgentConfig,
    ) -> None:
        """Test creating service with unsupported agent type raises error."""
        with pytest.raises(InvalidConfigurationError) as exc_info:
            factory.create_service(sample_agent_config)

        assert "Unsupported agent type 'none'" in str(exc_info.value)
        assert "Available types: []" in str(exc_info.value)

    def test_create_service_unsupported_agent_type_with_available_types(
        self,
        factory: ReasoningAgentFactory,
        mock_cot_service_class: type[MockAgentService],
    ) -> None:
        """Test error message shows available types when agent type is unsupported."""
        factory.register_service("chain_of_thought", mock_cot_service_class)

        config = AgentConfig(
            agent_type="unsupported",
            model_provider="openai",
            model_name="gpt-4",
            model_parameters={},
            agent_parameters={},
        )

        with pytest.raises(InvalidConfigurationError) as exc_info:
            factory.create_service(config)

        assert "Unsupported agent type 'unsupported'" in str(exc_info.value)
        assert "Available types: ['chain_of_thought']" in str(exc_info.value)

    def test_create_service_invalid_config_validation(
        self, factory: ReasoningAgentFactory
    ) -> None:
        """Test creating service with invalid configuration that fails validation."""

        class InvalidConfigService(MockAgentService):
            def __init__(self) -> None:
                super().__init__("invalid_test", validation_result=False)

        factory.register_service("invalid_test", InvalidConfigService)

        config = AgentConfig(
            agent_type="invalid_test",
            model_provider="test",
            model_name="test",
            model_parameters={},
            agent_parameters={},
        )

        with pytest.raises(InvalidConfigurationError) as exc_info:
            factory.create_service(config)

        assert "Configuration validation failed" in str(exc_info.value)
        assert "invalid_test" in str(exc_info.value)

    def test_get_supported_agent_types_immutability(
        self,
        factory: ReasoningAgentFactory,
        mock_none_service_class: type[MockAgentService],
    ) -> None:
        """Test that get_supported_agent_types returns a copy."""
        factory.register_service("none", mock_none_service_class)

        types1 = factory.get_supported_agent_types()
        types2 = factory.get_supported_agent_types()

        # Should return copies, not the same list
        assert types1 == types2
        assert types1 is not types2

        # Modifying returned list shouldn't affect factory
        types1.append("fake_type")
        types3 = factory.get_supported_agent_types()
        assert "fake_type" not in types3

    def test_is_agent_type_supported(
        self,
        factory: ReasoningAgentFactory,
        mock_none_service_class: type[MockAgentService],
        mock_cot_service_class: type[MockAgentService],
    ) -> None:
        """Test checking if agent types are supported."""
        # Initially nothing supported
        assert factory.is_agent_type_supported("none") is False
        assert factory.is_agent_type_supported("chain_of_thought") is False
        assert factory.is_agent_type_supported("unknown") is False

        # Register one service
        factory.register_service("none", mock_none_service_class)
        assert factory.is_agent_type_supported("none") is True
        assert factory.is_agent_type_supported("chain_of_thought") is False

        # Register second service
        factory.register_service("chain_of_thought", mock_cot_service_class)
        assert factory.is_agent_type_supported("none") is True
        assert factory.is_agent_type_supported("chain_of_thought") is True
        assert factory.is_agent_type_supported("unknown") is False

    def test_unregister_service(
        self,
        factory: ReasoningAgentFactory,
        mock_none_service_class: type[MockAgentService],
        mock_cot_service_class: type[MockAgentService],
    ) -> None:
        """Test unregistering services."""
        # Register services
        factory.register_service("none", mock_none_service_class)
        factory.register_service("chain_of_thought", mock_cot_service_class)

        assert len(factory.get_supported_agent_types()) == 2

        # Unregister one service
        result = factory.unregister_service("none")
        assert result is True
        assert factory.is_agent_type_supported("none") is False
        assert factory.is_agent_type_supported("chain_of_thought") is True
        assert len(factory.get_supported_agent_types()) == 1

        # Unregister non-existent service
        result = factory.unregister_service("none")
        assert result is False

        # Unregister remaining service
        result = factory.unregister_service("chain_of_thought")
        assert result is True
        assert len(factory.get_supported_agent_types()) == 0

    def test_factory_workflow_integration(
        self,
        factory: ReasoningAgentFactory,
        mock_none_service_class: type[MockAgentService],
        mock_cot_service_class: type[MockAgentService],
    ) -> None:
        """Test complete factory workflow with multiple services."""
        # Register services
        factory.register_service("none", mock_none_service_class)
        factory.register_service("chain_of_thought", mock_cot_service_class)

        # Create services with different configurations
        none_config = AgentConfig(
            agent_type="none",
            model_provider="openai",
            model_name="gpt-4",
            model_parameters={},
            agent_parameters={},
        )

        cot_config = AgentConfig(
            agent_type="chain_of_thought",
            model_provider="anthropic",
            model_name="claude-3",
            model_parameters={"temperature": 0.5},
            agent_parameters={},
        )

        none_service = factory.create_service(none_config)
        cot_service = factory.create_service(cot_config)

        # Verify services are different instances
        assert none_service is not cot_service
        assert none_service.supports_agent_type("none") is True
        assert none_service.supports_agent_type("chain_of_thought") is False
        assert cot_service.supports_agent_type("chain_of_thought") is True
        assert cot_service.supports_agent_type("none") is False

    def test_service_instantiation_isolation(
        self,
        factory: ReasoningAgentFactory,
        mock_none_service_class: type[MockAgentService],
        sample_agent_config: AgentConfig,
    ) -> None:
        """Test that each create_service call creates a new instance."""
        factory.register_service("none", mock_none_service_class)

        service1 = factory.create_service(sample_agent_config)
        service2 = factory.create_service(sample_agent_config)

        # Should be different instances
        assert service1 is not service2
        assert type(service1) is type(service2)

    def test_factory_error_messages_detail(
        self,
        factory: ReasoningAgentFactory,
        mock_none_service_class: type[MockAgentService],
    ) -> None:
        """Test that factory provides detailed error messages."""
        factory.register_service("none", mock_none_service_class)

        # Test unsupported agent type error
        config = AgentConfig(
            agent_type="unsupported",
            model_provider="test",
            model_name="test",
            model_parameters={},
            agent_parameters={},
        )

        with pytest.raises(InvalidConfigurationError) as exc_info:
            factory.create_service(config)

        error = exc_info.value
        assert error.agent_type == "unsupported"
        assert "Unsupported agent type" in error.config_issue
        assert "Available types: ['none']" in error.config_issue

        # Test validation failure error
        class FailingValidationService(MockAgentService):
            def __init__(self) -> None:
                super().__init__("failing", validation_result=False)

        factory.register_service("failing", FailingValidationService)

        failing_config = AgentConfig(
            agent_type="failing",
            model_provider="test",
            model_name="test",
            model_parameters={},
            agent_parameters={},
        )

        with pytest.raises(InvalidConfigurationError) as exc_info:
            factory.create_service(failing_config)

        error = exc_info.value
        assert error.agent_type == "failing"
        assert "Configuration validation failed" in error.config_issue
