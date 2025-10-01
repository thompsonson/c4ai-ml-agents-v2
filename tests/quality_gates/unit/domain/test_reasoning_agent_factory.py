"""Tests for reasoning agent service factory."""

import pytest

from ml_agents_v2.core.domain.services.reasoning.chain_of_thought_agent_service import (
    ChainOfThoughtAgentService,
)
from ml_agents_v2.core.domain.services.reasoning.none_agent_service import (
    NoneAgentService,
)
from ml_agents_v2.core.domain.services.reasoning.reasoning_agent_factory import (
    ReasoningAgentServiceFactory,
)
from ml_agents_v2.core.domain.services.reasoning.reasoning_agent_service import (
    ReasoningAgentService,
)


class TestReasoningAgentServiceFactory:
    """Test ReasoningAgentServiceFactory functionality."""

    @pytest.fixture
    def factory(self):
        """Create factory instance."""
        return ReasoningAgentServiceFactory()

    def test_factory_initialization(self, factory):
        """Test factory initialization with default services."""
        supported_types = factory.get_supported_types()
        assert "none" in supported_types
        assert "chain_of_thought" in supported_types
        assert len(supported_types) == 2

    def test_create_service_none_agent(self, factory):
        """Test creating None agent service."""
        service = factory.create_service("none")
        assert isinstance(service, NoneAgentService)
        assert service.get_agent_type() == "none"

    def test_create_service_chain_of_thought_agent(self, factory):
        """Test creating Chain of Thought agent service."""
        service = factory.create_service("chain_of_thought")
        assert isinstance(service, ChainOfThoughtAgentService)
        assert service.get_agent_type() == "chain_of_thought"

    def test_create_service_unknown_agent_type(self, factory):
        """Test creating service with unknown agent type raises ValueError."""
        with pytest.raises(ValueError, match="Unknown agent type: unknown_type"):
            factory.create_service("unknown_type")

    def test_get_supported_types(self, factory):
        """Test getting list of supported agent types."""
        types = factory.get_supported_types()
        assert isinstance(types, list)
        assert "none" in types
        assert "chain_of_thought" in types

    def test_register_new_service(self, factory):
        """Test registering new service type."""

        class CustomAgentService(ReasoningAgentService):
            def get_prompt_strategy(self):
                pass

            def process_question(self, question, config):
                pass

            def process_response(self, raw_response, context):
                pass

            def validate_config(self, config):
                pass

            def get_agent_type(self):
                return "custom"

        # Register new service
        factory.register_service("custom", CustomAgentService)

        # Verify it's supported
        assert "custom" in factory.get_supported_types()

        # Verify it can be created
        service = factory.create_service("custom")
        assert isinstance(service, CustomAgentService)
        assert service.get_agent_type() == "custom"

    def test_create_registry_dictionary(self, factory):
        """Test creating registry dictionary for EvaluationOrchestrator."""
        registry = factory.create_registry()

        assert isinstance(registry, dict)
        assert "none" in registry
        assert "chain_of_thought" in registry

        # Verify instances are created
        assert isinstance(registry["none"], NoneAgentService)
        assert isinstance(registry["chain_of_thought"], ChainOfThoughtAgentService)

        # Verify each instance is properly configured
        assert registry["none"].get_agent_type() == "none"
        assert registry["chain_of_thought"].get_agent_type() == "chain_of_thought"

    def test_create_registry_creates_new_instances(self, factory):
        """Test that create_registry creates new instances each time."""
        registry1 = factory.create_registry()
        registry2 = factory.create_registry()

        # Should be different instances
        assert registry1["none"] is not registry2["none"]
        assert registry1["chain_of_thought"] is not registry2["chain_of_thought"]

        # But should be same type
        assert type(registry1["none"]) is type(registry2["none"])
        assert type(registry1["chain_of_thought"]) is type(
            registry2["chain_of_thought"]
        )

    def test_validate_agent_type_valid_types(self, factory):
        """Test validation for supported agent types."""
        result = factory.validate_agent_type("none")
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0

        result = factory.validate_agent_type("chain_of_thought")
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0

    def test_validate_agent_type_invalid_type(self, factory):
        """Test validation for unsupported agent types."""
        result = factory.validate_agent_type("invalid_type")
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert "Unsupported agent type 'invalid_type'" in result.errors[0]
        assert "Supported types: ['none', 'chain_of_thought']" in result.errors[0]
        assert len(result.warnings) == 0

    def test_factory_is_extensible(self, factory):
        """Test that factory can be extended with new agent types."""

        class TreeOfThoughtAgentService(ReasoningAgentService):
            def get_prompt_strategy(self):
                pass

            def process_question(self, question, config):
                pass

            def process_response(self, raw_response, context):
                pass

            def validate_config(self, config):
                pass

            def get_agent_type(self):
                return "tree_of_thought"

        # Initially not supported
        assert "tree_of_thought" not in factory.get_supported_types()

        # Register new type
        factory.register_service("tree_of_thought", TreeOfThoughtAgentService)

        # Now supported
        assert "tree_of_thought" in factory.get_supported_types()

        # Can create instance
        service = factory.create_service("tree_of_thought")
        assert isinstance(service, TreeOfThoughtAgentService)

        # Appears in registry
        registry = factory.create_registry()
        assert "tree_of_thought" in registry
        assert isinstance(registry["tree_of_thought"], TreeOfThoughtAgentService)

        # Validation works
        result = factory.validate_agent_type("tree_of_thought")
        assert result.is_valid is True

    def test_factory_preserves_service_independence(self, factory):
        """Test that created services are independent instances."""
        service1 = factory.create_service("none")
        service2 = factory.create_service("none")

        # Should be different instances
        assert service1 is not service2

        # Should be same type
        assert type(service1) is type(service2)
        assert service1.get_agent_type() == service2.get_agent_type()

    def test_factory_service_registry_immutability(self):
        """Test that factory instance preserves its service registry."""
        factory1 = ReasoningAgentServiceFactory()
        factory2 = ReasoningAgentServiceFactory()

        # Both should have same initial services
        assert factory1.get_supported_types() == factory2.get_supported_types()

        # Registering on one shouldn't affect the other
        class CustomService(ReasoningAgentService):
            def get_agent_type(self):
                return "custom"

            def get_prompt_strategy(self):
                pass

            def process_question(self, question, config):
                pass

            def process_response(self, raw_response, context):
                pass

            def validate_config(self, config):
                pass

        factory1.register_service("custom", CustomService)

        assert "custom" in factory1.get_supported_types()
        assert "custom" not in factory2.get_supported_types()
