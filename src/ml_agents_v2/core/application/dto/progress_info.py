"""Progress tracking DTO for application layer."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ProgressInfo:
    """Data transfer object for evaluation progress tracking.

    Used for real-time progress updates during evaluation execution
    without exposing internal evaluation state.
    """

    evaluation_id: uuid.UUID
    current_question: int
    total_questions: int
    successful_answers: int
    failed_questions: int
    started_at: datetime
    last_updated: datetime
    estimated_completion: datetime | None = None
    current_question_text: str | None = None

    @property
    def completion_percentage(self) -> float:
        """Get completion percentage (0-100)."""
        if self.total_questions == 0:
            return 0.0
        return (self.current_question / self.total_questions) * 100

    @property
    def success_rate(self) -> float:
        """Get current success rate percentage."""
        if self.current_question == 0:
            return 0.0
        return (self.successful_answers / self.current_question) * 100

    @property
    def elapsed_minutes(self) -> float:
        """Get elapsed time in minutes."""
        return (self.last_updated - self.started_at).total_seconds() / 60

    @property
    def questions_per_minute(self) -> float:
        """Get processing rate in questions per minute."""
        elapsed = self.elapsed_minutes
        if elapsed == 0:
            return 0.0
        return self.current_question / elapsed

    @property
    def estimated_remaining_minutes(self) -> float | None:
        """Get estimated remaining time in minutes."""
        if self.questions_per_minute == 0:
            return None
        remaining_questions = self.total_questions - self.current_question
        return remaining_questions / self.questions_per_minute

    @property
    def progress_summary(self) -> str:
        """Get formatted progress summary."""
        return (
            f"{self.current_question}/{self.total_questions} "
            f"({self.completion_percentage:.1f}%) - "
            f"{self.successful_answers} correct"
        )
