"""Tests for Phase 9 multi-provider domain exceptions."""

import pytest

from ml_agents_v2.core.domain.services.llm_client import (
    UnsupportedModelError,
    UnsupportedProviderError,
    UnsupportedStrategyError,
)


class TestUnsupportedProviderError:
    """Test UnsupportedProviderError exception behavior."""

    def test_unsupported_provider_error_creation(self):
        """Test basic UnsupportedProviderError creation."""
        error = UnsupportedProviderError("invalid-provider")

        assert error.provider == "invalid-provider"
        assert error.supported_providers is None
        assert "invalid-provider" in str(error)
        assert "not supported" in str(error)

    def test_unsupported_provider_error_with_supported_list(self):
        """Test UnsupportedProviderError with supported providers list."""
        supported = ["openrouter", "openai", "anthropic"]
        error = UnsupportedProviderError(
            "invalid-provider", supported_providers=supported
        )

        assert error.provider == "invalid-provider"
        assert error.supported_providers == supported
        assert "invalid-provider" in str(error)
        assert "openrouter" in str(error)
        assert "openai" in str(error)
        assert "anthropic" in str(error)

    def test_unsupported_provider_error_message_format(self):
        """Test error message formatting is clear and helpful."""
        supported = ["openrouter", "openai"]
        error = UnsupportedProviderError("badprovider", supported_providers=supported)

        message = str(error)
        assert "badprovider" in message
        assert "Supported providers:" in message
        # Message should list providers in a readable format
        assert "openrouter" in message and "openai" in message


class TestUnsupportedStrategyError:
    """Test UnsupportedStrategyError exception behavior."""

    def test_unsupported_strategy_error_creation(self):
        """Test basic UnsupportedStrategyError creation."""
        error = UnsupportedStrategyError("invalid-strategy")

        assert error.strategy == "invalid-strategy"
        assert error.supported_strategies is None
        assert "invalid-strategy" in str(error)
        assert "not supported" in str(error)

    def test_unsupported_strategy_error_with_supported_list(self):
        """Test UnsupportedStrategyError with supported strategies list."""
        supported = ["marvin", "outlines", "native", "auto"]
        error = UnsupportedStrategyError(
            "invalid-strategy", supported_strategies=supported
        )

        assert error.strategy == "invalid-strategy"
        assert error.supported_strategies == supported
        assert "invalid-strategy" in str(error)
        assert "marvin" in str(error)
        assert "auto" in str(error)


class TestUnsupportedModelError:
    """Test UnsupportedModelError exception behavior."""

    def test_unsupported_model_error_creation(self):
        """Test basic UnsupportedModelError creation."""
        error = UnsupportedModelError("unknown-model-v1")

        assert error.model == "unknown-model-v1"
        assert error.provider is None
        assert error.reason is None
        assert "unknown-model-v1" in str(error)
        assert "not supported" in str(error)

    def test_unsupported_model_error_with_provider_context(self):
        """Test UnsupportedModelError with provider context."""
        error = UnsupportedModelError("gpt-5", provider="openai")

        assert error.model == "gpt-5"
        assert error.provider == "openai"
        assert "gpt-5" in str(error)
        assert "openai" in str(error)

    def test_unsupported_model_error_with_reason(self):
        """Test UnsupportedModelError with detailed reason."""
        error = UnsupportedModelError(
            "old-model-v1", provider="openai", reason="Model deprecated on 2024-01-01"
        )

        assert error.model == "old-model-v1"
        assert error.provider == "openai"
        assert error.reason == "Model deprecated on 2024-01-01"
        assert "old-model-v1" in str(error)
        assert "deprecated" in str(error)


class TestExceptionInheritance:
    """Test exception inheritance and exception handling patterns."""

    def test_all_exceptions_inherit_from_exception(self):
        """Test all multi-provider exceptions inherit from Exception."""
        assert issubclass(UnsupportedProviderError, Exception)
        assert issubclass(UnsupportedStrategyError, Exception)
        assert issubclass(UnsupportedModelError, Exception)

    def test_exceptions_can_be_caught_individually(self):
        """Test exceptions can be caught by specific type."""
        try:
            raise UnsupportedProviderError("test")
        except UnsupportedProviderError as e:
            assert e.provider == "test"
        except Exception:
            pytest.fail("Should have caught UnsupportedProviderError")

    def test_exceptions_can_be_caught_generically(self):
        """Test exceptions can be caught as generic Exception."""
        # Test that multi-provider exceptions can be caught as base Exception
        caught = False
        try:
            raise UnsupportedStrategyError("test")
        except Exception:  # noqa: B017
            caught = True

        assert caught
