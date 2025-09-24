"""None agent service - direct prompting without reasoning steps."""

from typing import Any

from ...value_objects.agent_config import AgentConfig
from ...value_objects.prompt_strategy import NONE_STRATEGY, PromptStrategy
from ...value_objects.question import Question
from ...value_objects.reasoning_result import ReasoningResult
from ...value_objects.validation_result import ValidationResult
from .reasoning_agent_service import ReasoningAgentService


class NoneAgentService(ReasoningAgentService):
    """Domain service for direct prompting approach."""

    def get_prompt_strategy(self) -> PromptStrategy:
        """Business rule: Direct prompting without reasoning scaffolding."""
        return NONE_STRATEGY

    def process_question(self, question: Question, config: AgentConfig) -> str:
        """Generate prompt using domain strategy."""
        strategy = self.get_prompt_strategy()
        return strategy.build_prompt(question)

    def process_response(
        self, raw_response: str, context: dict[str, Any]
    ) -> ReasoningResult:
        """Business rule: Extract direct answer, no reasoning trace."""
        cleaned_answer = self._clean_answer(raw_response)
        return ReasoningResult(
            final_answer=cleaned_answer,
            reasoning_text="",  # No reasoning for direct approach
            execution_metadata=context,
        )

    def _clean_answer(self, response: str) -> str:
        """Domain logic for answer extraction and cleaning."""
        # Remove common prefixes/suffixes
        answer = response.strip()
        prefixes = ["Answer:", "The answer is:", "Final answer:"]
        for prefix in prefixes:
            if answer.startswith(prefix):
                answer = answer[len(prefix) :].strip()
        return answer

    def validate_config(self, config: AgentConfig) -> ValidationResult:
        """Validate None agent configuration rules."""
        errors = []
        if config.agent_type != "none":
            errors.append("Agent type must be 'none' for None agent")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=[])

    def get_agent_type(self) -> str:
        """Return unique identifier for this reasoning approach."""
        return "none"
