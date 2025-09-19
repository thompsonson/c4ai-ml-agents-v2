"""ReasoningAgentService interface for question-answering."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ...value_objects.agent_config import AgentConfig
from ...value_objects.answer import Answer
from ...value_objects.question import Question


class ReasoningAgentService(ABC):
    """Abstract interface for reasoning agents that answer questions.

    Reasoning agents process questions using different approaches (none, chain of thought)
    and return structured answers with reasoning traces, confidence scores, and metrics.
    """

    @abstractmethod
    async def answer_question(
        self, question: Question, agent_config: AgentConfig
    ) -> Answer:
        """Answer a question using the configured reasoning approach.

        Args:
            question: Question to answer
            agent_config: Configuration for the reasoning agent

        Returns:
            Answer with reasoning trace and confidence if available

        Raises:
            ReasoningAgentError: If question answering fails
            InvalidConfigurationError: If agent config is invalid for this service
        """

    @abstractmethod
    def supports_agent_type(self, agent_type: str) -> bool:
        """Check if this service supports the given agent type.

        Args:
            agent_type: Agent type to check (e.g., "none", "chain_of_thought")

        Returns:
            True if agent type is supported, False otherwise
        """

    @abstractmethod
    def get_supported_model_providers(self) -> list[str]:
        """Get list of supported model providers.

        Returns:
            List of supported provider names (e.g., ["openai", "anthropic"])
        """

    @abstractmethod
    def validate_config(self, agent_config: AgentConfig) -> bool:
        """Validate that the agent configuration is compatible with this service.

        Args:
            agent_config: Configuration to validate

        Returns:
            True if configuration is valid, False otherwise
        """
