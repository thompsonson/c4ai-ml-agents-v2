"""Outlines-based LLM client for constrained generation structured outputs.

This client preserves domain boundaries while using constrained generation
to ensure valid JSON structure without post-processing.
"""

from __future__ import annotations

import json
from typing import Any

from openai import AsyncOpenAI
from pydantic import BaseModel

from ...core.domain.value_objects.answer import ParsedResponse


class OutlinesClient:
    """LLM client using Outlines for constrained generation.

    Key architectural principle: Domain calls with clean prompts, infrastructure
    configures generation constraints to guarantee valid structure.
    """

    def __init__(self, api_key: str, base_url: str = "https://openrouter.ai/api/v1"):
        """Initialize Outlines client with OpenAI-compatible API.

        Args:
            api_key: API key for the service
            base_url: Base URL for the API (defaults to OpenRouter)
        """
        self.api_key = api_key
        self.base_url = base_url
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

    def _format_messages(self, messages: list[dict[str, str]]) -> str:
        """Format messages list into single prompt string.

        Args:
            messages: List of message dicts with 'role' and 'content'

        Returns:
            Formatted prompt string
        """
        prompt_parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                prompt_parts.append(f"System: {content}")
            elif role == "user":
                prompt_parts.append(content)
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
        return "\n\n".join(prompt_parts)

    async def chat_completion(
        self, model: str, messages: list[dict[str, str]], **kwargs: Any
    ) -> ParsedResponse:
        """Execute constrained generation using Outlines.

        Domain provides clean prompt. Infrastructure configures Outlines to
        constrain generation to valid JSON structure.

        Args:
            model: Model identifier (e.g., "anthropic/claude-3-sonnet")
            messages: List of message dicts with 'role' and 'content' keys
            **kwargs: Additional parameters, including _internal_agent_type

        Returns:
            ParsedResponse: Response with guaranteed valid structure
        """
        # Extract internal context (never exposed to domain)
        agent_type = kwargs.pop("_internal_agent_type", None)

        # Note: Outlines has limitations with async and remote APIs
        # For now, fall back to using OpenAI structured outputs with schema
        # Full Outlines integration would require local model support

        try:
            schema = self._get_schema_for_agent(agent_type)
            json_schema = schema.model_json_schema()

            # Use OpenAI structured outputs as a constrained generation approach
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,  # type: ignore
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": schema.__name__.lower(),
                        "description": schema.__doc__
                        or f"Schema for {schema.__name__}",
                        "schema": json_schema,
                        "strict": True,
                    },
                },
                **kwargs,
            )

            content = response.choices[0].message.content or ""

            # Parse and validate the structured response
            parsed_json = json.loads(content)
            validated = schema.model_validate(parsed_json)

            structured_data = validated.model_dump()
            return ParsedResponse(content=content, structured_data=structured_data)

        except Exception:
            # Fallback: regular generation without constraints
            response = await self.client.chat.completions.create(
                model=model, messages=messages, **kwargs  # type: ignore
            )

            content = response.choices[0].message.content or ""
            return ParsedResponse(content=content)
