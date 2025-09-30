"""Output parsing factory working with domain LLMClient interface.

This module provides parsers that work with the LLMClient domain interface.
All type normalization is handled by the Anti-Corruption Layer (OpenRouterClient).
Parsers receive clean domain types and focus purely on structured output parsing.
"""

from typing import Any

from ...core.domain.services.llm_client import LLMClient
from ...core.domain.value_objects.agent_config import AgentConfig
from .model_capabilities import ModelCapabilitiesRegistry
from .models import BaseReasoningOutput, ChainOfThoughtOutput, DirectAnswerOutput


class StructuredLogProbsParser:
    """Use structured-logprobs for models supporting logprobs.

    Works with LLMClient domain interface - receives clean domain types
    from Anti-Corruption Layer. No type normalization needed.
    """

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def _pydantic_to_json_schema(
        self, model: type[BaseReasoningOutput]
    ) -> dict[str, Any]:
        """Convert Pydantic model to OpenAI structured output format."""
        schema = model.model_json_schema()
        return {
            "type": "json_schema",
            "json_schema": {
                "name": model.__name__.lower(),
                "description": model.__doc__ or f"Schema for {model.__name__}",
                "schema": schema,
                "strict": True,
            },
        }

    async def parse(
        self, model: type[BaseReasoningOutput], prompt: str, config: AgentConfig
    ) -> dict[str, Any]:
        """Parse using OpenAI structured output with logprobs processing.

        Receives clean domain types from LLMClient. No normalization needed.
        """
        json_schema = self._pydantic_to_json_schema(model)

        # Call through domain interface - gets clean ParsedResponse
        parsed_response = await self.llm_client.chat_completion(
            model=config.model_name,
            messages=[{"role": "user", "content": prompt}],
            response_format=json_schema,
            logprobs=True,
            **config.model_parameters,
        )

        # Validate structured data if present
        if parsed_response.has_structured_data():
            parsed_data = model.model_validate(parsed_response.structured_data)
            confidence_scores = None  # TODO: Extract from ParsedResponse if needed
        else:
            # Fallback to content parsing
            parsed_data = model.model_validate_json(parsed_response.content)
            confidence_scores = None

        return {
            "parsed_data": parsed_data,
            "confidence_scores": confidence_scores,
        }


class InstructorParser:
    """Use instructor for models without logprobs support.

    Works with LLMClient domain interface - receives clean domain types
    from Anti-Corruption Layer. No type normalization needed.
    """

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    async def parse(
        self, model: type[BaseReasoningOutput], prompt: str, config: AgentConfig
    ) -> dict[str, Any]:
        """Parse using instructor approach through domain interface.

        Note: This is a simplified implementation. Full instructor integration
        would require additional adapter layer to use instructor with LLMClient.
        """
        # Call through domain interface - gets clean ParsedResponse
        parsed_response = await self.llm_client.chat_completion(
            model=config.model_name,
            messages=[{"role": "user", "content": prompt}],
            **config.model_parameters,
        )

        # Parse content as JSON and validate with Pydantic model
        try:
            parsed_data = model.model_validate_json(parsed_response.content)
        except Exception:
            # Fallback: create model with just the content
            # This assumes the model has an 'answer' field
            parsed_data = model(answer=parsed_response.content)

        return {
            "parsed_data": parsed_data,
            "confidence_scores": None,  # Not available with instructor
        }


class OutputParserFactory:
    """Factory for creating appropriate parser based on model capabilities.

    Works with LLMClient domain interface. Parsers receive clean domain types
    from Anti-Corruption Layer.
    """

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def create_parser(
        self, model_name: str
    ) -> StructuredLogProbsParser | InstructorParser:
        """Create parser based on model capabilities."""
        if ModelCapabilitiesRegistry.supports_logprobs(model_name):
            return StructuredLogProbsParser(self.llm_client)
        else:
            return InstructorParser(self.llm_client)

    def get_output_model(self, agent_type: str) -> type[BaseReasoningOutput]:
        """Map domain agent type to infrastructure output model."""
        mapping: dict[str, type[BaseReasoningOutput]] = {
            "none": DirectAnswerOutput,
            "chain_of_thought": ChainOfThoughtOutput,
        }
        return mapping.get(agent_type, DirectAnswerOutput)
