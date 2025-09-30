"""EvaluationQuestionResultRepository interface."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from ..entities.evaluation_question_result import EvaluationQuestionResult


class ProgressInfo:
    """Progress information for evaluation execution.

    Contains metrics about evaluation progress based on saved question results.
    """

    def __init__(
        self,
        evaluation_id: uuid.UUID,
        total_questions: int,
        completed_questions: int,
        successful_questions: int,
        failed_questions: int,
        latest_processed_at: str | None = None,
    ):
        self.evaluation_id = evaluation_id
        self.total_questions = total_questions
        self.completed_questions = completed_questions
        self.successful_questions = successful_questions
        self.failed_questions = failed_questions
        self.latest_processed_at = latest_processed_at

    @property
    def completion_percentage(self) -> float:
        """Calculate completion percentage."""
        if self.total_questions == 0:
            return 0.0
        return (self.completed_questions / self.total_questions) * 100.0

    @property
    def success_rate(self) -> float:
        """Calculate success rate of completed questions."""
        if self.completed_questions == 0:
            return 0.0
        return (self.successful_questions / self.completed_questions) * 100.0


class EvaluationQuestionResultRepository(ABC):
    """Repository interface for EvaluationQuestionResult entity persistence.

    Defines the contract for storing, retrieving, and managing individual
    question results within evaluations, enabling incremental persistence
    and graceful interruption handling.
    """

    @abstractmethod
    def save(self, question_result: EvaluationQuestionResult) -> None:
        """Persist a question result entity.

        Args:
            question_result: The question result to persist

        Raises:
            RepositoryError: If persistence fails
        """

    @abstractmethod
    def get_by_id(self, question_result_id: uuid.UUID) -> EvaluationQuestionResult:
        """Retrieve question result by ID.

        Args:
            question_result_id: Unique identifier of the question result

        Returns:
            EvaluationQuestionResult entity

        Raises:
            RepositoryError: If retrieval fails
            EntityNotFoundError: If question result doesn't exist
        """

    @abstractmethod
    def get_by_evaluation_id(
        self, evaluation_id: uuid.UUID
    ) -> list[EvaluationQuestionResult]:
        """Get all question results for an evaluation.

        Args:
            evaluation_id: Evaluation identifier

        Returns:
            List of question results for the evaluation

        Raises:
            RepositoryError: If retrieval fails
        """

    @abstractmethod
    def count_by_evaluation_id(self, evaluation_id: uuid.UUID) -> int:
        """Count question results for an evaluation.

        Args:
            evaluation_id: Evaluation identifier

        Returns:
            Number of question results for the evaluation

        Raises:
            RepositoryError: If count fails
        """

    @abstractmethod
    def get_progress(
        self, evaluation_id: uuid.UUID, total_questions: int
    ) -> ProgressInfo:
        """Get progress information for an evaluation.

        Args:
            evaluation_id: Evaluation identifier
            total_questions: Total number of questions in the benchmark

        Returns:
            Progress information with completion metrics

        Raises:
            RepositoryError: If retrieval fails
        """

    @abstractmethod
    def exists(self, evaluation_id: uuid.UUID, question_id: str) -> bool:
        """Check if a question result exists for the evaluation.

        Args:
            evaluation_id: Evaluation identifier
            question_id: Question identifier within benchmark

        Returns:
            True if question result exists, False otherwise

        Raises:
            RepositoryError: If check fails
        """

    @abstractmethod
    def delete_by_evaluation_id(self, evaluation_id: uuid.UUID) -> None:
        """Delete all question results for an evaluation.

        Args:
            evaluation_id: Evaluation identifier

        Raises:
            RepositoryError: If deletion fails
        """

    @abstractmethod
    def get_completed_question_ids(self, evaluation_id: uuid.UUID) -> list[str]:
        """Get list of question IDs that have been completed for an evaluation.

        Args:
            evaluation_id: Evaluation identifier

        Returns:
            List of question IDs that have been processed

        Raises:
            RepositoryError: If retrieval fails
        """

    @abstractmethod
    def get_next_question_index(self, evaluation_id: uuid.UUID) -> int:
        """Get the index of the next question to process.

        Args:
            evaluation_id: Evaluation identifier

        Returns:
            Zero-based index of next question to process

        Raises:
            RepositoryError: If retrieval fails
        """
