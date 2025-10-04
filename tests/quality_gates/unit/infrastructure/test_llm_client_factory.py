"""Tests for LLMClientFactoryImpl multi-provider factory."""

from unittest.mock import Mock

import pytest

from ml_agents_v2.core.domain.services.llm_client import (
    LLMClient,
    UnsupportedProviderError,
    UnsupportedStrategyError,
)
from ml_agents_v2.infrastructure.factories.llm_client_factory_impl import (
    LLMClientFactoryImpl,
)
from ml_agents_v2.infrastructure.parsers import (
    MarvinParsingClient,
    NativeParsingClient,
    OutlinesParsingClient,
)
from ml_agents_v2.infrastructure.providers import (
    AnthropicClient,
    LiteLLMClient,
    OpenAIClient,
    OpenRouterClient,
)


class TestFactoryInitialization:
    """Test factory creation and configuration."""

    def test_factory_initialization_with_provider_configs(self):
        """Test factory initializes with provider configurations."""
        provider_configs = {
            "openrouter": {"api_key": "test-key", "base_url": "https://test.com"},
            "openai": {"api_key": "openai-key"},
        }

        factory = LLMClientFactoryImpl(
            provider_configs=provider_configs,
            default_provider="openrouter",
            default_parsing_strategy="auto",
        )

        assert factory.provider_configs == provider_configs
        assert factory.default_provider == "openrouter"
        assert factory.default_parsing_strategy == "auto"

    def test_factory_initialization_with_empty_config(self):
        """Test factory can initialize with empty provider configs."""
        factory = LLMClientFactoryImpl(
            provider_configs={},
            default_provider="openrouter",
        )

        assert factory.provider_configs == {}
        assert factory.default_provider == "openrouter"


class TestProviderAutoDetection:
    """Test provider auto-detection from model names."""

    @pytest.fixture
    def factory(self):
        """Create factory for testing auto-detection."""
        return LLMClientFactoryImpl(
            provider_configs={
                "openrouter": {"api_key": "test"},
                "openai": {"api_key": "test"},
                "anthropic": {"api_key": "test"},
            },
            default_provider="openrouter",
        )

    def test_detect_openai_from_gpt_prefix(self, factory):
        """Test auto-detection of OpenAI from gpt- prefix."""
        provider = factory._detect_provider("gpt-4")
        assert provider == "openai"

        provider = factory._detect_provider("gpt-3.5-turbo")
        assert provider == "openai"

    def test_detect_openai_from_o1_prefix(self, factory):
        """Test auto-detection of OpenAI from o1- prefix."""
        provider = factory._detect_provider("o1-preview")
        assert provider == "openai"

    def test_detect_anthropic_from_claude_prefix(self, factory):
        """Test auto-detection of Anthropic from claude- prefix."""
        provider = factory._detect_provider("claude-3-sonnet")
        assert provider == "anthropic"

        provider = factory._detect_provider("claude-3-opus")
        assert provider == "anthropic"

    def test_detect_openrouter_from_provider_slash_format(self, factory):
        """Test detection from provider/model format."""
        # These should be detected as openrouter (common format)
        provider = factory._detect_provider("meta/llama-3")
        assert provider == "openrouter"

        provider = factory._detect_provider("google/gemini-pro")
        assert provider == "openrouter"

    def test_default_provider_when_no_match(self, factory):
        """Test default provider used when no pattern matches."""
        provider = factory._detect_provider("unknown-model-123")
        assert provider == "openrouter"  # Default


