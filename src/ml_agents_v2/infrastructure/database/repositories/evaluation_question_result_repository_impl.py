"""SQLAlchemy implementation of EvaluationQuestionResultRepository."""

import uuid

from sqlalchemy import and_, func, select
from sqlalchemy.exc import SQLAlchemyError

from ml_agents_v2.core.domain.entities.evaluation_question_result import (
    EvaluationQuestionResult,
)
from ml_agents_v2.core.domain.repositories.evaluation_question_result_repository import (
    EvaluationQuestionResultRepository,
    ProgressInfo,
)
from ml_agents_v2.core.domain.repositories.exceptions import (
    EntityNotFoundError,
    RepositoryError,
)
from ml_agents_v2.infrastructure.database.models.evaluation_question_result import (
    EvaluationQuestionResultModel,
)
from ml_agents_v2.infrastructure.database.session_manager import DatabaseSessionManager


class EvaluationQuestionResultRepositoryImpl(EvaluationQuestionResultRepository):
    """SQLAlchemy implementation of EvaluationQuestionResultRepository interface.

    Provides concrete implementation of question result persistence using
    SQLAlchemy ORM with domain entity conversion and progress tracking.
    """

    def __init__(self, session_manager: DatabaseSessionManager):
        """Initialize repository with session manager.

        Args:
            session_manager: Database session manager for SQLAlchemy operations
        """
        self.session_manager = session_manager

    def save(self, question_result: EvaluationQuestionResult) -> None:
        """Save question result to database.

        Args:
            question_result: Domain question result entity to save

        Raises:
            RepositoryError: If database operation fails
        """
        try:
            result_model = EvaluationQuestionResultModel.from_domain(question_result)

            with self.session_manager.get_session() as session:
                session.add(result_model)
                # Session is automatically committed by context manager
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to save question result: {e}") from e

    def get_by_id(self, question_result_id: uuid.UUID) -> EvaluationQuestionResult:
        """Retrieve question result by ID.

        Args:
            question_result_id: Unique identifier of the question result

        Returns:
            EvaluationQuestionResult domain entity

        Raises:
            EntityNotFoundError: If question result not found
            RepositoryError: If database operation fails
        """
        try:
            with self.session_manager.get_session() as session:
                stmt = select(EvaluationQuestionResultModel).where(
                    EvaluationQuestionResultModel.id == question_result_id
                )
                result = session.execute(stmt).scalar_one_or_none()

                if result is None:
                    raise EntityNotFoundError(
                        "EvaluationQuestionResult", str(question_result_id)
                    )

                return result.to_domain()
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to retrieve question result: {e}") from e

    def get_by_evaluation_id(
        self, evaluation_id: uuid.UUID
    ) -> list[EvaluationQuestionResult]:
        """Get all question results for an evaluation.

        Args:
            evaluation_id: Evaluation identifier

        Returns:
            List of question results for the evaluation

        Raises:
            RepositoryError: If database operation fails
        """
        try:
            with self.session_manager.get_session() as session:
                stmt = (
                    select(EvaluationQuestionResultModel)
                    .where(EvaluationQuestionResultModel.evaluation_id == evaluation_id)
                    .order_by(EvaluationQuestionResultModel.processed_at)
                )
                results = session.execute(stmt).scalars().all()

                return [result.to_domain() for result in results]
        except SQLAlchemyError as e:
            raise RepositoryError(
                f"Failed to retrieve question results for evaluation: {e}"
            ) from e

    def count_by_evaluation_id(self, evaluation_id: uuid.UUID) -> int:
        """Count question results for an evaluation.

        Args:
            evaluation_id: Evaluation identifier

        Returns:
            Number of question results for the evaluation

        Raises:
            RepositoryError: If database operation fails
        """
        try:
            with self.session_manager.get_session() as session:
                stmt = select(func.count(EvaluationQuestionResultModel.id)).where(
                    EvaluationQuestionResultModel.evaluation_id == evaluation_id
                )
                result = session.execute(stmt).scalar()
                return result or 0
        except SQLAlchemyError as e:
            raise RepositoryError(
                f"Failed to count question results for evaluation: {e}"
            ) from e

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
            RepositoryError: If database operation fails
        """
        try:
            with self.session_manager.get_session() as session:
                # Count total completed questions
                total_stmt = select(func.count(EvaluationQuestionResultModel.id)).where(
                    EvaluationQuestionResultModel.evaluation_id == evaluation_id
                )
                completed_questions = session.execute(total_stmt).scalar() or 0

                # Count successful questions (no error message)
                success_stmt = select(
                    func.count(EvaluationQuestionResultModel.id)
                ).where(
                    and_(
                        EvaluationQuestionResultModel.evaluation_id == evaluation_id,
                        EvaluationQuestionResultModel.error_message.is_(None),
                    )
                )
                successful_questions = session.execute(success_stmt).scalar() or 0

                # Count failed questions (has error message)
                failed_stmt = select(
                    func.count(EvaluationQuestionResultModel.id)
                ).where(
                    and_(
                        EvaluationQuestionResultModel.evaluation_id == evaluation_id,
                        EvaluationQuestionResultModel.error_message.is_not(None),
                    )
                )
                failed_questions = session.execute(failed_stmt).scalar() or 0

                # Get latest processed timestamp
                latest_stmt = select(
                    func.max(EvaluationQuestionResultModel.processed_at)
                ).where(EvaluationQuestionResultModel.evaluation_id == evaluation_id)
                latest_processed = session.execute(latest_stmt).scalar()
                latest_processed_str = (
                    latest_processed.isoformat() if latest_processed else None
                )

                return ProgressInfo(
                    evaluation_id=evaluation_id,
                    total_questions=total_questions,
                    completed_questions=completed_questions,
                    successful_questions=successful_questions,
                    failed_questions=failed_questions,
                    latest_processed_at=latest_processed_str,
                )
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to get progress for evaluation: {e}") from e

    def exists(self, evaluation_id: uuid.UUID, question_id: str) -> bool:
        """Check if a question result exists for the evaluation.

        Args:
            evaluation_id: Evaluation identifier
            question_id: Question identifier within benchmark

        Returns:
            True if question result exists, False otherwise

        Raises:
            RepositoryError: If database operation fails
        """
        try:
            with self.session_manager.get_session() as session:
                stmt = select(EvaluationQuestionResultModel.id).where(
                    and_(
                        EvaluationQuestionResultModel.evaluation_id == evaluation_id,
                        EvaluationQuestionResultModel.question_id == question_id,
                    )
                )
                result = session.execute(stmt).scalar_one_or_none()
                return result is not None
        except SQLAlchemyError as e:
            raise RepositoryError(
                f"Failed to check question result existence: {e}"
            ) from e

    def delete_by_evaluation_id(self, evaluation_id: uuid.UUID) -> None:
        """Delete all question results for an evaluation.

        Args:
            evaluation_id: Evaluation identifier

        Raises:
            RepositoryError: If database operation fails
        """
        try:
            with self.session_manager.get_session() as session:
                from sqlalchemy import delete

                stmt = delete(EvaluationQuestionResultModel).where(
                    EvaluationQuestionResultModel.evaluation_id == evaluation_id
                )
                session.execute(stmt)
                # Session is automatically committed by context manager
        except SQLAlchemyError as e:
            raise RepositoryError(
                f"Failed to delete question results for evaluation: {e}"
            ) from e

    def get_completed_question_ids(self, evaluation_id: uuid.UUID) -> list[str]:
        """Get list of question IDs that have been completed for an evaluation.

        Args:
            evaluation_id: Evaluation identifier

        Returns:
            List of question IDs that have been processed

        Raises:
            RepositoryError: If database operation fails
        """
        try:
            with self.session_manager.get_session() as session:
                stmt = (
                    select(EvaluationQuestionResultModel.question_id)
                    .where(EvaluationQuestionResultModel.evaluation_id == evaluation_id)
                    .order_by(EvaluationQuestionResultModel.processed_at)
                )
                results = session.execute(stmt).scalars().all()
                return list(results)
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to get completed question IDs: {e}") from e

    def get_next_question_index(self, evaluation_id: uuid.UUID) -> int:
        """Get the index of the next question to process.

        Args:
            evaluation_id: Evaluation identifier

        Returns:
            Zero-based index of next question to process

        Raises:
            RepositoryError: If database operation fails
        """
        try:
            with self.session_manager.get_session() as session:
                stmt = select(func.count(EvaluationQuestionResultModel.id)).where(
                    EvaluationQuestionResultModel.evaluation_id == evaluation_id
                )
                completed_count = session.execute(stmt).scalar() or 0
                return completed_count
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to get next question index: {e}") from e
