"""Concrete implementation of LLMClientFactory for multi-provider support.

This factory implements the N×M matrix of providers × parsing strategies,
enabling dynamic client creation based on model capabilities and configuration.
"""

from typing import Any

import structlog

from ...core.domain.services.llm_client import (
    LLMClient,
    LLMClientFactory,
    UnsupportedProviderError,
    UnsupportedStrategyError,
)
from ..parsers import MarvinParsingClient, NativeParsingClient, OutlinesParsingClient
from ..providers import (
    AnthropicClient,
    LiteLLMClient,
    OpenAIClient,
    OpenRouterClient,
)


class LLMClientFactoryImpl(LLMClientFactory):
    """Concrete implementation of LLMClientFactory with N×M matrix support.

    This factory creates LLM clients by:
    1. Auto-detecting provider from model name if not specified
    2. Creating base provider client
    3. Auto-selecting optimal parsing strategy if set to "auto"
    4. Wrapping base client with parsing strategy

    Supported providers: openrouter, openai, anthropic, litellm
    Supported strategies: auto, marvin, outlines, native
    """

    def __init__(
        self,
        provider_configs: dict[str, dict[str, Any]],
        default_provider: str = "openrouter",
        default_parsing_strategy: str = "auto",
    ):
        """Initialize factory with provider configurations.

        Args:
            provider_configs: Dict mapping provider names to configuration dicts
            default_provider: Default provider when auto-detection fails
            default_parsing_strategy: Default strategy when set to "auto"
        """
        self.provider_configs = provider_configs
        self.default_provider = default_provider
        self.default_parsing_strategy = default_parsing_strategy
        self._logger = structlog.get_logger(__name__)

    def create_client(
        self,
        model_name: str,
        provider: str | None = None,
        strategy: str = "auto",
    ) -> LLMClient:
        """Create appropriate LLM client for model and strategy combination.

        Args:
            model_name: Model identifier (e.g., "gpt-4", "claude-3-sonnet")
            provider: LLM provider or None for auto-detection from model name
            strategy: Parsing approach ("marvin", "outlines", "native", "auto")

        Returns:
            LLMClient: Configured client implementing domain interface

        Raises:
            UnsupportedProviderError: If provider is not supported or configured
            UnsupportedStrategyError: If strategy is not compatible with model
        """
        # Step 1: Auto-detect provider from model name if not specified
        if provider is None:
            provider = self._detect_provider(model_name)

        self._logger.debug(
            "Creating LLM client",
            model=model_name,
            provider=provider,
            strategy=strategy,
        )

        # Step 2: Create base provider client
        base_client = self._create_provider_client(provider)

        # Step 3: Auto-select parsing strategy if "auto"
        if strategy == "auto":
            strategy = self._select_optimal_strategy(model_name, provider)

        self._logger.debug(
            "Selected parsing strategy",
            model=model_name,
            provider=provider,
            strategy=strategy,
        )

        # Step 4: Wrap with parsing strategy
        return self._wrap_with_parser(base_client, strategy, model_name)

    def _detect_provider(self, model_name: str) -> str:
        """Auto-detect provider from model name prefix.

        Args:
            model_name: Model identifier

        Returns:
            Provider name (openai, anthropic, openrouter, etc.)
        """
        # OpenAI models
        if model_name.startswith(("gpt-", "o1-", "text-")):
            return "openai"
        # Anthropic Claude models
        elif model_name.startswith("claude-"):
            return "anthropic"
        # Check for provider prefix format (provider/model)
        elif "/" in model_name:
            prefix = model_name.split("/")[0].lower()
            # Map common provider prefixes
            provider_mapping = {
                "openai": "openai",
                "anthropic": "anthropic",
                "meta": "openrouter",  # Meta models usually via OpenRouter
                "google": "openrouter",
                "mistral": "openrouter",
                "cohere": "openrouter",
            }
            if prefix in provider_mapping:
                return provider_mapping[prefix]

        # Default fallback
        return self.default_provider

    def _create_provider_client(self, provider: str) -> LLMClient:
        """Create base LLM client for specified provider.

        Args:
            provider: Provider name (openrouter, openai, anthropic, litellm)

        Returns:
            Base LLM client instance

        Raises:
            UnsupportedProviderError: If provider not configured or unsupported
        """
        # Check if provider has configuration
        config = self.provider_configs.get(provider)
        if not config:
            raise UnsupportedProviderError(
                provider,
                supported_providers=list(self.provider_configs.keys()),
            )

        # Create provider-specific client
        try:
            if provider == "openrouter":
                return OpenRouterClient(**config)
            elif provider == "openai":
                # Check if API key is configured
                if not config.get("api_key"):
                    raise UnsupportedProviderError(
                        provider,
                        supported_providers=[
                            p
                            for p, c in self.provider_configs.items()
                            if c.get("api_key")
                        ],
                    )
                return OpenAIClient(**config)
            elif provider == "anthropic":
                if not config.get("api_key"):
                    raise UnsupportedProviderError(
                        provider,
                        supported_providers=[
                            p
                            for p, c in self.provider_configs.items()
                            if c.get("api_key")
                        ],
                    )
                return AnthropicClient(**config)
            elif provider == "litellm":
                return LiteLLMClient(config)
            else:
                raise UnsupportedProviderError(
                    provider,
                    supported_providers=[
                        "openrouter",
                        "openai",
                        "anthropic",
                        "litellm",
                    ],
                )
        except (ImportError, Exception) as e:
            self._logger.error(
                "Failed to create provider client",
                provider=provider,
                error=str(e),
            )
            raise

    def _select_optimal_strategy(self, model_name: str, provider: str) -> str:
        """Select optimal parsing strategy based on model capabilities.

        Args:
            model_name: Model identifier
            provider: Provider name

        Returns:
            Strategy name (marvin, outlines, native)
        """
        # OpenAI models support native structured output
        if provider == "openai" and model_name.startswith(("gpt-4", "gpt-3.5-turbo")):
            return "native"

        # Anthropic models work well with Marvin post-processing
        elif provider == "anthropic":
            return "marvin"

        # OpenRouter can use different strategies based on model
        elif provider == "openrouter":
            # If model supports structured output, use native
            if "gpt-4" in model_name or "gpt-3.5" in model_name:
                return "native"
            # Otherwise use Marvin
            return "marvin"

        # LiteLLM and others: default to Marvin
        else:
            return "marvin"

    def _wrap_with_parser(
        self, base_client: LLMClient, strategy: str, model_name: str
    ) -> LLMClient:
        """Wrap base client with parsing strategy.

        Args:
            base_client: Base LLM client
            strategy: Parsing strategy name
            model_name: Model identifier (for logging)

        Returns:
            Wrapped client with parsing capabilities

        Raises:
            UnsupportedStrategyError: If strategy is not supported
        """
        if strategy == "marvin":
            return MarvinParsingClient(base_client)
        elif strategy == "outlines":
            return OutlinesParsingClient(base_client)
        elif strategy == "native":
            return NativeParsingClient(base_client)
        else:
            raise UnsupportedStrategyError(
                strategy,
                supported_strategies=["marvin", "outlines", "native", "auto"],
            )

    def get_supported_providers(self) -> list[str]:
        """Return list of all supported provider names.

        Returns:
            List of provider names
        """
        return ["openrouter", "openai", "anthropic", "litellm"]

    def get_supported_strategies(self) -> list[str]:
        """Return list of all supported parsing strategies.

        Returns:
            List of strategy names
        """
        return ["auto", "marvin", "outlines", "native"]

    def validate_combination(
        self, model_name: str, provider: str, strategy: str
    ) -> bool:
        """Check if model + provider + strategy combination is valid.

        Args:
            model_name: Model identifier
            provider: Provider name
            strategy: Parsing strategy name

        Returns:
            True if combination is valid, False otherwise
        """
        # Check provider is supported
        if provider not in self.get_supported_providers():
            return False

        # Check strategy is supported
        if strategy not in self.get_supported_strategies():
            return False

        # Check provider has configuration
        if provider not in self.provider_configs:
            return False

        # All checks passed
        return True
