"""Output parsing factory with dual parsing strategy support."""

from typing import Any

import instructor  # type: ignore
import structured_logprobs  # type: ignore
from openai import AsyncOpenAI

from ...core.domain.value_objects.agent_config import AgentConfig
from .model_capabilities import ModelCapabilitiesRegistry
from .models import BaseReasoningOutput, ChainOfThoughtOutput, DirectAnswerOutput


class StructuredLogProbsParser:
    """Use structured-logprobs for models supporting logprobs."""

    def __init__(self, openrouter_client: AsyncOpenAI):
        self.openrouter_client = openrouter_client

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
        """Parse using OpenAI structured output with logprobs processing."""
        json_schema = self._pydantic_to_json_schema(model)

        # Make structured output request with logprobs enabled
        response = await self.openrouter_client.chat.completions.create(
            model=config.model_name,
            messages=[{"role": "user", "content": prompt}],
            response_format=json_schema,  # type: ignore
            logprobs=True,
            **config.model_parameters,
        )

        # Process response with structured-logprobs for confidence scoring
        try:
            enhanced_response = structured_logprobs.add_logprobs(response)
            confidence_scores = enhanced_response.log_probs
        except (AttributeError, Exception):
            # Fallback if logprobs processing fails
            confidence_scores = getattr(response.choices[0], "logprobs", None)

        # Parse the structured JSON response
        parsed_json = response.choices[0].message.parsed
        if parsed_json:
            parsed_data = model.model_validate(parsed_json)
        else:
            # Fallback to content parsing if parsed field is not available
            content = response.choices[0].message.content

            parsed_data = model.model_validate_json(content)

        return {
            "parsed_data": parsed_data,
            "confidence_scores": confidence_scores,
            "token_usage": response.usage,
        }


class InstructorParser:
    """Use instructor for models without logprobs support."""

    def __init__(self, openrouter_client: AsyncOpenAI):
        self.client = instructor.from_openai(openrouter_client)

    async def parse(
        self, model: type[BaseReasoningOutput], prompt: str, config: AgentConfig
    ) -> dict[str, Any]:
        """Parse using instructor with Pydantic model directly."""
        response = await self.client.chat.completions.create(
            model=config.model_name,
            messages=[{"role": "user", "content": prompt}],
            response_model=model,
            **config.model_parameters,
        )

        return {
            "parsed_data": response,
            "confidence_scores": None,  # Not available with instructor
            "token_usage": getattr(response, "_raw_response", {}).get("usage"),
        }


class OutputParserFactory:
    """Factory for creating appropriate parser based on model capabilities."""

    def __init__(self, openrouter_client: AsyncOpenAI):
        self.openrouter_client = openrouter_client

    def create_parser(
        self, model_name: str
    ) -> StructuredLogProbsParser | InstructorParser:
        """Create parser based on model capabilities."""
        if ModelCapabilitiesRegistry.supports_logprobs(model_name):
            return StructuredLogProbsParser(self.openrouter_client)
        else:
            return InstructorParser(self.openrouter_client)

    def get_output_model(self, agent_type: str) -> type[BaseReasoningOutput]:
        """Map domain agent type to infrastructure output model."""
        mapping: dict[str, type[BaseReasoningOutput]] = {
            "none": DirectAnswerOutput,
            "chain_of_thought": ChainOfThoughtOutput,
        }
        return mapping.get(agent_type, DirectAnswerOutput)
