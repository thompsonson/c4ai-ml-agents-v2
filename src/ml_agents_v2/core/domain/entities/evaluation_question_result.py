"""EvaluationQuestionResult entity."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from ..value_objects.reasoning_trace import ReasoningTrace

if TYPE_CHECKING:
    from ..value_objects.evaluation_results import QuestionResult


@dataclass(frozen=True)
class EvaluationQuestionResult:
    """Individual question-answer pair with complete processing details.

    Purpose: Represents a single question's evaluation result within an evaluation,
    enabling incremental persistence and graceful interruption handling.

    Identity: Composite key (evaluation_id, question_id)

    Business Rules:
    - Immutable once created (represents completed processing)
    - Must belong to existing evaluation
    - Question ID must be unique within evaluation
    - Processing time must be positive
    - Error message required if processing failed
    """

    id: uuid.UUID
    evaluation_id: uuid.UUID
    question_id: str
    question_text: str
    expected_answer: str
    actual_answer: str | None
    is_correct: bool | None
    execution_time: float
    reasoning_trace: ReasoningTrace | None
    error_message: str | None
    technical_details: str | None
    processed_at: datetime

    def __post_init__(self) -> None:
        """Validate EvaluationQuestionResult state after construction."""
        # Business rule: processing time must be positive
        if self.execution_time < 0:
            raise ValueError("Processing time must be positive")

        # Business rule: error message required if processing failed
        if self.actual_answer is None and self.error_message is None:
            raise ValueError("Error message required if processing failed")

        # Business rule: successful processing must have answer and correctness
        if self.actual_answer is not None and self.is_correct is None:
            raise ValueError("Successful processing must have correctness evaluation")

    def is_successful(self) -> bool:
        """Check if question was processed without errors.

        Returns:
            True if processing was successful, False otherwise
        """
        return self.error_message is None and self.actual_answer is not None

    def matches_expected(self) -> bool:
        """Verify answer correctness.

        Returns:
            True if answer matches expected result
        """
        return self.is_correct is True

    @classmethod
    def create_successful(
        cls,
        evaluation_id: uuid.UUID,
        question_id: str,
        question_text: str,
        expected_answer: str,
        actual_answer: str,
        is_correct: bool,
        execution_time: float,
        reasoning_trace: ReasoningTrace | None = None,
    ) -> EvaluationQuestionResult:
        """Factory method for successful question processing.

        Args:
            evaluation_id: Parent evaluation identifier
            question_id: Question identifier within benchmark
            question_text: Original question content
            expected_answer: Ground truth answer
            actual_answer: Agent's extracted answer
            is_correct: Correctness evaluation result
            execution_time: Processing duration in seconds
            reasoning_trace: Step-by-step reasoning documentation

        Returns:
            New EvaluationQuestionResult instance
        """
        return cls(
            id=uuid.uuid4(),
            evaluation_id=evaluation_id,
            question_id=question_id,
            question_text=question_text,
            expected_answer=expected_answer,
            actual_answer=actual_answer,
            is_correct=is_correct,
            execution_time=execution_time,
            reasoning_trace=reasoning_trace,
            error_message=None,
            technical_details=None,
            processed_at=datetime.now(),
        )

    @classmethod
    def create_failed(
        cls,
        evaluation_id: uuid.UUID,
        question_id: str,
        question_text: str,
        expected_answer: str,
        error_message: str,
        execution_time: float,
        technical_details: str | None = None,
    ) -> EvaluationQuestionResult:
        """Factory method for failed question processing.

        Args:
            evaluation_id: Parent evaluation identifier
            question_id: Question identifier within benchmark
            question_text: Original question content
            expected_answer: Ground truth answer
            error_message: Failure description
            execution_time: Processing duration in seconds
            technical_details: Raw technical error information for debugging

        Returns:
            New EvaluationQuestionResult instance
        """
        return cls(
            id=uuid.uuid4(),
            evaluation_id=evaluation_id,
            question_id=question_id,
            question_text=question_text,
            expected_answer=expected_answer,
            actual_answer=None,
            is_correct=None,
            execution_time=execution_time,
            reasoning_trace=None,
            error_message=error_message,
            technical_details=technical_details,
            processed_at=datetime.now(),
        )

    def to_question_result(self) -> QuestionResult:
        """Convert to legacy QuestionResult format for backward compatibility.

        Returns:
            QuestionResult value object
        """
        from ..value_objects.evaluation_results import QuestionResult

        return QuestionResult(
            question_id=self.question_id,
            question_text=self.question_text,
            expected_answer=self.expected_answer,
            actual_answer=self.actual_answer or "",
            is_correct=self.is_correct or False,
        )
