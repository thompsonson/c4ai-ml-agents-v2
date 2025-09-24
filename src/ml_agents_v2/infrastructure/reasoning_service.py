"""Infrastructure service for executing domain reasoning strategies."""

import time
from typing import Any

from openai import AsyncOpenAI

from ..core.domain.services.reasoning.reasoning_agent_service import (
    ReasoningAgentService,
)
from ..core.domain.value_objects.agent_config import AgentConfig
from ..core.domain.value_objects.answer import Answer
from ..core.domain.value_objects.failure_reason import FailureReason
from ..core.domain.value_objects.question import Question
from .openrouter.error_mapper import OpenRouterErrorMapper
from .structured_output.parsing_factory import OutputParserFactory


class ReasoningInfrastructureService:
    """Infrastructure service executing domain reasoning strategies."""

    def __init__(
        self, openrouter_client: AsyncOpenAI, error_mapper: OpenRouterErrorMapper
    ):
        self.openrouter_client = openrouter_client
        self.error_mapper = error_mapper
        self.parser_factory = OutputParserFactory(openrouter_client)

    async def execute_reasoning(
        self,
        domain_service: ReasoningAgentService,
        question: Question,
        config: AgentConfig,
    ) -> Answer | FailureReason:
        """Execute domain reasoning strategy with structured output parsing."""
        try:
            # Domain: Get prompt strategy and generate prompt
            prompt = domain_service.process_question(question, config)

            # Infrastructure: Get model-specific parser and output model
            parser = self.parser_factory.create_parser(config.model_name)
            output_model = self.parser_factory.get_output_model(
                domain_service.get_agent_type()
            )

            # Infrastructure: Parse with structured output
            start_time = time.time()
            parse_result = await parser.parse(output_model, prompt, config)
            execution_time = time.time() - start_time

            # Domain: Process structured data into domain result
            processing_metadata = {
                "execution_time": execution_time,
                "token_usage": parse_result.get("token_usage"),
            }

            # Convert pydantic output to string for domain processing
            raw_response = str(parse_result["parsed_data"].answer)

            reasoning_result = domain_service.process_response(
                raw_response, processing_metadata
            )

            # Infrastructure: Convert to Answer value object
            return self._convert_to_answer(reasoning_result, execution_time)

        except Exception as e:
            # Infrastructure: Map external errors to domain failures
            return self.error_mapper.map_to_failure_reason(e)

    def _convert_to_domain_format(self, pydantic_output: Any) -> dict[str, Any]:
        """Convert infrastructure Pydantic model to domain-compatible format."""
        return {
            "final_answer": pydantic_output.answer,
            "reasoning_text": getattr(pydantic_output, "reasoning", ""),
        }

    def _convert_to_answer(
        self, reasoning_result: Any, execution_time: float
    ) -> Answer:
        """Convert domain result to Answer value object."""
        return Answer(
            extracted_answer=reasoning_result.get_answer(),
            reasoning_trace=reasoning_result.get_reasoning_trace(),
            confidence=None,  # Not available with current parsing strategy
            execution_time=execution_time,
            token_usage=reasoning_result.execution_metadata.get("token_usage"),
            raw_response=str(reasoning_result.final_answer),
        )