class TestClientCreation:
    """Test client creation for each provider."""

    @pytest.fixture
    def factory(self):
        """Create factory with all provider configs."""
        return LLMClientFactoryImpl(
            provider_configs={
                "openrouter": {
                    "api_key": "or-key",
                    "base_url": "https://openrouter.ai/api/v1",
                    "timeout": 60,
                    "max_retries": 3,
                },
                "openai": {
                    "api_key": "openai-key",
                    "timeout": 60,
                    "max_retries": 3,
                },
                "anthropic": {
                    "api_key": "anthropic-key",
                    "timeout": 60,
                },
                "litellm": {
                    "api_key": "litellm-key",
                },
            },
        )

    def test_create_openrouter_client(self, factory):
        """Test creating OpenRouter client."""
        client = factory._create_provider_client("openrouter")

        assert isinstance(client, OpenRouterClient)
        assert client.api_key == "or-key"

    def test_create_openai_client(self, factory):
        """Test creating OpenAI client."""
        client = factory._create_provider_client("openai")

        assert isinstance(client, OpenAIClient)
        assert client.api_key == "openai-key"

    def test_create_anthropic_client(self, factory):
        """Test creating Anthropic client."""
        client = factory._create_provider_client("anthropic")

        assert isinstance(client, AnthropicClient)
        assert client.api_key == "anthropic-key"

    def test_create_litellm_client(self, factory):
        """Test creating LiteLLM client (or raises ImportError if not installed)."""
        try:
            client = factory._create_provider_client("litellm")
            assert isinstance(client, LiteLLMClient)
        except ImportError as e:
            # LiteLLM is optional dependency - allow test to pass if not installed
            assert "litellm package is required" in str(e)
            pytest.skip("LiteLLM not installed (optional dependency)")

    def test_create_client_with_missing_config_raises_error(self):
        """Test creating client for unconfigured provider raises error."""
        factory = LLMClientFactoryImpl(
            provider_configs={"openrouter": {"api_key": "test"}},
        )

        with pytest.raises(UnsupportedProviderError) as exc_info:
            factory._create_provider_client("openai")

        assert exc_info.value.provider == "openai"

    def test_create_client_with_missing_api_key_raises_error(self):
        """Test creating client with None API key raises error."""
        factory = LLMClientFactoryImpl(
            provider_configs={
                "openrouter": {"api_key": "test"},
                "openai": {"api_key": None},  # Missing API key
            },
        )

        with pytest.raises(UnsupportedProviderError):
            factory._create_provider_client("openai")


class TestStrategySelection:
    """Test auto-strategy selection logic."""

    @pytest.fixture
    def factory(self):
        """Create factory for testing strategy selection."""
        return LLMClientFactoryImpl(
            provider_configs={"openrouter": {"api_key": "test"}},
        )

    def test_auto_strategy_selects_native_for_gpt4(self, factory):
        """Test auto-selection of native strategy for GPT-4."""
        strategy = factory._select_optimal_strategy("gpt-4", "openai")
        assert strategy == "native"

        strategy = factory._select_optimal_strategy("gpt-3.5-turbo", "openai")
        assert strategy == "native"

    def test_auto_strategy_selects_marvin_for_anthropic(self, factory):
        """Test auto-selection of marvin strategy for Anthropic."""
        strategy = factory._select_optimal_strategy("claude-3-sonnet", "anthropic")
        assert strategy == "marvin"

    def test_auto_strategy_selects_marvin_default(self, factory):
        """Test marvin is default strategy for unknown models."""
        strategy = factory._select_optimal_strategy("unknown-model", "litellm")
        assert strategy == "marvin"


class TestParserWrapping:
    """Test parser wrapping behavior."""

    @pytest.fixture
    def mock_base_client(self):
        """Create mock base LLM client."""
        mock = Mock(spec=LLMClient)
        return mock

    @pytest.fixture
    def factory(self):
        """Create factory for testing."""
        return LLMClientFactoryImpl(
            provider_configs={"openrouter": {"api_key": "test"}},
        )

    def test_wrap_with_marvin_parser(self, factory, mock_base_client):
        """Test wrapping with Marvin parser."""
        wrapped = factory._wrap_with_parser(mock_base_client, "marvin", "test-model")

        assert isinstance(wrapped, MarvinParsingClient)
        assert wrapped.base_client is mock_base_client

    def test_wrap_with_native_parser(self, factory, mock_base_client):
        """Test wrapping with native parser."""
        wrapped = factory._wrap_with_parser(mock_base_client, "native", "gpt-4")

        assert isinstance(wrapped, NativeParsingClient)
        assert wrapped.base_client is mock_base_client

    def test_wrap_with_outlines_parser(self, factory, mock_base_client):
        """Test wrapping with Outlines parser."""
        wrapped = factory._wrap_with_parser(mock_base_client, "outlines", "test-model")

        assert isinstance(wrapped, OutlinesParsingClient)
        assert wrapped.base_client is mock_base_client

    def test_unsupported_strategy_raises_error(self, factory, mock_base_client):
        """Test unsupported strategy raises UnsupportedStrategyError."""
        with pytest.raises(UnsupportedStrategyError) as exc_info:
            factory._wrap_with_parser(mock_base_client, "invalid-strategy", "test")

        assert exc_info.value.strategy == "invalid-strategy"


