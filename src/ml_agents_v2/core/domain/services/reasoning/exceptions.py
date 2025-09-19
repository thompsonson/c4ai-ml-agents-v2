"""Reasoning agent service exceptions."""

from __future__ import annotations


class ReasoningAgentError(Exception):
    """Base exception for reasoning agent operations."""

    def __init__(self, message: str, cause: Exception | None = None) -> None:
        """Initialize reasoning agent error.

        Args:
            message: Error description
            cause: Optional underlying exception
        """
        super().__init__(message)
        self.cause = cause


class InvalidConfigurationError(ReasoningAgentError):
    """Exception raised when agent configuration is invalid."""

    def __init__(self, config_issue: str, agent_type: str) -> None:
        """Initialize invalid configuration error.

        Args:
            config_issue: Description of the configuration problem
            agent_type: Type of agent that has invalid config
        """
        super().__init__(f"Invalid configuration for {agent_type}: {config_issue}")
        self.config_issue = config_issue
        self.agent_type = agent_type


class ModelProviderError(ReasoningAgentError):
    """Exception raised when model provider interaction fails."""

    def __init__(self, provider: str, error_details: str) -> None:
        """Initialize model provider error.

        Args:
            provider: Name of the model provider
            error_details: Detailed error information
        """
        super().__init__(f"Model provider '{provider}' error: {error_details}")
        self.provider = provider
        self.error_details = error_details


class QuestionProcessingError(ReasoningAgentError):
    """Exception raised when question processing fails."""

    def __init__(self, question_id: str, processing_stage: str, details: str) -> None:
        """Initialize question processing error.

        Args:
            question_id: ID of the question that failed processing
            processing_stage: Stage where processing failed
            details: Detailed error information
        """
        super().__init__(
            f"Failed to process question '{question_id}' at {processing_stage}: {details}"
        )
        self.question_id = question_id
        self.processing_stage = processing_stage
        self.details = details


class TimeoutError(ReasoningAgentError):
    """Exception raised when reasoning operation times out."""

    def __init__(self, timeout_seconds: float) -> None:
        """Initialize timeout error.

        Args:
            timeout_seconds: Number of seconds before timeout occurred
        """
        super().__init__(
            f"Reasoning operation timed out after {timeout_seconds} seconds"
        )
        self.timeout_seconds = timeout_seconds
