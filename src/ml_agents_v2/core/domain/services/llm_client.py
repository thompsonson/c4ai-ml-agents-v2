"""LLM Client domain service interface.

This module defines the domain interface for LLM clients, serving as the
Anti-Corruption Layer boundary between the domain and infrastructure layers.
All LLM client implementations must conform to this interface.
"""

from typing import Any, Protocol, runtime_checkable

from ..value_objects.answer import ParsedResponse


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
