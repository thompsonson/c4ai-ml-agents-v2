"""Infrastructure service for executing domain reasoning strategies."""

import time
from datetime import datetime
from typing import Any

from ..core.domain.services.llm_client import LLMClientFactory
from ..core.domain.services.reasoning.reasoning_agent_service import (
    ReasoningAgentService,
)
from ..core.domain.value_objects.agent_config import AgentConfig
from ..core.domain.value_objects.answer import Answer
from ..core.domain.value_objects.failure_reason import FailureReason
from ..core.domain.value_objects.question import Question
from .providers import OpenRouterErrorMapper
from .shared_exceptions import ParserException


class ReasoningInfrastructureService:
    """Infrastructure service executing domain reasoning strategies."""

    def __init__(
        self,
        llm_client_factory: LLMClientFactory,
        error_mapper: OpenRouterErrorMapper,
        parsing_strategy: str = "auto",
    ):
        self.llm_client_factory = llm_client_factory
        self.error_mapper = error_mapper
        self.parsing_strategy = parsing_strategy

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

            # Infrastructure: Create client for this specific model and provider (Phase 9)
            # Factory returns fully-wrapped client with parsing strategy applied
            llm_client = self.llm_client_factory.create_client(
                model_name=config.model_name,
                provider=config.model_provider,
                strategy=self.parsing_strategy,
            )

            # Infrastructure: Execute with structured output parsing
            start_time = time.time()
            response = await llm_client.chat_completion(
                model=f"{config.model_provider}/{config.model_name}",
                messages=[{"role": "user", "content": prompt}],
                _internal_agent_type=config.agent_type,  # For Marvin strategy
                **config.model_parameters,
            )
            execution_time = time.time() - start_time

            # Verify structured data was extracted
            if not response.has_structured_data():
                raise ParserException(
                    parser_type=self.parsing_strategy,
                    model=config.model_name,
                    provider=config.model_provider,
                    stage="structured_data_extraction",
                    content=response.content,
                    error=ValueError("Parser must return structured_data"),
                )

            # Extract answer from structured data
            structured_data = response.structured_data
            if isinstance(structured_data, dict) and "answer" in structured_data:
                raw_response = str(structured_data["answer"])
            else:
                raw_response = str(structured_data)

            # Domain: Process structured data into domain result
            processing_metadata = {
                "execution_time": execution_time,
            }

            reasoning_result = domain_service.process_response(
                raw_response, processing_metadata
            )

            # Infrastructure: Convert to Answer value object
            return self._convert_to_answer(reasoning_result, execution_time)

        except ParserException as e:
            # ACL Boundary - translate parser failures to domain type
            return self._translate_parser_exception(e)
        except Exception as e:
            # Infrastructure: Map external errors to domain failures
            return self.error_mapper.map_to_failure_reason(e)

    def _convert_to_answer(
        self, reasoning_result: Any, execution_time: float
    ) -> Answer:
        """Convert domain result to Answer value object."""
        return Answer(
            extracted_answer=reasoning_result.get_answer(),
            reasoning_trace=reasoning_result.get_reasoning_trace(),
            confidence=None,  # Not available with current parsing strategy
            execution_time=execution_time,
            raw_response=str(reasoning_result.final_answer),
        )

    def _translate_parser_exception(self, error: ParserException) -> FailureReason:
        """ACL boundary - map parser failures to domain FailureReason.

        Note: Uses string "parsing_error" not enum, per domain model implementation.
        """
        return FailureReason(
            category="parsing_error",  # String constant from VALID_FAILURE_CATEGORIES
            description=f"{error.parser_type} failed at {error.stage}",
            technical_details=(
                f"Parser: {error.parser_type}\n"
                f"Model: {error.model}\n"
                f"Provider: {error.provider}\n"
                f"Stage: {error.stage}\n"
                f"Original Error: {error.original_error}\n"
                f"Content: {error.get_truncated_content()}"
            ),
            occurred_at=datetime.now(),
            recoverable=False,
        )
