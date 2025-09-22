"""Evaluation summary DTO for application layer."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class EvaluationSummary:
    """Data transfer object for detailed evaluation results summary.

    Used for displaying comprehensive evaluation results and analysis
    without exposing the full domain entity structure.
    """

    evaluation_id: uuid.UUID
    agent_type: str
    model_name: str
    benchmark_name: str
    status: str
    total_questions: int
    correct_answers: int
    accuracy: float
    execution_time_minutes: float
    total_tokens: int | None
    average_time_per_question: float
    error_count: int
    created_at: datetime
    completed_at: datetime | None

    @property
    def accuracy_percentage(self) -> str:
        """Get formatted accuracy percentage."""
        return f"{self.accuracy:.1f}%"

    @property
    def success_rate_display(self) -> str:
        """Get formatted success rate."""
        return f"{self.correct_answers}/{self.total_questions} correct"

    @property
    def performance_summary(self) -> str:
        """Get formatted performance summary."""
        return (
            f"Accuracy: {self.accuracy_percentage}, "
            f"Time: {self.execution_time_minutes:.1f}m, "
            f"Errors: {self.error_count}"
        )

    @property
    def token_usage_display(self) -> str:
        """Get formatted token usage."""
        if self.total_tokens is None:
            return "Token usage not available"
        return f"{self.total_tokens:,} tokens"
