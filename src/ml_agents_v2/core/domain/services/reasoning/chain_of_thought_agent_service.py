"""Chain of Thought reasoning agent service - provides step-by-step reasoning."""

from __future__ import annotations

import time

from ...value_objects.agent_config import AgentConfig
from ...value_objects.answer import Answer, TokenUsage
from ...value_objects.question import Question
from ...value_objects.reasoning_trace import ReasoningTrace
from .exceptions import InvalidConfigurationError, QuestionProcessingError
from .reasoning_agent_service import ReasoningAgentService


class ChainOfThoughtAgentService(ReasoningAgentService):
    """Reasoning agent that provides answers with explicit step-by-step reasoning.

    This agent simulates a chain-of-thought reasoning process, showing
    the step-by-step thinking that leads to the final answer.
    """

    def __init__(self) -> None:
        """Initialize the Chain of Thought reasoning agent service."""
        self._supported_providers = ["openai", "anthropic", "mock"]

    async def answer_question(
        self, question: Question, agent_config: AgentConfig
    ) -> Answer:
        """Answer a question with explicit chain-of-thought reasoning.

        Args:
            question: Question to answer
            agent_config: Configuration for the reasoning agent

        Returns:
            Answer with detailed reasoning trace and confidence score

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
            # Simulate processing the question with reasoning
            reasoning_text, extracted_answer, confidence = self._simulate_reasoning(
                question, agent_config
            )

            execution_time = time.time() - start_time

            # Create reasoning trace for chain-of-thought approach
            reasoning_trace = ReasoningTrace(
                approach_type="chain_of_thought",
                reasoning_text=reasoning_text,
                metadata={
                    "steps": len(reasoning_text.split("Step")),
                    "reasoning_length": len(reasoning_text),
                },
            )

            # Simulate higher token usage due to reasoning
            base_tokens = len(question.text.split()) + 20
            reasoning_tokens = len(reasoning_text.split()) + 10
            completion_tokens = len(extracted_answer.split()) + reasoning_tokens
            prompt_tokens = base_tokens + 30  # Additional tokens for CoT prompting

            token_usage = TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            )

            # Simulate raw response with reasoning
            raw_response = f"Reasoning: {reasoning_text}\n\nAnswer: {extracted_answer}"

            return Answer(
                extracted_answer=extracted_answer,
                reasoning_trace=reasoning_trace,
                confidence=confidence,
                execution_time=execution_time,
                token_usage=token_usage,
                raw_response=raw_response,
            )

        except Exception as e:
            raise QuestionProcessingError(
                question.id, "reasoning_generation", str(e)
            ) from e

    def supports_agent_type(self, agent_type: str) -> bool:
        """Check if this service supports the given agent type.

        Args:
            agent_type: Agent type to check

        Returns:
            True if agent type is "chain_of_thought", False otherwise
        """
        return agent_type == "chain_of_thought"

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
        if agent_config.agent_type != "chain_of_thought":
            return False

        # Check model provider is supported
        if agent_config.model_provider not in self._supported_providers:
            return False

        # Chain of thought requires certain model parameters
        if "temperature" in agent_config.model_parameters:
            temp = agent_config.model_parameters["temperature"]
            if not isinstance(temp, (int, float)) or temp < 0 or temp > 2:
                return False

        return True

    def _simulate_reasoning(
        self, question: Question, agent_config: AgentConfig
    ) -> tuple[str, str, float]:
        """Simulate generating reasoning and answer for the question.

        Args:
            question: Question to answer
            agent_config: Agent configuration

        Returns:
            Tuple of (reasoning_text, extracted_answer, confidence_score)
        """
        # This is a simulation for testing purposes
        # In a real implementation, this would call the model provider API with CoT prompting

        if "2+2" in question.text or "2 + 2" in question.text:
            reasoning = (
                "Step 1: I need to solve the arithmetic problem 2 + 2.\n"
                "Step 2: Addition of 2 + 2 means combining two groups of 2.\n"
                "Step 3: 2 + 2 = 4."
            )
            return reasoning, "4", 0.95

        elif "capital" in question.text.lower() and "france" in question.text.lower():
            reasoning = (
                "Step 1: The question asks about the capital of France.\n"
                "Step 2: France is a country in Europe.\n"
                "Step 3: The capital city of France is Paris.\n"
                "Step 4: Paris is both the largest city and the political center of France."
            )
            return reasoning, "Paris", 0.98

        elif "what" in question.text.lower():
            reasoning = (
                "Step 1: This is a 'what' question asking for information.\n"
                "Step 2: I need to analyze the context to understand what is being asked.\n"
                "Step 3: Without sufficient context, I cannot provide a specific answer.\n"
                "Step 4: I should acknowledge the limitation and ask for clarification."
            )
            return reasoning, "I need more context to answer this question.", 0.60

        else:
            reasoning = (
                "Step 1: I'm analyzing this question to understand what is being asked.\n"
                "Step 2: The question appears to be general and may require contextual knowledge.\n"
                "Step 3: I'll provide a helpful response acknowledging the chain-of-thought process."
            )
            return (
                reasoning,
                "This is a simulated chain-of-thought response.",
                0.75,
            )
