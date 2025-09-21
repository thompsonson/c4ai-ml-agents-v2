"""SQLAlchemy implementation of EvaluationRepository."""

import uuid
from typing import Union

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from ml_agents_v2.core.domain.entities.evaluation import Evaluation
from ml_agents_v2.core.domain.repositories.evaluation_repository import (
    EvaluationRepository,
)
from ml_agents_v2.core.domain.repositories.exceptions import (
    EntityNotFoundError,
    RepositoryError,
)
from ml_agents_v2.infrastructure.database.models.evaluation import EvaluationModel
from ml_agents_v2.infrastructure.database.session_manager import DatabaseSessionManager


class EvaluationRepositoryImpl(EvaluationRepository):
    """SQLAlchemy implementation of EvaluationRepository interface.

    Provides concrete implementation of evaluation persistence using
    SQLAlchemy ORM with proper domain entity conversion.
    """

    def __init__(self, session_manager: DatabaseSessionManager):
        """Initialize repository with session manager.

        Args:
            session_manager: Database session manager for SQLAlchemy operations
        """
        self.session_manager = session_manager

    def save(self, evaluation: Evaluation) -> None:
        """Save evaluation to database.

        Args:
            evaluation: Domain evaluation entity to save

        Raises:
            RepositoryError: If database operation fails
        """
        try:
            evaluation_model = EvaluationModel.from_domain(evaluation)

            with self.session_manager.get_session() as session:
                session.add(evaluation_model)
                # Session is automatically committed by context manager
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to save evaluation: {e}") from e

    def get_by_id(self, evaluation_id: uuid.UUID) -> Evaluation:
        """Retrieve evaluation by ID.

        Args:
            evaluation_id: UUID of evaluation to retrieve

        Returns:
            Domain evaluation entity

        Raises:
            EntityNotFoundError: If evaluation not found
            RepositoryError: If database operation fails
        """
        try:
            with self.session_manager.get_session() as session:
                stmt = select(EvaluationModel).where(
                    EvaluationModel.evaluation_id == evaluation_id
                )
                result = session.execute(stmt)
                evaluation_model = result.scalar_one_or_none()

                if evaluation_model is None:
                    raise EntityNotFoundError("Evaluation", str(evaluation_id))

                return evaluation_model.to_domain()
        except EntityNotFoundError:
            raise
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to retrieve evaluation: {e}") from e

    def update(self, evaluation: Evaluation) -> None:
        """Update existing evaluation in database.

        Args:
            evaluation: Updated domain evaluation entity

        Raises:
            EntityNotFoundError: If evaluation not found
            RepositoryError: If database operation fails
        """
        try:
            with self.session_manager.get_session() as session:
                stmt = select(EvaluationModel).where(
                    EvaluationModel.evaluation_id == evaluation.evaluation_id
                )
                result = session.execute(stmt)
                existing_model = result.scalar_one_or_none()

                if existing_model is None:
                    raise EntityNotFoundError(
                        "Evaluation", str(evaluation.evaluation_id)
                    )

                # Update the existing model with new data
                updated_model = EvaluationModel.from_domain(evaluation)

                # Copy all fields from updated model to existing model
                existing_model.preprocessed_benchmark_id = (
                    updated_model.preprocessed_benchmark_id
                )
                existing_model.agent_config_json = updated_model.agent_config_json
                existing_model.status = updated_model.status
                existing_model.created_at = updated_model.created_at
                existing_model.started_at = updated_model.started_at
                existing_model.completed_at = updated_model.completed_at
                existing_model.results_json = updated_model.results_json
                existing_model.failure_reason_json = updated_model.failure_reason_json

                # Session is automatically committed by context manager
        except EntityNotFoundError:
            raise
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to update evaluation: {e}") from e

    def delete(self, evaluation_id: uuid.UUID) -> None:
        """Delete evaluation from database.

        Args:
            evaluation_id: UUID of evaluation to delete

        Raises:
            EntityNotFoundError: If evaluation not found
            RepositoryError: If database operation fails
        """
        try:
            with self.session_manager.get_session() as session:
                stmt = select(EvaluationModel).where(
                    EvaluationModel.evaluation_id == evaluation_id
                )
                result = session.execute(stmt)
                evaluation_model = result.scalar_one_or_none()

                if evaluation_model is None:
                    raise EntityNotFoundError("Evaluation", str(evaluation_id))

                session.delete(evaluation_model)
                # Session is automatically committed by context manager
        except EntityNotFoundError:
            raise
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to delete evaluation: {e}") from e

    def exists(self, evaluation_id: uuid.UUID) -> bool:
        """Check if evaluation exists in database.

        Args:
            evaluation_id: UUID of evaluation to check

        Returns:
            True if evaluation exists, False otherwise

        Raises:
            RepositoryError: If database operation fails
        """
        try:
            with self.session_manager.get_session() as session:
                stmt = select(EvaluationModel.evaluation_id).where(
                    EvaluationModel.evaluation_id == evaluation_id
                )
                result = session.execute(stmt)
                return result.scalar_one_or_none() is not None
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to check evaluation existence: {e}") from e

    def list_by_status(self, status: str) -> list[Evaluation]:
        """List evaluations by status.

        Args:
            status: Evaluation status to filter by

        Returns:
            List of domain evaluation entities

        Raises:
            RepositoryError: If database operation fails
        """
        try:
            with self.session_manager.get_session() as session:
                stmt = select(EvaluationModel).where(EvaluationModel.status == status)
                result = session.execute(stmt)
                evaluation_models = result.scalars().all()

                return [model.to_domain() for model in evaluation_models]
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to list evaluations by status: {e}") from e

    def list_by_benchmark_id(self, benchmark_id: uuid.UUID) -> list[Evaluation]:
        """List evaluations by benchmark ID.

        Args:
            benchmark_id: UUID of benchmark to filter by

        Returns:
            List of domain evaluation entities

        Raises:
            RepositoryError: If database operation fails
        """
        try:
            with self.session_manager.get_session() as session:
                stmt = select(EvaluationModel).where(
                    EvaluationModel.preprocessed_benchmark_id == benchmark_id
                )
                result = session.execute(stmt)
                evaluation_models = result.scalars().all()

                return [model.to_domain() for model in evaluation_models]
        except SQLAlchemyError as e:
            raise RepositoryError(
                f"Failed to list evaluations by benchmark: {e}"
            ) from e

    def list_all(self, limit: Union[int, None] = None) -> list[Evaluation]:
        """List all evaluations.

        Returns:
            List of all domain evaluation entities

        Raises:
            RepositoryError: If database operation fails
        """
        try:
            with self.session_manager.get_session() as session:
                stmt = select(EvaluationModel).order_by(
                    EvaluationModel.created_at.desc()
                )
                if limit is not None:
                    stmt = stmt.limit(limit)
                result = session.execute(stmt)
                evaluation_models = result.scalars().all()

                return [model.to_domain() for model in evaluation_models]
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to list all evaluations: {e}") from e
