"""Tests for model capabilities registry."""

import pytest

from ml_agents_v2.infrastructure.structured_output.model_capabilities import (
    ModelCapabilities,
    ModelCapabilitiesRegistry,
)


class TestModelCapabilities:
    """Test ModelCapabilities dataclass."""

    def test_model_capabilities_creation(self):
        """Test creating ModelCapabilities instance."""
        capabilities = ModelCapabilities(
            supports_structured_output=True,
            supports_logprobs=True,
            provider="openai",
            model_family="gpt-4",
        )

        assert capabilities.supports_structured_output is True
        assert capabilities.supports_logprobs is True
        assert capabilities.provider == "openai"
        assert capabilities.model_family == "gpt-4"

    def test_model_capabilities_immutability(self):
        """Test ModelCapabilities is immutable."""
        capabilities = ModelCapabilities(
            supports_structured_output=True,
            supports_logprobs=False,
            provider="anthropic",
            model_family="claude-3",
        )

        # Should raise AttributeError when trying to modify frozen dataclass
        with pytest.raises(AttributeError):
            capabilities.supports_logprobs = True  # type: ignore


class TestModelCapabilitiesRegistry:
    """Test ModelCapabilitiesRegistry functionality."""

    def test_get_capabilities_openai_models(self):
        """Test capability detection for OpenAI models."""
        # Test exact matches
        gpt4_capabilities = ModelCapabilitiesRegistry.get_capabilities("gpt-4")
        assert gpt4_capabilities.supports_structured_output is True
        assert gpt4_capabilities.supports_logprobs is True
        assert gpt4_capabilities.provider == "openai"
        assert gpt4_capabilities.model_family == "gpt-4"

        gpt35_capabilities = ModelCapabilitiesRegistry.get_capabilities("gpt-3.5-turbo")
        assert gpt35_capabilities.supports_structured_output is True
        assert gpt35_capabilities.supports_logprobs is True
        assert gpt35_capabilities.provider == "openai"
        assert gpt35_capabilities.model_family == "gpt-3.5"

    def test_get_capabilities_claude_models(self):
        """Test capability detection for Claude models."""
        claude_capabilities = ModelCapabilitiesRegistry.get_capabilities(
            "claude-3-opus"
        )
        assert claude_capabilities.supports_structured_output is True
        assert claude_capabilities.supports_logprobs is False
        assert claude_capabilities.provider == "anthropic"
        assert claude_capabilities.model_family == "claude-3"

    def test_get_capabilities_llama_models(self):
        """Test capability detection for Llama models."""
        llama_capabilities = ModelCapabilitiesRegistry.get_capabilities(
            "meta-llama/llama-3.1-8b-instruct"
        )
        assert llama_capabilities.supports_structured_output is True
        assert llama_capabilities.supports_logprobs is False
        assert llama_capabilities.provider == "meta"
        assert llama_capabilities.model_family == "llama-3.1"

    def test_get_capabilities_unknown_model(self):
        """Test fallback behavior for unknown models."""
        unknown_capabilities = ModelCapabilitiesRegistry.get_capabilities(
            "unknown-model"
        )
        assert unknown_capabilities.supports_structured_output is True
        assert unknown_capabilities.supports_logprobs is False
        assert unknown_capabilities.provider == "unknown"
        assert unknown_capabilities.model_family == "unknown"

    def test_supports_logprobs_method(self):
        """Test convenience method for logprobs support."""
        assert ModelCapabilitiesRegistry.supports_logprobs("gpt-4") is True
        assert ModelCapabilitiesRegistry.supports_logprobs("gpt-3.5-turbo") is True
        assert ModelCapabilitiesRegistry.supports_logprobs("claude-3-opus") is False
        assert (
            ModelCapabilitiesRegistry.supports_logprobs(
                "meta-llama/llama-3.1-8b-instruct"
            )
            is False
        )
        assert ModelCapabilitiesRegistry.supports_logprobs("unknown-model") is False

    def test_supports_structured_output_method(self):
        """Test convenience method for structured output support."""
        assert ModelCapabilitiesRegistry.supports_structured_output("gpt-4") is True
        assert (
            ModelCapabilitiesRegistry.supports_structured_output("claude-3-opus")
            is True
        )
        assert (
            ModelCapabilitiesRegistry.supports_structured_output(
                "meta-llama/llama-3.1-8b-instruct"
            )
            is True
        )
        assert (
            ModelCapabilitiesRegistry.supports_structured_output("unknown-model")
            is True
        )

    def test_partial_model_name_matching(self):
        """Test that partial model names use fallback behavior."""
        # Test partial matches that should fall back to default
        capabilities = ModelCapabilitiesRegistry.get_capabilities("gpt-4-custom")
        # Should still get OpenAI capabilities due to partial matching logic
        assert capabilities.supports_structured_output is True

    def test_all_registered_models_have_capabilities(self):
        """Test that all models in registry have valid capabilities."""
        registry = ModelCapabilitiesRegistry._capabilities

        for _model_name, capabilities in registry.items():
            assert isinstance(capabilities.supports_structured_output, bool)
            assert isinstance(capabilities.supports_logprobs, bool)
            assert isinstance(capabilities.provider, str)
            assert isinstance(capabilities.model_family, str)
            assert len(capabilities.provider) > 0
            assert len(capabilities.model_family) > 0

    def test_registry_completeness(self):
        """Test that registry includes expected model families."""
        expected_providers = {"openai", "anthropic", "meta", "google"}
        registry = ModelCapabilitiesRegistry._capabilities

        actual_providers = {cap.provider for cap in registry.values()}
        assert expected_providers.issubset(actual_providers)

        # Test that OpenAI models support logprobs
        openai_models = [
            name for name, cap in registry.items() if cap.provider == "openai"
        ]
        assert len(openai_models) > 0

        for model_name in openai_models:
            cap = registry[model_name]
            assert (
                cap.supports_logprobs is True
            ), f"OpenAI model {model_name} should support logprobs"

        # Test that non-OpenAI models don't support logprobs
        non_openai_models = [
            name for name, cap in registry.items() if cap.provider != "openai"
        ]
        for model_name in non_openai_models:
            cap = registry[model_name]
            assert (
                cap.supports_logprobs is False
            ), f"Non-OpenAI model {model_name} should not support logprobs"
