"""Chain of Thought agent service - step-by-step reasoning approach."""

from typing import Any

from ...value_objects.agent_config import AgentConfig
from ...value_objects.prompt_strategy import CHAIN_OF_THOUGHT_STRATEGY, PromptStrategy
from ...value_objects.question import Question
from ...value_objects.reasoning_result import ReasoningResult
from ...value_objects.validation_result import ValidationResult
from .reasoning_agent_service import ReasoningAgentService


class ChainOfThoughtAgentService(ReasoningAgentService):
    """Domain service for Chain of Thought reasoning."""

    def get_prompt_strategy(self) -> PromptStrategy:
        """Business rule: Step-by-step reasoning strategy."""
        return CHAIN_OF_THOUGHT_STRATEGY

    def process_question(self, question: Question, config: AgentConfig) -> str:
        """Generate prompt using domain strategy."""
        strategy = self.get_prompt_strategy()
        return strategy.build_prompt(question)

    def process_response(
        self, raw_response: str, context: dict[str, Any]
    ) -> ReasoningResult:
        """Business rule: Separate reasoning from final answer."""
        reasoning, answer = self._parse_reasoning_response(raw_response)

        return ReasoningResult(
            final_answer=answer, reasoning_text=reasoning, execution_metadata=context
        )

    def _parse_reasoning_response(self, response: str) -> tuple[str, str]:
        """Domain logic for separating reasoning from answer."""
        # Look for answer indicators
        answer_markers = ["Final answer:", "Answer:", "Therefore:", "So the answer is:"]

        for marker in answer_markers:
            if marker in response:
                parts = response.split(marker, 1)
                reasoning = parts[0].strip()
                answer = parts[1].strip() if len(parts) > 1 else ""
                return reasoning, answer

        # Fallback: treat entire response as reasoning, extract last sentence as answer
        sentences = response.split(". ")
        if len(sentences) > 1:
            reasoning = ". ".join(sentences[:-1]) + "."
            answer = sentences[-1].strip()
        else:
            reasoning = response
            answer = response

        return reasoning, answer

    def validate_config(self, config: AgentConfig) -> ValidationResult:
        """Validate Chain of Thought configuration rules."""
        errors: list[str] = []
        warnings: list[str] = []

        if config.agent_type != "chain_of_thought":
            errors.append(
                "Agent type must be 'chain_of_thought' for Chain of Thought agent"
            )

        # Business rule: Sufficient tokens for reasoning
        max_tokens = config.model_parameters.get("max_tokens", 1000)
        if max_tokens < 200:
            errors.append(
                "Chain of Thought requires at least 200 max_tokens for reasoning steps"
            )

        return ValidationResult(
            is_valid=len(errors) == 0, errors=errors, warnings=warnings
        )

    def get_agent_type(self) -> str:
        """Return unique identifier for this reasoning approach."""
        return "chain_of_thought"
