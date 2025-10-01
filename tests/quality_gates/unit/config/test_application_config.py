"""Tests for ApplicationConfig."""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from ml_agents_v2.config.application_config import ApplicationConfig


class TestApplicationConfig:
    """Test ApplicationConfig environment variable loading and validation."""

    def test_config_loads_from_environment_variables(self):
        """Test that ApplicationConfig loads values from environment variables."""
        with patch.dict(
            os.environ,
            {
                "OPENROUTER_API_KEY": "sk-or-v1-test-key",
                "DATABASE_URL": "sqlite:///data/test.db",
                "LOG_LEVEL": "DEBUG",
            },
        ):
            config = ApplicationConfig()

            assert config.openrouter_api_key == "sk-or-v1-test-key"
            assert config.database_url == "sqlite:///data/test.db"
            assert config.log_level == "DEBUG"

    def test_config_has_sensible_defaults(self):
        """Test that ApplicationConfig provides sensible defaults."""
        with patch.dict(
            os.environ, {"OPENROUTER_API_KEY": "sk-or-v1-test-key"}, clear=True
        ):
            config = ApplicationConfig()

            assert config.database_url == "sqlite:///data/ml_agents_v2.db"
            assert config.openrouter_base_url == "https://openrouter.ai/api/v1"
            assert config.log_level == "INFO"
            assert config.app_name == "ML-Agents-v2"

    def test_config_validates_required_fields(self):
        """Test that ApplicationConfig validates required fields."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValidationError, match="Field required"):
                ApplicationConfig(_env_file=None)

    def test_config_loads_agent_defaults(self):
        """Test that ApplicationConfig loads agent default parameters."""
        with patch.dict(
            os.environ, {"OPENROUTER_API_KEY": "sk-or-v1-test-key"}, clear=True
        ):
            config = ApplicationConfig()

            # None agent defaults
            assert config.none_agent_defaults["temperature"] == 0.1
            assert config.none_agent_defaults["max_tokens"] == 800

            # Chain of thought agent defaults
            assert config.cot_agent_defaults["temperature"] == 0.8
            assert config.cot_agent_defaults["max_tokens"] == 1000

    def test_config_supports_env_file(self):
        """Test that ApplicationConfig can load from .env file."""
        # This will be tested once we create the .env.example
        pass