class TestFactoryProtocolCompliance:
    """Test factory implements domain protocol correctly."""

    @pytest.fixture
    def factory(self):
        """Create factory for protocol compliance testing."""
        return LLMClientFactoryImpl(
            provider_configs={
                "openrouter": {"api_key": "test", "base_url": "https://test.com"},
            },
        )

    def test_get_supported_providers_returns_list(self, factory):
        """Test get_supported_providers returns correct list."""
        providers = factory.get_supported_providers()

        assert isinstance(providers, list)
        assert "openrouter" in providers
        assert "openai" in providers
        assert "anthropic" in providers
        assert "litellm" in providers

    def test_get_supported_strategies_returns_list(self, factory):
        """Test get_supported_strategies returns correct list."""
        strategies = factory.get_supported_strategies()

        assert isinstance(strategies, list)
        assert "auto" in strategies
        assert "marvin" in strategies
        assert "outlines" in strategies
        assert "native" in strategies

    def test_validate_combination_accepts_valid_combo(self, factory):
        """Test validate_combination returns True for valid combinations."""
        assert factory.validate_combination("gpt-4", "openrouter", "auto") is True
        assert factory.validate_combination("gpt-4", "openrouter", "marvin") is True

    def test_validate_combination_rejects_invalid_provider(self, factory):
        """Test validate_combination rejects unsupported provider."""
        assert (
            factory.validate_combination("gpt-4", "invalid-provider", "auto") is False
        )

    def test_validate_combination_rejects_invalid_strategy(self, factory):
        """Test validate_combination rejects unsupported strategy."""
        assert factory.validate_combination("gpt-4", "openrouter", "invalid") is False

    def test_validate_combination_rejects_unconfigured_provider(self):
        """Test validate_combination rejects provider without config."""
        factory = LLMClientFactoryImpl(
            provider_configs={},  # No providers configured
        )

        assert factory.validate_combination("gpt-4", "openrouter", "auto") is False


class TestEndToEndClientCreation:
    """Test complete end-to-end client creation flow."""

    @pytest.fixture
    def factory(self):
        """Create factory with full configuration."""
        return LLMClientFactoryImpl(
            provider_configs={
                "openrouter": {"api_key": "or-key", "base_url": "https://test.com"},
                "openai": {"api_key": "openai-key"},
            },
            default_provider="openrouter",
            default_parsing_strategy="auto",
        )

    def test_create_client_with_auto_provider_and_strategy(self, factory):
        """Test creating client with auto-detection."""
        # Should detect OpenAI provider and native strategy
        client = factory.create_client("gpt-4", provider=None, strategy="auto")

        # Should be wrapped with native parser
        assert isinstance(client, NativeParsingClient)
        # Base client should be OpenAI
        assert isinstance(client.base_client, OpenAIClient)

    def test_create_client_with_explicit_provider(self, factory):
        """Test creating client with explicit provider."""
        client = factory.create_client(
            "test-model", provider="openrouter", strategy="marvin"
        )

        assert isinstance(client, MarvinParsingClient)
        assert isinstance(client.base_client, OpenRouterClient)

    def test_create_client_respects_strategy_parameter(self, factory):
        """Test explicit strategy parameter is respected."""
        # Force marvin even though auto would choose native
        client = factory.create_client("gpt-4", provider="openai", strategy="marvin")

        assert isinstance(client, MarvinParsingClient)
        assert isinstance(client.base_client, OpenAIClient)
