"""Marvin-based parsing strategy that wraps any LLM client.

This parsing client uses Marvin for post-processing structured output extraction
from natural language responses. It can wrap any base LLM client.
"""

from typing import Any

import structlog
from pydantic import BaseModel

from ...core.domain.services.llm_client import LLMClient
from ...core.domain.value_objects.answer import ParsedResponse


class MarvinParsingClient(LLMClient):
    """Wraps any LLM client with Marvin post-processing for structured output.

    This client follows the Decorator pattern - it wraps a base LLM client
    and adds Marvin post-processing to extract structured data from natural
    language responses.
    """

    def __init__(self, base_client: LLMClient):
        """Initialize Marvin parser with base LLM client.

        Args:
            base_client: The base LLM client to wrap (OpenRouter, OpenAI, etc.)
        """
        self.base_client = base_client
        self._logger = structlog.get_logger(__name__)

        # Import Marvin only when needed
        try:
            import marvin

            self.marvin = marvin
        except ImportError as e:
            raise ImportError(
                "marvin package is required for Marvin parsing. "
                "Install it with: pip install marvin"
            ) from e

    def _get_schema_for_agent(self, agent_type: str | None) -> type[BaseModel]:
        """Map domain agent type to infrastructure Pydantic schema.

        This is infrastructure-only logic - domain never sees these types.

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

    async def chat_completion(
        self, model: str, messages: list[dict[str, str]], **kwargs: Any
    ) -> ParsedResponse:
        """Execute chat completion with Marvin post-processing.

        Args:
            model: Model identifier
            messages: List of message dicts
            **kwargs: Additional parameters, including _internal_agent_type

        Returns:
            ParsedResponse with structured_data extracted by Marvin

        Raises:
            Various exceptions if parsing fails
        """
        # Extract internal context (infrastructure-only parameter)
        agent_type = kwargs.pop("_internal_agent_type", None)

        # Step 1: Get natural language response from base client
        response = await self.base_client.chat_completion(model, messages, **kwargs)

        # Step 2: Use Marvin to extract structured data
        schema = self._get_schema_for_agent(agent_type)

        try:
            extracted: Any = await self.marvin.extract_async(
                response.content,
                target=schema,
                instructions="Extract the structured data from the response",
            )

            # Marvin can return a list or single object
            structured: BaseModel = (
                extracted[0] if isinstance(extracted, list) and extracted else extracted
            )

            structured_data = structured.model_dump()

            self._logger.debug(
                "Marvin successfully extracted structured data",
                agent_type=agent_type,
                has_data=structured_data is not None,
            )

            # Return with both original content and extracted structured data
            return ParsedResponse(
                content=response.content, structured_data=structured_data
            )

        except Exception as e:
            self._logger.error(
                "Marvin extraction failed",
                error=str(e),
                error_type=type(e).__name__,
                content_preview=response.content[:200] if response.content else None,
            )
            # Let exception propagate - no fallback
            raise
