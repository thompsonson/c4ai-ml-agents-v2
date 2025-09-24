"""ReasoningAgentService interface for domain reasoning logic."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ...value_objects.agent_config import AgentConfig
from ...value_objects.prompt_strategy import PromptStrategy
from ...value_objects.question import Question
from ...value_objects.reasoning_result import ReasoningResult
from ...value_objects.validation_result import ValidationResult


class ReasoningAgentService(ABC):
    """Domain service implementing specific reasoning approach.

    Contains pure business logic for reasoning strategies including prompt
    engineering rules, response parsing patterns, and configuration validation.
    Infrastructure concerns (API calls, network handling) are handled
    separately.
    """

    @abstractmethod
    def get_prompt_strategy(self) -> PromptStrategy:
        """Return prompt engineering strategy for this approach."""

    @abstractmethod
    def process_question(self, question: Question, config: AgentConfig) -> str:
        """Generate prompt using domain strategy.

        Args:
            question: Question to process
            config: Agent configuration

        Returns:
            Formatted prompt string
        """

    @abstractmethod
    def process_response(
        self, raw_response: str, context: dict[str, Any]
    ) -> ReasoningResult:
        """Apply domain parsing rules to extract structured result.

        Args:
            raw_response: Raw response from LLM
            context: Execution context and metadata

        Returns:
            ReasoningResult with parsed answer and reasoning
        """

    @abstractmethod
    def validate_config(self, config: AgentConfig) -> ValidationResult:
        """Validate configuration against domain requirements.

        Args:
            config: Agent configuration to validate

        Returns:
            ValidationResult with any errors or warnings
        """

    @abstractmethod
    def get_agent_type(self) -> str:
        """Return unique identifier for this reasoning approach."""
