"""Tests for AgentConfig value object."""

import pytest

from ml_agents_v2.core.domain.value_objects.agent_config import AgentConfig


class TestAgentConfig:
    """Test AgentConfig value object behavior."""

    def test_agent_config_creation(self) -> None:
        """Test basic AgentConfig creation with valid parameters."""
        config = AgentConfig(
            agent_type="chain_of_thought",
            model_provider="openrouter",
            model_name="anthropic/claude-3-sonnet",
            model_parameters={"temperature": 0.7, "max_tokens": 1000},
            agent_parameters={},
        )

        assert config.agent_type == "chain_of_thought"
        assert config.model_provider == "openrouter"
        assert config.model_name == "anthropic/claude-3-sonnet"
        assert config.model_parameters == {"temperature": 0.7, "max_tokens": 1000}
        assert config.agent_parameters == {}

    def test_agent_config_value_equality(self) -> None:
        """Test that AgentConfigs with same values are equal."""
        config1 = AgentConfig(
            agent_type="none",
            model_provider="openrouter",
            model_name="gpt-4",
            model_parameters={"temperature": 0.5},
            agent_parameters={},
        )

        config2 = AgentConfig(
            agent_type="none",
            model_provider="openrouter",
            model_name="gpt-4",
            model_parameters={"temperature": 0.5},
            agent_parameters={},
        )

        assert config1.equals(config2)
        assert config1 is not config2  # Different instances

    def test_agent_config_value_inequality(self) -> None:
        """Test that AgentConfigs with different values are not equal."""
        config1 = AgentConfig(
            agent_type="none",
            model_provider="openrouter",
            model_name="gpt-4",
            model_parameters={"temperature": 0.5},
            agent_parameters={},
        )

        config2 = AgentConfig(
            agent_type="chain_of_thought",  # Different agent_type
            model_provider="openrouter",
            model_name="gpt-4",
            model_parameters={"temperature": 0.5},
            agent_parameters={},
        )

        assert not config1.equals(config2)

    def test_agent_config_validation_valid_agent_type(self) -> None:
        """Test validation accepts valid agent types."""
        config = AgentConfig(
            agent_type="none",
            model_provider="openrouter",
            model_name="gpt-4",
            model_parameters={},
            agent_parameters={},
        )

        result = config.validate_configuration()
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_agent_config_validation_invalid_agent_type(self) -> None:
        """Test validation rejects invalid agent types."""
        config = AgentConfig(
            agent_type="invalid_agent",
            model_provider="openrouter",
            model_name="gpt-4",
            model_parameters={},
            agent_parameters={},
        )

        result = config.validate_configuration()
        assert result.is_valid is False
        assert "agent_type" in str(result.errors)

    def test_agent_config_validation_invalid_temperature(self) -> None:
        """Test validation rejects invalid model parameters."""
        config = AgentConfig(
            agent_type="none",
            model_provider="openrouter",
            model_name="gpt-4",
            model_parameters={"temperature": 5.0},  # Invalid: > 2.0
            agent_parameters={},
        )

        result = config.validate_configuration()
        assert result.is_valid is False
        assert "temperature" in str(result.errors)

    def test_agent_config_to_dict(self) -> None:
        """Test serialization to dictionary."""
        config = AgentConfig(
            agent_type="chain_of_thought",
            model_provider="openrouter",
            model_name="anthropic/claude-3-sonnet",
            model_parameters={"temperature": 0.8, "max_tokens": 1500},
            agent_parameters={"some_param": "value"},
        )

        result = config.to_dict()
        expected = {
            "agent_type": "chain_of_thought",
            "model_provider": "openrouter",
            "model_name": "anthropic/claude-3-sonnet",
            "model_parameters": {"temperature": 0.8, "max_tokens": 1500},
            "agent_parameters": {"some_param": "value"},
        }

        assert result == expected

    def test_agent_config_immutability(self) -> None:
        """Test that AgentConfig is immutable after creation."""
        config = AgentConfig(
            agent_type="none",
            model_provider="openrouter",
            model_name="gpt-4",
            model_parameters={"temperature": 0.7},
            agent_parameters={},
        )

        # Should not be able to modify attributes
        with pytest.raises(AttributeError):
            config.agent_type = "chain_of_thought"  # type: ignore

        # Should not be able to modify dictionary contents
        with pytest.raises(TypeError):
            config.model_parameters["temperature"] = 0.5  # type: ignore
