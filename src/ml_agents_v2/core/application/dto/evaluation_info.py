"""Evaluation information DTO for application layer."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class EvaluationInfo:
    """Data transfer object for evaluation summary information.

    Used for displaying evaluation lists and basic information without
    exposing the full domain entity structure.
    """

    evaluation_id: uuid.UUID
    agent_type: str
    model_name: str
    benchmark_name: str
    status: str
    accuracy: float | None
    created_at: datetime
    completed_at: datetime | None
    total_questions: int | None
    correct_answers: int | None

    @property
    def is_completed(self) -> bool:
        """Check if evaluation is completed successfully."""
        return self.status == "completed"

    @property
    def is_failed(self) -> bool:
        """Check if evaluation failed."""
        return self.status == "failed"

    @property
    def is_running(self) -> bool:
        """Check if evaluation is currently running."""
        return self.status == "running"

    @property
    def accuracy_percentage(self) -> str:
        """Get formatted accuracy percentage."""
        if self.accuracy is None:
            return "-"
        return f"{self.accuracy:.1f}%"

    @property
    def duration_minutes(self) -> float | None:
        """Get evaluation duration in minutes."""
        if self.completed_at is None:
            return None
        return (self.completed_at - self.created_at).total_seconds() / 60
