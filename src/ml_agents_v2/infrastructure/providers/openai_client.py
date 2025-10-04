"""OpenAI API client with native structured output support.

This implementation provides direct access to OpenAI models with support for
native structured output via response_format parameter.
"""

from typing import Any

import structlog
from openai import AsyncOpenAI

from ...core.domain.services.llm_client import LLMClient
from ...core.domain.value_objects.answer import ParsedResponse


class OpenAIClient(LLMClient):
    """OpenAI provider implementation with native structured output support.

    This client uses OpenAI's native structured output capabilities via the
    response_format parameter for models that support it (GPT-4, GPT-3.5-turbo).
    """

    def __init__(self, api_key: str, timeout: int = 60, max_retries: int = 3):
        """Initialize OpenAI client.

        Args:
            api_key: OpenAI API key for authentication
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts for failed requests
        """
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self._logger = structlog.get_logger(__name__)

        # Initialize AsyncOpenAI client with standard base URL
        self._client = AsyncOpenAI(
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
        )

    async def chat_completion(
        self,
        model: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> ParsedResponse:
        """Execute chat completion with OpenAI.

        Args:
            model: Model identifier (e.g., "gpt-4", "gpt-3.5-turbo")
            messages: List of message dicts with 'role' and 'content' keys
            **kwargs: Additional model parameters (temperature, response_format, etc.)

        Returns:
            ParsedResponse: Normalized domain object

        Raises:
            Domain-appropriate exceptions for infrastructure errors
        """
        # Build request parameters
        request_params = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "top_p": kwargs.get("top_p", 1.0),
            "frequency_penalty": kwargs.get("frequency_penalty", 0.0),
            "presence_penalty": kwargs.get("presence_penalty", 0.0),
        }

        # Add optional parameters
        if "max_tokens" in kwargs and kwargs["max_tokens"] is not None:
            request_params["max_tokens"] = kwargs["max_tokens"]
        if "stop" in kwargs and kwargs["stop"] is not None:
            request_params["stop"] = kwargs["stop"]
        if "response_format" in kwargs and kwargs["response_format"] is not None:
            request_params["response_format"] = kwargs["response_format"]
        if "logprobs" in kwargs:
            request_params["logprobs"] = kwargs["logprobs"]

        # Make API call
        api_response = await self._client.chat.completions.create(**request_params)

        # Translate to domain type
        return self._translate_to_domain(api_response)

    def _translate_to_domain(self, api_response: Any) -> ParsedResponse:
        """Convert OpenAI API response to domain ParsedResponse.

        Args:
            api_response: Raw API response from OpenAI

        Returns:
            ParsedResponse: Clean domain object
        """
        self._logger.debug(
            "Translating OpenAI response to domain type",
            response_type=type(api_response).__name__,
        )

        content = ""
        structured_data = None

        try:
            if hasattr(api_response, "choices") and api_response.choices:
                choice = api_response.choices[0]
                message = choice.message

                # Get content
                content = message.content or ""

                # Get structured data if available (from response_format)
                if hasattr(message, "parsed") and message.parsed:
                    structured_data = message.parsed
                    self._logger.debug(
                        "Extracted structured data from OpenAI response",
                        structured_data_type=type(structured_data).__name__,
                    )

        except Exception as e:
            self._logger.error(
                "Error translating OpenAI response",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

        return ParsedResponse(content=content, structured_data=structured_data)

    async def health_check(self) -> dict[str, Any]:
        """Check OpenAI API health.

        Returns:
            Dictionary with health status

        Raises:
            Exception: For API errors or connection issues
        """
        try:
            response = await self._client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
            )

            return {
                "status": "healthy",
                "message": "OpenAI API connection successful",
                "model_used": response.model,
                "response_id": response.id,
            }

        except Exception:
            raise
