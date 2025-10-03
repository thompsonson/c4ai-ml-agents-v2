"""Tests for model capabilities registry."""

from ml_agents_v2.infrastructure.model_capabilities import (
    ModelCapabilitiesRegistry,
)


class TestModelCapabilitiesRegistry:
    """Test ModelCapabilitiesRegistry functionality."""

    def test_supports_logprobs_openai_models(self):
        """Test logprobs support detection for OpenAI models."""
        # Test exact matches
        assert ModelCapabilitiesRegistry.supports_logprobs("gpt-4") is True
        assert ModelCapabilitiesRegistry.supports_logprobs("gpt-4-turbo") is True
        assert ModelCapabilitiesRegistry.supports_logprobs("gpt-4o") is True
        assert ModelCapabilitiesRegistry.supports_logprobs("gpt-3.5-turbo") is True
        assert ModelCapabilitiesRegistry.supports_logprobs("o1") is True
        assert ModelCapabilitiesRegistry.supports_logprobs("o1-mini") is True

    def test_supports_logprobs_with_provider_prefix(self):
        """Test logprobs support detection with provider prefixes."""
        # Test with provider prefixes
        assert ModelCapabilitiesRegistry.supports_logprobs("openai/gpt-4") is True
        assert (
            ModelCapabilitiesRegistry.supports_logprobs("openai/gpt-3.5-turbo") is True
        )

    def test_supports_logprobs_non_openai_models(self):
        """Test logprobs support detection for non-OpenAI models."""
        # These models don't support logprobs
        assert ModelCapabilitiesRegistry.supports_logprobs("claude-3-sonnet") is False
        assert (
            ModelCapabilitiesRegistry.supports_logprobs("anthropic/claude-3-sonnet")
            is False
        )
        assert (
            ModelCapabilitiesRegistry.supports_logprobs("llama-3.1-8b-instruct")
            is False
        )
        assert (
            ModelCapabilitiesRegistry.supports_logprobs("meta/llama-3.1-8b-instruct")
            is False
        )

    def test_supports_logprobs_partial_matching(self):
        """Test partial model name matching for logprobs."""
        # Test partial matches
        assert ModelCapabilitiesRegistry.supports_logprobs("gpt-4-custom") is True
        assert ModelCapabilitiesRegistry.supports_logprobs("gpt-3.5-turbo-16k") is True
        assert ModelCapabilitiesRegistry.supports_logprobs("openai/gpt-4o-mini") is True

    def test_supports_logprobs_unknown_model(self):
        """Test logprobs support for unknown models."""
        # Unknown model should return False
        assert ModelCapabilitiesRegistry.supports_logprobs("unknown-model") is False
        assert (
            ModelCapabilitiesRegistry.supports_logprobs("custom/unknown-model") is False
        )
