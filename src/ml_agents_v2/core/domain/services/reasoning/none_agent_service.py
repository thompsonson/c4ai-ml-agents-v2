"""None reasoning agent service - provides direct responses without reasoning."""

from __future__ import annotations

import time

from ...value_objects.agent_config import AgentConfig
from ...value_objects.answer import Answer, TokenUsage
from ...value_objects.question import Question
from ...value_objects.reasoning_trace import ReasoningTrace
from .exceptions import InvalidConfigurationError, QuestionProcessingError
from .reasoning_agent_service import ReasoningAgentService


class NoneAgentService(ReasoningAgentService):
    """Reasoning agent that provides direct answers without explicit reasoning.

    This agent simulates a basic question-answering system that doesn't
    show its reasoning process. It returns simple answers with minimal
    token usage tracking.
    """

    def __init__(self) -> None:
        """Initialize the None reasoning agent service."""
        self._supported_providers = ["openai", "anthropic", "mock"]

    async def answer_question(
        self, question: Question, agent_config: AgentConfig
    ) -> Answer:
        """Answer a question without explicit reasoning.

        Args:
            question: Question to answer
            agent_config: Configuration for the reasoning agent

        Returns:
            Answer with no reasoning trace and simulated response

        Raises:
            InvalidConfigurationError: If agent config is invalid
            QuestionProcessingError: If question processing fails
        """
        if not self.validate_config(agent_config):
            raise InvalidConfigurationError(
                "Configuration validation failed", agent_config.agent_type
            )

        start_time = time.time()

        try:
            # Simulate processing the question
            # In a real implementation, this would call the actual model provider
            extracted_answer = self._simulate_answer(question, agent_config)

            execution_time = time.time() - start_time

            # Create empty reasoning trace for "none" approach
            reasoning_trace = ReasoningTrace(
                approach_type="none", reasoning_text="", metadata={}
            )

            # Simulate token usage
            prompt_tokens = len(question.text.split()) + 10  # Rough estimate
            completion_tokens = len(extracted_answer.split()) + 5
            token_usage = TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            )

            # Simulate raw response
            raw_response = f"Direct answer: {extracted_answer}"

            return Answer(
                extracted_answer=extracted_answer,
                reasoning_trace=reasoning_trace,
                confidence=None,  # None agent doesn't provide confidence
                execution_time=execution_time,
                token_usage=token_usage,
                raw_response=raw_response,
            )

        except Exception as e:
            raise QuestionProcessingError(
                question.id, "answer_generation", str(e)
            ) from e

    def supports_agent_type(self, agent_type: str) -> bool:
        """Check if this service supports the given agent type.

        Args:
            agent_type: Agent type to check

        Returns:
            True if agent type is "none", False otherwise
        """
        return agent_type == "none"

    def get_supported_model_providers(self) -> list[str]:
        """Get list of supported model providers.

        Returns:
            List of supported provider names
        """
        return self._supported_providers.copy()

    def validate_config(self, agent_config: AgentConfig) -> bool:
        """Validate that the agent configuration is compatible with this service.

        Args:
            agent_config: Configuration to validate

        Returns:
            True if configuration is valid, False otherwise
        """
        # Check agent type
        if agent_config.agent_type != "none":
            return False

        # Check model provider is supported
        if agent_config.model_provider not in self._supported_providers:
            return False

        # For None agent, we don't need special agent parameters
        return True

    def _simulate_answer(self, question: Question, agent_config: AgentConfig) -> str:
        """Simulate generating an answer to the question.

        Args:
            question: Question to answer
            agent_config: Agent configuration

        Returns:
            Simulated answer text
        """
        # This is a simple simulation for testing purposes
        # In a real implementation, this would call the model provider API
        if "2+2" in question.text or "2 + 2" in question.text:
            return "4"
        elif "capital" in question.text.lower() and "france" in question.text.lower():
            return "Paris"
        elif "what" in question.text.lower():
            return "I don't have enough information to answer this question."
        else:
            return "This is a simulated response from the none agent."
