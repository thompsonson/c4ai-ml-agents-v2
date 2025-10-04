"""LLM Client domain service interface.

This module defines the domain interface for LLM clients, serving as the
Anti-Corruption Layer boundary between the domain and infrastructure layers.
All LLM client implementations must conform to this interface.
"""

from typing import Any, Protocol, runtime_checkable

from ..value_objects.answer import ParsedResponse


class UnsupportedProviderError(Exception):
    """Raised when an unsupported LLM provider is requested."""

    def __init__(self, provider: str, supported_providers: list[str] | None = None):
        """Initialize with provider name and optional list of supported providers.

        Args:
            provider: The unsupported provider that was requested
            supported_providers: Optional list of supported provider names
        """
        self.provider = provider
        self.supported_providers = supported_providers

        if supported_providers:
            message = (
                f"Provider '{provider}' is not supported. "
                f"Supported providers: {', '.join(supported_providers)}"
            )
        else:
            message = f"Provider '{provider}' is not supported or not configured"

        super().__init__(message)


class UnsupportedStrategyError(Exception):
    """Raised when an unsupported parsing strategy is requested."""

    def __init__(self, strategy: str, supported_strategies: list[str] | None = None):
        """Initialize with strategy name and optional list of supported strategies.

        Args:
            strategy: The unsupported strategy that was requested
            supported_strategies: Optional list of supported strategy names
        """
        self.strategy = strategy
        self.supported_strategies = supported_strategies

        if supported_strategies:
            message = (
                f"Strategy '{strategy}' is not supported. "
                f"Supported strategies: {', '.join(supported_strategies)}"
            )
        else:
            message = f"Strategy '{strategy}' is not supported"

        super().__init__(message)


class UnsupportedModelError(Exception):
    """Raised when an unsupported model is requested."""

    def __init__(
        self,
        model: str,
        provider: str | None = None,
        reason: str | None = None,
    ):
        """Initialize with model name and optional context.

        Args:
            model: The unsupported model that was requested
            provider: Optional provider name for context
            reason: Optional reason why the model is unsupported
        """
        self.model = model
        self.provider = provider
        self.reason = reason

        parts = [f"Model '{model}' is not supported"]
        if provider:
            parts.append(f"by provider '{provider}'")
        if reason:
            parts.append(f": {reason}")

        super().__init__(" ".join(parts))


@runtime_checkable
class LLMClient(Protocol):
    """Domain service interface for LLM clients.

    This protocol defines the contract that all LLM client implementations
    must follow. It serves as the Anti-Corruption Layer boundary, ensuring
    that external API variations are normalized to consistent domain types.

    All implementations must:
    1. Return ParsedResponse objects with normalized content
    2. Handle token usage normalization internally
    3. Convert external API errors to domain-appropriate exceptions
    4. Never leak external API types into the domain layer
    """

    async def chat_completion(
        self, model: str, messages: list[dict[str, str]], **kwargs: Any
    ) -> ParsedResponse:
        """Execute chat completion request.

        Args:
            model: Model identifier (e.g., "gpt-4", "claude-3-sonnet")
            messages: List of message dicts with 'role' and 'content' keys
            **kwargs: Additional model parameters (temperature, max_tokens, etc.)

        Returns:
            ParsedResponse: Normalized response with consistent domain types

        Raises:
            Domain-appropriate exceptions for infrastructure errors
        """
        ...


class LLMClientFactory(Protocol):
    """Domain interface for creating LLM clients with multi-provider support.

    Application services depend on this factory interface rather than concrete
    LLM clients, enabling dynamic client selection based on model capabilities
    and configuration.
    """

    def create_client(
        self,
        model_name: str,
        provider: str | None = None,
        strategy: str = "auto",
    ) -> LLMClient:
        """Create appropriate LLM client for model and strategy.

        Args:
            model_name: Model identifier (e.g., "gpt-4", "claude-3-sonnet")
            provider: LLM provider or None for auto-detection from model name
            strategy: Parsing approach ("marvin", "outlines", "native", "auto")

        Returns:
            LLMClient: Configured client implementing domain interface

        Raises:
            UnsupportedProviderError: If provider is not supported
            UnsupportedStrategyError: If strategy is not compatible with model
            UnsupportedModelError: If model is not supported by any provider
        """
        ...

    def get_supported_providers(self) -> list[str]:
        """Return list of all supported provider names."""
        ...

    def get_supported_strategies(self) -> list[str]:
        """Return list of all supported parsing strategies."""
        ...

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
        ...
