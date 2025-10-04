"""LiteLLM client for unified access to 100+ LLM providers.

This implementation uses LiteLLM to provide access to a wide range of models
from various providers through a single unified interface.
"""

from typing import Any

import structlog

from ...core.domain.services.llm_client import LLMClient
from ...core.domain.value_objects.answer import ParsedResponse


class LiteLLMClient(LLMClient):
    """LiteLLM provider for accessing 100+ models through unified interface.

    This client uses the LiteLLM library to provide access to models from:
    - OpenAI, Anthropic, Google, Cohere, Replicate
    - Hugging Face, Together AI, Anyscale
    - Local models via Ollama, vLLM, etc.
    """

    def __init__(self, config: dict[str, Any]):
        """Initialize LiteLLM client.

        Args:
            config: Configuration dictionary with provider-specific settings
                   Example: {"api_base": "http://localhost:11434", "api_key": "..."}
        """
        self.config = config
        self._logger = structlog.get_logger(__name__)

        # Import LiteLLM only when needed
        try:
            import litellm  # type: ignore[import-not-found]

            self.litellm = litellm

            # Configure LiteLLM with user settings
            if "api_base" in config:
                litellm.api_base = config["api_base"]
            if "api_key" in config:
                litellm.api_key = config["api_key"]

        except ImportError as e:
            raise ImportError(
                "litellm package is required for LiteLLM client. "
                "Install it with: pip install litellm"
            ) from e

    async def chat_completion(
        self,
        model: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> ParsedResponse:
        """Execute chat completion with LiteLLM.

        Args:
            model: Model identifier (can be from any LiteLLM-supported provider)
            messages: List of message dicts with 'role' and 'content' keys
            **kwargs: Additional model parameters (temperature, max_tokens, etc.)

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
        }

        # Add optional parameters
        if "max_tokens" in kwargs and kwargs["max_tokens"] is not None:
            request_params["max_tokens"] = kwargs["max_tokens"]
        if "top_p" in kwargs and kwargs["top_p"] is not None:
            request_params["top_p"] = kwargs["top_p"]
        if "frequency_penalty" in kwargs:
            request_params["frequency_penalty"] = kwargs["frequency_penalty"]
        if "presence_penalty" in kwargs:
            request_params["presence_penalty"] = kwargs["presence_penalty"]
        if "stop" in kwargs and kwargs["stop"] is not None:
            request_params["stop"] = kwargs["stop"]

        # Make async API call through LiteLLM
        api_response = await self.litellm.acompletion(**request_params)

        # Translate to domain type
        return self._translate_to_domain(api_response)

    def _translate_to_domain(self, api_response: Any) -> ParsedResponse:
        """Convert LiteLLM API response to domain ParsedResponse.

        Args:
            api_response: Raw API response from LiteLLM

        Returns:
            ParsedResponse: Clean domain object
        """
        self._logger.debug(
            "Translating LiteLLM response to domain type",
            response_type=type(api_response).__name__,
        )

        content = ""
        structured_data = None

        try:
            # LiteLLM returns OpenAI-compatible response format
            if hasattr(api_response, "choices") and api_response.choices:
                choice = api_response.choices[0]
                message = choice.message if hasattr(choice, "message") else choice

                # Get content
                if hasattr(message, "content"):
                    content = message.content or ""
                elif isinstance(message, dict):
                    content = message.get("content", "")

                self._logger.debug(
                    "Extracted content from LiteLLM response",
                    content_length=len(content),
                )

        except Exception as e:
            self._logger.error(
                "Error translating LiteLLM response",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

        # LiteLLM doesn't provide structured output - will use parsing wrappers
        return ParsedResponse(content=content, structured_data=structured_data)

    async def health_check(self) -> dict[str, Any]:
        """Check LiteLLM API health.

        Returns:
            Dictionary with health status

        Raises:
            Exception: For API errors or connection issues
        """
        try:
            # Use a simple, fast model for health check
            # Default to ollama if api_base is configured for it
            model = self.config.get("default_model", "ollama/llama2")

            response = await self.litellm.acompletion(
                model=model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
            )

            return {
                "status": "healthy",
                "message": "LiteLLM API connection successful",
                "model_used": model,
                "response_id": getattr(response, "id", "N/A"),
            }

        except Exception:
            raise
