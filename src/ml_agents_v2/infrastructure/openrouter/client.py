"""OpenRouter API client as Anti-Corruption Layer.

This implementation serves as the Anti-Corruption Layer (ACL) between the domain
and external LLM APIs. It implements the LLMClient domain interface and ensures
all external API types are normalized to consistent domain types.

ALL type normalization happens here and ONLY here.
"""

import json
from typing import Any

import httpx
import structlog

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

    def get_headers(self) -> dict[str, str]:
        """Get HTTP headers for OpenRouter requests.

        Returns:
            Dictionary of headers including authentication and attribution
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/c4ai/ml-agents-v2",
            "X-Title": "ML-Agents-v2",
        }
        return headers

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
    ) -> dict[str, Any]:
        """Make the actual API request to OpenRouter.

        This method handles the low-level HTTP communication and retry logic.
        It returns raw API response that gets normalized by _translate_to_domain.
        """
        url = f"{self.base_url}/chat/completions"
        headers = self.get_headers()

        # Build request payload with default parameters
        payload = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "top_p": kwargs.get("top_p", 1.0),
            "frequency_penalty": kwargs.get("frequency_penalty", 0.0),
            "presence_penalty": kwargs.get("presence_penalty", 0.0),
        }

        # Add optional parameters
        if "max_tokens" in kwargs and kwargs["max_tokens"] is not None:
            payload["max_tokens"] = kwargs["max_tokens"]
        if "stop" in kwargs and kwargs["stop"] is not None:
            payload["stop"] = kwargs["stop"]

        # Add any additional parameters (structured output, etc.)
        for key, value in kwargs.items():
            if key not in payload and value is not None:
                payload[key] = value

        # Make the request with retries
        last_exception: (
            httpx.HTTPStatusError | httpx.TimeoutException | httpx.RequestError | None
        ) = None

        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        url=url,
                        headers=headers,
                        content=json.dumps(payload),
                        timeout=self.timeout,
                    )

                # Raise for HTTP error status codes
                response.raise_for_status()
                return response.json()  # type: ignore[no-any-return]

            except httpx.HTTPStatusError as e:
                last_exception = e
                # Don't retry on client errors (4xx) except rate limits
                if 400 <= e.response.status_code < 500:
                    if e.response.status_code == 429:  # Rate limit - can retry
                        if attempt < self.max_retries:
                            continue
                    # For other 4xx errors, don't retry
                    raise
                # For 5xx errors, retry
                if attempt < self.max_retries:
                    continue
                raise

            except (httpx.TimeoutException, httpx.RequestError) as e:
                last_exception = e
                # Retry on network/timeout errors
                if attempt < self.max_retries:
                    continue
                raise

        # If we exhausted all retries, raise the last exception
        if last_exception:
            raise last_exception

        # This should never be reached, but needed for type checking
        raise RuntimeError("Failed to complete request after all retries")

    def _translate_to_domain(self, api_response: dict[str, Any]) -> ParsedResponse:
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
            has_choices=(
                "choices" in api_response if isinstance(api_response, dict) else "N/A"
            ),
        )

        # Extract content from response
        content = ""
        structured_data = None

        try:
            if "choices" in api_response and api_response["choices"]:
                choice = api_response["choices"][0]
                message = choice.get("message", {})

                self._logger.debug(
                    "Processing message from API response",
                    message_type=type(message).__name__,
                    message_keys=(
                        list(message.keys()) if hasattr(message, "keys") else "N/A"
                    ),
                    has_content=(
                        "content" in message
                        if hasattr(message, "__contains__")
                        else "N/A"
                    ),
                    has_parsed=(
                        "parsed" in message
                        if hasattr(message, "__contains__")
                        else "N/A"
                    ),
                )

                # Get content
                content = message.get("content", "")

                # Get structured data if available (OpenAI structured output)
                try:
                    if "parsed" in message and message["parsed"]:
                        structured_data = message["parsed"]
                        self._logger.debug(
                            "Extracted structured data from response",
                            structured_data_type=type(structured_data).__name__,
                        )
                except (TypeError, AttributeError) as e:
                    self._logger.error(
                        "Failed to extract structured data - ChatCompletionMessage object detected",
                        message_type=type(message).__name__,
                        message_attributes=(
                            dir(message) if hasattr(message, "__dict__") else "N/A"
                        ),
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
        """Check OpenRouter API health and get account information.

        Returns:
            Dictionary with health status and account details

        Raises:
            httpx.HTTPStatusError: For HTTP error responses
            httpx.TimeoutException: For request timeouts
            httpx.RequestError: For other request errors
        """
        url = f"{self.base_url}/auth/key"
        headers = self.get_headers()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url=url,
                headers=headers,
                timeout=self.timeout,
            )

        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]
