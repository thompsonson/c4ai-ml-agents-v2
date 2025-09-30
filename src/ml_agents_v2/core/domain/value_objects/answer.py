"""Answer value object."""

from __future__ import annotations

from dataclasses import dataclass

from .reasoning_trace import ReasoningTrace


@dataclass(frozen=True)
class ParsedResponse:
    """Response from LLM client with standardized format.

    This value object represents the normalized response from any LLM provider,
    eliminating external API type variations at the infrastructure boundary.
    """

    content: str
    structured_data: dict | None = None

    def __post_init__(self) -> None:
        """Validate ParsedResponse attributes after construction."""
        if not self.content or not self.content.strip():
            raise ValueError("Response content cannot be empty")

    def has_structured_data(self) -> bool:
        """Check if response includes parsed structured output."""
        return self.structured_data is not None


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
