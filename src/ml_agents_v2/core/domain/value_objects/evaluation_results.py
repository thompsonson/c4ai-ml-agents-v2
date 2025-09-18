"""EvaluationResults value object."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class QuestionResult:
    """Per-question evaluation outcome.

    Contains the question, expected and actual answers, and correctness assessment.
    Used for detailed analysis of evaluation performance.
    """

    question_id: str
    question_text: str
    expected_answer: str
    actual_answer: str
    is_correct: bool

    def __post_init__(self) -> None:
        """Validate QuestionResult attributes after construction."""
        if not self.question_id or not self.question_id.strip():
            raise ValueError("Question ID cannot be empty")

        if not self.question_text or not self.question_text.strip():
            raise ValueError("Question text cannot be empty")


@dataclass(frozen=True)
class EvaluationResults:
    """Complete evaluation outcomes and metrics.

    Contains aggregate performance metrics along with detailed per-question results
    for comprehensive analysis of reasoning agent performance.
    """

    total_questions: int
    correct_answers: int
    accuracy: float
    average_execution_time: float
    total_tokens: int
    error_count: int
    detailed_results: list[QuestionResult]
    summary_statistics: dict[str, Any]

    def __post_init__(self) -> None:
        """Validate EvaluationResults attributes after construction."""
        if self.total_questions < 0:
            raise ValueError("Total questions cannot be negative")

        if self.correct_answers < 0:
            raise ValueError("Correct answers cannot be negative")

        if self.error_count < 0:
            raise ValueError("Error count cannot be negative")

        if self.total_tokens < 0:
            raise ValueError("Total tokens cannot be negative")

        if self.average_execution_time < 0:
            raise ValueError("Average execution time cannot be negative")

        if not (0 <= self.accuracy <= 100):
            raise ValueError("Accuracy must be between 0 and 100")

        if self.correct_answers > self.total_questions:
            raise ValueError("Correct answers cannot exceed total questions")

        if len(self.detailed_results) != self.total_questions:
            raise ValueError(
                f"Detailed results count ({len(self.detailed_results)}) "
                f"must match total questions ({self.total_questions})"
            )

    def calculate_accuracy(self) -> float:
        """Compute accuracy percentage from correct answers and total questions."""
        if self.total_questions == 0:
            return 0.0
        return (self.correct_answers / self.total_questions) * 100.0

    def get_performance_summary(self) -> dict[str, Any]:
        """Return summary statistics for performance analysis."""
        return {
            "accuracy": self.accuracy,
            "total_questions": self.total_questions,
            "correct_answers": self.correct_answers,
            "error_count": self.error_count,
            "average_execution_time": self.average_execution_time,
            "total_tokens": self.total_tokens,
            "tokens_per_question": (
                self.total_tokens / self.total_questions
                if self.total_questions > 0
                else 0
            ),
            "success_rate": (
                (self.total_questions - self.error_count) / self.total_questions
                if self.total_questions > 0
                else 0
            ),
        }

    def export_detailed_csv(self) -> str:
        """Export detailed per-question results as CSV format string."""
        output = io.StringIO()
        writer = csv.writer(output)

        # Write CSV header
        writer.writerow(
            [
                "question_id",
                "question_text",
                "expected_answer",
                "actual_answer",
                "is_correct",
            ]
        )

        # Write detailed results
        for result in self.detailed_results:
            writer.writerow(
                [
                    result.question_id,
                    result.question_text,
                    result.expected_answer,
                    result.actual_answer,
                    result.is_correct,
                ]
            )

        return output.getvalue()
