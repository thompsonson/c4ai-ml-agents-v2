"""Output parsing factory working with domain LLMClient interface.

This module provides parsers that work with the LLMClient domain interface.
All type normalization is handled by the Anti-Corruption Layer (OpenRouterClient).
Parsers receive clean domain types and focus purely on structured output parsing.
"""

import json
from typing import Any

from ...core.domain.services.llm_client import LLMClient
from ...core.domain.value_objects.agent_config import AgentConfig
from .exceptions import ParserException
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
            model=f"{config.model_provider}/{config.model_name}",
            messages=[{"role": "user", "content": prompt}],
            response_format=json_schema,
            logprobs=True,
            **config.model_parameters,
        )

        # Validate structured data if present
        if parsed_response.has_structured_data():
            try:
                parsed_data = model.model_validate(parsed_response.structured_data)
                confidence_scores = None  # TODO: Extract from ParsedResponse if needed
            except Exception as e:
                raise ParserException(
                    parser_type="StructuredLogProbsParser",
                    model=config.model_name,
                    provider=config.model_provider,
                    stage="schema_validation",
                    content=str(parsed_response.structured_data),
                    error=e,
                ) from e
        else:
            # Fallback to content parsing
            if not parsed_response.content or not parsed_response.content.strip():
                raise ParserException(
                    parser_type="StructuredLogProbsParser",
                    model=config.model_name,
                    provider=config.model_provider,
                    stage="response_empty",
                    content=parsed_response.content,
                    error=ValueError("Empty response content"),
                )

            try:
                parsed_data = model.model_validate_json(parsed_response.content)
                confidence_scores = None
            except Exception as e:
                raise ParserException(
                    parser_type="StructuredLogProbsParser",
                    model=config.model_name,
                    provider=config.model_provider,
                    stage="json_parse",
                    content=parsed_response.content,
                    error=e,
                ) from e

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

    def _add_json_schema_instructions(
        self, domain_prompt: str, output_model: type[BaseReasoningOutput]
    ) -> str:
        """Add JSON formatting requirements to domain prompt.

        Domain provides complete prompt using PromptStrategy (NONE_STRATEGY or CHAIN_OF_THOUGHT_STRATEGY).
        Infrastructure adds technical JSON schema formatting instructions.

        Uses model_json_schema() directly - single source of truth, no schema drift.
        """
        schema = output_model.model_json_schema()

        json_instructions = f"""

You must respond with valid JSON matching this exact schema:
{json.dumps(schema, indent=2)}

Do not include any text outside the JSON structure.
Your entire response must be valid JSON only.
"""
        return domain_prompt + json_instructions

    def _parse_json_response(
        self, content: str, provider: str, model_name: str
    ) -> dict[str, Any]:
        """Parse JSON response - raise ParserException on failure"""
        if not content or not content.strip():
            raise ParserException(
                parser_type="InstructorParser",
                model=model_name,
                provider=provider,
                stage="response_empty",
                content=content,
                error=ValueError("Empty response"),
            )

        try:
            parsed_content = json.loads(content)
            if not isinstance(parsed_content, dict):
                raise ValueError("Response content is not a JSON object")
            return parsed_content
        except json.JSONDecodeError as e:
            raise ParserException(
                parser_type="InstructorParser",
                model=model_name,
                provider=provider,
                stage="json_parse",
                content=content,
                error=e,
            ) from e

    def _validate_against_schema(
        self,
        data: dict[str, Any],
        model: type[BaseReasoningOutput],
        provider: str,
        model_name: str,
        content: str,
    ) -> BaseReasoningOutput:
        """Validate parsed data against Pydantic model"""
        try:
            return model.model_validate(data)
        except Exception as e:
            raise ParserException(
                parser_type="InstructorParser",
                model=model_name,
                provider=provider,
                stage="schema_validation",
                content=content,
                error=e,
            ) from e

    async def parse(
        self, model: type[BaseReasoningOutput], prompt: str, config: AgentConfig
    ) -> dict[str, Any]:
        """Parse using instructor approach with JSON schema instructions.

        Adds JSON schema formatting to domain prompt and validates response.
        No fallback logic - raises ParserException on any failure.
        """
        # Infrastructure: Add JSON schema instructions to domain prompt
        enhanced_prompt = self._add_json_schema_instructions(prompt, model)

        # Call through domain interface - gets clean ParsedResponse
        parsed_response = await self.llm_client.chat_completion(
            model=f"{config.model_provider}/{config.model_name}",
            messages=[{"role": "user", "content": enhanced_prompt}],
            **config.model_parameters,
        )

        # Infrastructure: Parse and validate with proper exception handling
        parsed_json = self._parse_json_response(
            parsed_response.content, config.model_provider, config.model_name
        )
        parsed_data = self._validate_against_schema(
            parsed_json,
            model,
            config.model_provider,
            config.model_name,
            parsed_response.content,
        )

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
