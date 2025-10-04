"""Anthropic API client implementation.

This implementation provides access to Claude models via the Anthropic SDK,
translating between OpenAI-style message format and Anthropic's format.
"""

from typing import Any

import structlog

from ...core.domain.services.llm_client import LLMClient
from ...core.domain.value_objects.answer import ParsedResponse


class AnthropicClient(LLMClient):
    """Anthropic provider implementation for Claude models.

    This client translates between OpenAI-style messages and Anthropic's SDK,
    providing a consistent interface while leveraging Anthropic's native capabilities.
    """

    def __init__(self, api_key: str, timeout: int = 60):
        """Initialize Anthropic client.

        Args:
            api_key: Anthropic API key for authentication
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.timeout = timeout
        self._logger = structlog.get_logger(__name__)

        # Import Anthropic SDK only when needed
        try:
            from anthropic import AsyncAnthropic

            self._client = AsyncAnthropic(
                api_key=api_key,
                timeout=timeout,
            )
        except ImportError as e:
            raise ImportError(
                "anthropic package is required for Anthropic client. "
                "Install it with: pip install anthropic"
            ) from e

    async def chat_completion(
        self,
        model: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> ParsedResponse:
        """Execute chat completion with Anthropic.

        Args:
            model: Model identifier (e.g., "claude-3-sonnet", "claude-3-opus")
            messages: List of message dicts with 'role' and 'content' keys
            **kwargs: Additional model parameters (temperature, max_tokens, etc.)

        Returns:
            ParsedResponse: Normalized domain object

        Raises:
            Domain-appropriate exceptions for infrastructure errors
        """
        # Convert OpenAI-style messages to Anthropic format
        # Anthropic separates system messages from conversation messages
        system_message = None
        conversation_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                conversation_messages.append(
                    {"role": msg["role"], "content": msg["content"]}
                )

        # Build request parameters for Anthropic SDK
        request_params = {
            "model": model,
            "messages": conversation_messages,
            "max_tokens": kwargs.get(
                "max_tokens", 1024
            ),  # Anthropic requires max_tokens
            "temperature": kwargs.get("temperature", 0.7),
        }

        # Add system message if present
        if system_message:
            request_params["system"] = system_message

        # Add optional parameters
        if "top_p" in kwargs and kwargs["top_p"] is not None:
            request_params["top_p"] = kwargs["top_p"]
        if "stop_sequences" in kwargs and kwargs["stop_sequences"] is not None:
            request_params["stop_sequences"] = kwargs["stop_sequences"]

        # Make API call
        api_response = await self._client.messages.create(**request_params)

        # Translate to domain type
        return self._translate_to_domain(api_response)

    def _translate_to_domain(self, api_response: Any) -> ParsedResponse:
        """Convert Anthropic API response to domain ParsedResponse.

        Args:
            api_response: Raw API response from Anthropic

        Returns:
            ParsedResponse: Clean domain object
        """
        self._logger.debug(
            "Translating Anthropic response to domain type",
            response_type=type(api_response).__name__,
        )

        content = ""

        try:
            # Anthropic returns content in content blocks
            if hasattr(api_response, "content") and api_response.content:
                # Concatenate all text content blocks
                content_parts = []
                for block in api_response.content:
                    if hasattr(block, "text"):
                        content_parts.append(block.text)
                content = "".join(content_parts)

                self._logger.debug(
                    "Extracted content from Anthropic response",
                    content_length=len(content),
                )

        except Exception as e:
            self._logger.error(
                "Error translating Anthropic response",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

        # Anthropic doesn't have native structured output yet
        # Will be wrapped with Marvin parser for structured extraction
        return ParsedResponse(content=content, structured_data=None)

    async def health_check(self) -> dict[str, Any]:
        """Check Anthropic API health.

        Returns:
            Dictionary with health status

        Raises:
            Exception: For API errors or connection issues
        """
        try:
            response = await self._client.messages.create(
                model="claude-3-haiku-20240307",  # Use cheapest model for health check
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
            )

            return {
                "status": "healthy",
                "message": "Anthropic API connection successful",
                "model_used": response.model,
                "response_id": response.id,
            }

        except Exception:
            raise
