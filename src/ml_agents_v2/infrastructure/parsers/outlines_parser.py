"""Outlines-based constrained generation parsing strategy.

This parsing client uses constrained generation principles (currently via OpenAI
structured output) to ensure valid JSON structure. Future enhancement could add
true Outlines constrained generation for local models.
"""

from typing import Any

import structlog
from pydantic import BaseModel

from ...core.domain.services.llm_client import LLMClient
from ...core.domain.value_objects.answer import ParsedResponse


class OutlinesParsingClient(LLMClient):
    """Wraps LLM client with constrained generation for structured output.

    Currently uses OpenAI's native structured output as the constrained
    generation mechanism. Future versions could integrate true Outlines
    library for local model constrained generation.
    """

    def __init__(self, base_client: LLMClient):
        """Initialize Outlines parser with base LLM client.

        Args:
            base_client: The base LLM client to wrap
        """
        self.base_client = base_client
        self._logger = structlog.get_logger(__name__)

    def _get_schema_for_agent(self, agent_type: str | None) -> type[BaseModel]:
        """Map domain agent type to infrastructure Pydantic schema.

        Args:
            agent_type: Domain agent type (e.g., "none", "chain_of_thought")

        Returns:
            Infrastructure Pydantic model for structured output
        """
        from ..models import ChainOfThoughtOutput, DirectAnswerOutput

        mapping: dict[str, type[BaseModel]] = {
            "none": DirectAnswerOutput,
            "chain_of_thought": ChainOfThoughtOutput,
        }
        return mapping.get(agent_type or "none", DirectAnswerOutput)

    def _create_response_format(self, schema: type[BaseModel]) -> dict[str, Any]:
        """Create response_format for constrained generation.

        Args:
            schema: Pydantic model class

        Returns:
            Dictionary with response_format specification
        """
        json_schema = schema.model_json_schema()
        return {
            "type": "json_schema",
            "json_schema": {
                "name": schema.__name__.lower(),
                "description": schema.__doc__ or f"Schema for {schema.__name__}",
                "schema": json_schema,
                "strict": True,
            },
        }

    async def chat_completion(
        self, model: str, messages: list[dict[str, str]], **kwargs: Any
    ) -> ParsedResponse:
        """Execute chat completion with constrained generation.

        Args:
            model: Model identifier
            messages: List of message dicts
            **kwargs: Additional parameters, including _internal_agent_type

        Returns:
            ParsedResponse with structured_data from constrained generation

        Raises:
            Various exceptions if parsing fails
        """
        # Extract internal context (infrastructure-only parameter)
        agent_type = kwargs.pop("_internal_agent_type", None)

        # Get schema and create response_format for constrained generation
        schema = self._get_schema_for_agent(agent_type)
        response_format = self._create_response_format(schema)

        # Add response_format to kwargs for constrained generation
        kwargs["response_format"] = response_format

        self._logger.debug(
            "Using constrained generation (Outlines-style)",
            agent_type=agent_type,
            schema=schema.__name__,
        )

        try:
            # Call base client with response_format constraints
            response = await self.base_client.chat_completion(model, messages, **kwargs)

            # Response should have structured_data from constrained generation
            if not response.has_structured_data():
                self._logger.warning(
                    "Constrained generation did not return structured_data, falling back",
                    model=model,
                    agent_type=agent_type,
                )
                # If no structured data, try to parse from content
                import json

                try:
                    parsed_json = json.loads(response.content)
                    validated = schema.model_validate(parsed_json)
                    structured_data = validated.model_dump()
                    return ParsedResponse(
                        content=response.content, structured_data=structured_data
                    )
                except (json.JSONDecodeError, Exception) as e:
                    self._logger.error(
                        "Failed to parse structured data from content", error=str(e)
                    )
                    # Return response as-is if all parsing fails
                    return response

            return response

        except Exception as e:
            self._logger.error(
                "Constrained generation failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
