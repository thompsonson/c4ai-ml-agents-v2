"""Answer value object."""

from __future__ import annotations

from dataclasses import dataclass

from .reasoning_trace import ReasoningTrace


@dataclass(frozen=True)
class TokenUsage:
    """LLM token consumption metrics.

    Tracks the number of tokens used in the request and response
    for cost analysis and performance monitoring.
    """

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

    def __post_init__(self) -> None:
        """Validate TokenUsage attributes after construction."""
        if (
            self.prompt_tokens < 0
            or self.completion_tokens < 0
            or self.total_tokens < 0
        ):
            raise ValueError("Token counts cannot be negative")

        if self.total_tokens != self.prompt_tokens + self.completion_tokens:
            raise ValueError(
                f"total_tokens ({self.total_tokens}) must equal "
                f"prompt_tokens + completion_tokens ({self.prompt_tokens + self.completion_tokens})"
            )


@dataclass(frozen=True)
class Answer:
    """Response from reasoning agent with trace information.

    Contains the final answer extracted from the model response along with
    metadata about the reasoning process, performance, and token usage.
    """

    extracted_answer: str
    reasoning_trace: ReasoningTrace
    confidence: float | None
    execution_time: float
    token_usage: TokenUsage
    raw_response: str

    def __post_init__(self) -> None:
        """Validate Answer attributes after construction."""
        if not self.extracted_answer or not self.extracted_answer.strip():
            raise ValueError("Extracted answer cannot be empty")

        if self.execution_time < 0:
            raise ValueError("Execution time cannot be negative")

        if self.confidence is not None and (self.confidence < 0 or self.confidence > 1):
            raise ValueError("Confidence must be between 0 and 1")

        if not self.raw_response or not self.raw_response.strip():
            raise ValueError("Raw response cannot be empty")

    def has_confidence(self) -> bool:
        """Return whether this answer has a confidence score."""
        return self.confidence is not None
