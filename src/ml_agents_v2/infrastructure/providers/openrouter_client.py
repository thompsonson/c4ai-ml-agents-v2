"""OpenRouter API client as Anti-Corruption Layer.

This implementation serves as the Anti-Corruption Layer (ACL) between the domain
and external LLM APIs. It implements the LLMClient domain interface and ensures
all external API types are normalized to consistent domain types.

ALL type normalization happens here and ONLY here.
"""

from typing import Any

import structlog
from openai import AsyncOpenAI

from ...core.domain.services.llm_client import LLMClient
from ...core.domain.value_objects.answer import ParsedResponse


class OpenRouterClient(LLMClient):
    """Anti-Corruption Layer for OpenRouter API.

    This class implements the LLMClient domain interface and serves as the
    ONLY point where external API types are normalized to domain types.

    Key responsibilities:
    1. Implement LLMClient domain interface
    2. Normalize ALL external API types to domain types
    3. Handle API variations (Pydantic models, dicts, None)
    4. Never leak external types to domain layer
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://openrouter.ai/api/v1",
        timeout: int = 60,
        max_retries: int = 3,
    ):
        """Initialize OpenRouter Anti-Corruption Layer.

        Args:
            api_key: OpenRouter API key for authentication
            base_url: OpenRouter API base URL
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts for failed requests
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._logger = structlog.get_logger(__name__)

        # Initialize AsyncOpenAI client configured for OpenRouter
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
        )

    async def chat_completion(
        self,
        model: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> ParsedResponse:
        """Execute chat completion request with ACL normalization.

        This is THE boundary where external API chaos becomes domain order.
        All external API responses are IMMEDIATELY normalized to domain types.

        Args:
            model: Model identifier (e.g., "gpt-4", "claude-3-sonnet")
            messages: List of message dicts with 'role' and 'content' keys
            **kwargs: Additional model parameters (temperature, max_tokens, etc.)

        Returns:
            ParsedResponse: Normalized domain object with consistent types

        Raises:
            Domain-appropriate exceptions for infrastructure errors
        """
        # Make external API call (last place external types exist)
        api_response = await self._make_api_request(model, messages, **kwargs)

        # IMMEDIATELY normalize to domain types - external types die here
        return self._translate_to_domain(api_response)

    async def _make_api_request(
        self,
        model: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> Any:
        """Make the actual API request to OpenRouter using OpenAI client.

        This method uses the AsyncOpenAI client to communicate with OpenRouter.
        It returns the raw OpenAI response object that gets normalized by _translate_to_domain.
        """
        # Prepare extra headers for OpenRouter attribution
        extra_headers = {
            "HTTP-Referer": "https://github.com/c4ai/ml-agents-v2",
            "X-Title": "ML-Agents-v2",
        }

        # Build request parameters with defaults
        request_params = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "top_p": kwargs.get("top_p", 1.0),
            "frequency_penalty": kwargs.get("frequency_penalty", 0.0),
            "presence_penalty": kwargs.get("presence_penalty", 0.0),
            "extra_headers": extra_headers,
        }

        # Add optional parameters if provided
        if "max_tokens" in kwargs and kwargs["max_tokens"] is not None:
            request_params["max_tokens"] = kwargs["max_tokens"]
        if "stop" in kwargs and kwargs["stop"] is not None:
            request_params["stop"] = kwargs["stop"]

        # Add any additional parameters (structured output, logprobs, etc.)
        for key, value in kwargs.items():
            if key not in request_params and value is not None:
                request_params[key] = value

        # Make the request using OpenAI client (includes built-in retries)
        response = await self._client.chat.completions.create(**request_params)
        return response

    def _translate_to_domain(self, api_response: Any) -> ParsedResponse:
        """THE method that converts external API chaos to domain order.

        This is the ONLY place in the system where external API types
        are handled. All normalization happens here.

        Args:
            api_response: Raw API response from external service

        Returns:
            ParsedResponse: Clean domain object with normalized types
        """
        self._logger.debug(
            "Starting API response translation to domain types",
            response_type=type(api_response).__name__,
            has_choices=hasattr(api_response, "choices"),
        )

        # Extract content from response
        content = ""
        structured_data = None

        try:
            # Handle OpenAI ChatCompletion response object
            if hasattr(api_response, "choices") and api_response.choices:
                choice = api_response.choices[0]
                message = choice.message

                self._logger.debug(
                    "Processing message from API response",
                    message_type=type(message).__name__,
                    has_content=hasattr(message, "content"),
                    has_parsed=hasattr(message, "parsed"),
                )

                # Get content (handle both string and None)
                content = message.content or ""

                # Get structured data if available (OpenAI structured output)
                try:
                    if hasattr(message, "parsed") and message.parsed:
                        structured_data = message.parsed
                        self._logger.debug(
                            "Extracted structured data from response",
                            structured_data_type=type(structured_data).__name__,
                        )
                except (TypeError, AttributeError) as e:
                    self._logger.error(
                        "Failed to extract structured data from OpenAI response",
                        message_type=type(message).__name__,
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                    # Continue without structured data rather than failing
                    structured_data = None

        except Exception as e:
            self._logger.error(
                "Critical error in response translation",
                api_response_type=type(api_response).__name__,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

        self._logger.debug(
            "Completed API response translation",
            content_length=len(content),
            has_structured_data=structured_data is not None,
        )

        # Return clean domain object
        return ParsedResponse(content=content, structured_data=structured_data)

    async def health_check(self) -> dict[str, Any]:
        """Check OpenRouter API health by making a simple API call.

        Returns:
            Dictionary with health status and response details

        Raises:
            Exception: For API errors or connection issues
        """
        try:
            # Make a simple chat completion request to test connectivity
            response = await self._client.chat.completions.create(
                model="openai/gpt-3.5-turbo",  # Use a reliable, cheap model for health check
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
                extra_headers={
                    "HTTP-Referer": "https://github.com/c4ai/ml-agents-v2",
                    "X-Title": "ML-Agents-v2",
                },
            )

            # If we get here, the API is responding
            return {
                "status": "healthy",
                "message": "OpenRouter API connection successful",
                "model_used": response.model,
                "response_id": response.id,
            }

        except Exception:
            # Re-raise the exception to be handled by the health service
            raise
