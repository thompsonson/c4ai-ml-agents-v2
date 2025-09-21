"""Synchronous OpenRouter API client implementation."""

import json
from typing import Any, Union

import httpx


class OpenRouterClient:
    """Synchronous OpenRouter API client for chat completions.

    Provides a simple interface to OpenRouter's chat completion API
    with automatic error handling and retry logic.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://openrouter.ai/api/v1",
        timeout: int = 60,
        max_retries: int = 3,
    ):
        """Initialize OpenRouter client.

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

    def chat_completion(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Union[int, None] = None,
        top_p: float = 1.0,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0,
        stop: Union[str, list[str], None] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute chat completion request to OpenRouter.

        Args:
            model: Model identifier (e.g., "meta-llama/llama-3.1-8b-instruct")
            messages: List of message objects with role and content
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter
            frequency_penalty: Frequency penalty parameter
            presence_penalty: Presence penalty parameter
            stop: Stop sequences for generation
            **kwargs: Additional parameters to pass to the API

        Returns:
            Complete API response as dictionary

        Raises:
            httpx.HTTPStatusError: For HTTP error responses (4xx, 5xx)
            httpx.TimeoutException: For request timeouts
            httpx.RequestError: For other request errors
        """
        url = f"{self.base_url}/chat/completions"
        headers = self.get_headers()

        # Build request payload
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "frequency_penalty": frequency_penalty,
            "presence_penalty": presence_penalty,
        }

        # Add optional parameters
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if stop is not None:
            payload["stop"] = stop

        # Add any additional parameters
        payload.update(kwargs)

        # Make the request with retries
        last_exception: Union[
            httpx.HTTPStatusError, httpx.TimeoutException, httpx.RequestError, None
        ] = None

        for attempt in range(self.max_retries + 1):
            try:
                response = httpx.post(
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

    def health_check(self) -> dict[str, Any]:
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

        response = httpx.get(
            url=url,
            headers=headers,
            timeout=self.timeout,
        )

        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]
