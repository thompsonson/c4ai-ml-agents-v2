"""Instructor-based LLM client for structured outputs.

This client uses the instructor library to handle structured outputs automatically.
No manual JSON schema prompts - instructor handles everything internally.
"""

from typing import Any

import instructor  # type: ignore
from openai import OpenAI

from ...core.domain.value_objects.answer import ParsedResponse


class InstructorClient:
    """LLM client using instructor library for automatic structured output."""

    def __init__(self, api_key: str, base_url: str = "https://openrouter.ai/api/v1"):
        """Initialize instructor client with OpenAI-compatible API.

        Args:
            api_key: API key for the service
            base_url: Base URL for the API (defaults to OpenRouter)
        """
        # Create base OpenAI client
        base_client = OpenAI(api_key=api_key, base_url=base_url)

        # Patch with instructor for structured outputs
        self.instructor_client = instructor.from_openai(base_client)
        self.base_client = base_client

    async def chat_completion(
        self, model: str, messages: list[dict[str, str]], **kwargs: Any
    ) -> ParsedResponse:
        """Execute chat completion with automatic structured output handling.

        If response_model is provided in kwargs, uses instructor for structured
        output. Otherwise, falls back to regular OpenAI completion.

        Args:
            model: Model identifier (e.g., "anthropic/claude-3-sonnet")
            messages: List of message dicts with 'role' and 'content' keys
            **kwargs: Additional parameters including optional response_model

        Returns:
            ParsedResponse: Normalized response with structured_data if applicable
        """
        response_model = kwargs.pop("response_model", None)

        if response_model:
            # Use instructor - NO JSON PROMPT MANIPULATION
            try:
                result = self.instructor_client.chat.completions.create(
                    model=model,
                    messages=messages,  # Clean domain prompts only
                    response_model=response_model,
                    **kwargs,
                )

                # Return with structured data
                if hasattr(result, "model_dump"):
                    structured_data = result.model_dump()
                else:
                    structured_data = result.dict()

                return ParsedResponse(
                    content=str(result), structured_data=structured_data
                )

            except Exception as e:
                # If instructor fails, we still need to return a ParsedResponse
                # This maintains the domain interface contract
                raise e

        # Regular OpenAI call without structured output
        response = self.base_client.chat.completions.create(
            model=model, messages=messages, **kwargs  # type: ignore
        )

        content = response.choices[0].message.content or ""
        return ParsedResponse(content=content)
