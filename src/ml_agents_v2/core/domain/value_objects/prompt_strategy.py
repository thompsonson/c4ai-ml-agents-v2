"""PromptStrategy value objects for reasoning approaches."""

from __future__ import annotations

from dataclasses import dataclass

from .agent_config import AgentConfig
from .question import Question
from .validation_result import ValidationResult


@dataclass(frozen=True)
class PromptStrategy:
    """Domain value object defining prompt engineering strategy."""

    system_prompt: str
    user_prompt_template: str

    def build_prompt(self, question: Question) -> str:
        """Apply reasoning-specific prompt engineering rules."""
        return self.user_prompt_template.format(question_text=question.text)

    def validate_requirements(self, config: AgentConfig) -> ValidationResult:
        """Validate configuration supports this strategy."""
        errors: list[str] = []
        warnings: list[str] = []

        # Basic validation - subclasses can override for specific requirements
        if not config.model_name:
            errors.append("Model name is required")

        return ValidationResult(
            is_valid=len(errors) == 0, errors=errors, warnings=warnings
        )


# Strategy implementations following documentation patterns
NONE_STRATEGY = PromptStrategy(
    system_prompt=(
        "You are a helpful assistant that provides direct, concise answers."
    ),
    user_prompt_template=(
        "Answer the following question directly:\n\n" "Question: {question_text}"
    ),
)

CHAIN_OF_THOUGHT_STRATEGY = PromptStrategy(
    system_prompt="You are a helpful assistant that thinks step by step.",
    user_prompt_template=(
        "Think through this question step by step, then provide your answer:\n\n"
        "Question: {question_text}"
    ),
)
