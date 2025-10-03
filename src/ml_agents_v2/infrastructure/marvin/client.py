"""Marvin-based LLM client for post-processing structured outputs.

This client preserves domain boundaries by never exposing infrastructure types
through the domain interface. It uses Marvin to extract structured data from
natural language responses in a post-processing step.
"""

from __future__ import annotations

from typing import Any

import marvin
from openai import AsyncOpenAI
from pydantic import BaseModel

from ...core.domain.value_objects.answer import ParsedResponse


class MarvinClient:
    """LLM client using Marvin for post-processing structured output extraction.

    Key architectural principle: Domain calls this with clean prompts and gets
    ParsedResponse back. Infrastructure handles schema mapping internally using
    the _internal_agent_type context parameter.
    """

    def __init__(self, api_key: str, base_url: str = "https://openrouter.ai/api/v1"):
        """Initialize Marvin client with OpenAI-compatible API.

        Args:
            api_key: API key for the service
            base_url: Base URL for the API (defaults to OpenRouter)
        """
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    def _get_schema_for_agent(self, agent_type: str | None) -> type[BaseModel]:
        """Map domain agent type string to infrastructure schema.

        This is pure infrastructure logic - domain never sees these types.

        Args:
            agent_type: Domain agent type string (e.g., "none", "chain_of_thought")

        Returns:
            Infrastructure Pydantic model for structured output
        """
        from ..models import ChainOfThoughtOutput, DirectAnswerOutput

        mapping: dict[str, type[BaseModel]] = {
            "none": DirectAnswerOutput,
            "chain_of_thought": ChainOfThoughtOutput,
        }
        return mapping.get(agent_type or "none", DirectAnswerOutput)

    async def chat_completion(
        self, model: str, messages: list[dict[str, str]], **kwargs: Any
    ) -> ParsedResponse:
        """Execute chat completion with Marvin post-processing.

        Domain calls this with clean prompts. Infrastructure handles structured
        output extraction transparently using Marvin.

        Args:
            model: Model identifier (e.g., "anthropic/claude-3-sonnet")
            messages: List of message dicts with 'role' and 'content' keys
            **kwargs: Additional parameters, including _internal_agent_type

        Returns:
            ParsedResponse: Normalized response with structured_data
        """
        # Extract internal context (never exposed to domain)
        agent_type = kwargs.pop("_internal_agent_type", None)

        # Call 1: Get natural language response with clean domain prompt
        response = await self.client.chat.completions.create(
            model=model, messages=messages, **kwargs  # type: ignore[arg-type]
        )

        content = response.choices[0].message.content or ""

        # Call 2: Use Marvin to extract structured data (infrastructure only)
        schema = self._get_schema_for_agent(agent_type)

        # Marvin extracts structure from natural language
        # If this fails, let the exception propagate - no fallback
        extracted: Any = await marvin.extract_async(
            content, target=schema, instructions="Extract the structured data"
        )
        structured: BaseModel = (
            extracted[0] if isinstance(extracted, list) and extracted else extracted
        )

        # Return with both content and structured data
        structured_data = structured.model_dump()
        return ParsedResponse(content=content, structured_data=structured_data)
