"""Native structured output parsing strategy.

This parsing client uses the provider's native structured output capabilities
(e.g., OpenAI's response_format parameter) to get structured data directly.
"""

from typing import Any

import structlog
from pydantic import BaseModel

from ...core.domain.services.llm_client import LLMClient
from ...core.domain.value_objects.answer import ParsedResponse


class NativeParsingClient(LLMClient):
    """Wraps LLM client to use provider's native structured output.

    This client adds response_format parameter for providers that support
    native structured output (OpenAI, some others). It follows the Decorator
    pattern - wrapping a base client and adding native structured output.
    """

    def __init__(self, base_client: LLMClient):
        """Initialize native parser with base LLM client.

        Args:
            base_client: The base LLM client to wrap (should support response_format)
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
        """Create OpenAI-style response_format from Pydantic model.

        Args:
            schema: Pydantic model class

        Returns:
            Dictionary with response_format for native structured output
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
        """Execute chat completion with native structured output.

        Args:
            model: Model identifier
            messages: List of message dicts
            **kwargs: Additional parameters, including _internal_agent_type

        Returns:
            ParsedResponse with structured_data from native parsing

        Raises:
            Various exceptions if parsing fails
        """
        # Extract internal context (infrastructure-only parameter)
        agent_type = kwargs.pop("_internal_agent_type", None)

        # Get schema and create response_format
        schema = self._get_schema_for_agent(agent_type)
        response_format = self._create_response_format(schema)

        # Add response_format and logprobs to kwargs
        kwargs["response_format"] = response_format
        kwargs["logprobs"] = True  # Enable for confidence scoring

        self._logger.debug(
            "Using native structured output",
            agent_type=agent_type,
            schema=schema.__name__,
        )

        # Call base client with response_format
        response = await self.base_client.chat_completion(model, messages, **kwargs)

        # Base client should have extracted structured_data via response_format
        if not response.has_structured_data():
            self._logger.warning(
                "Native structured output did not return structured_data",
                model=model,
                agent_type=agent_type,
            )

        return response
