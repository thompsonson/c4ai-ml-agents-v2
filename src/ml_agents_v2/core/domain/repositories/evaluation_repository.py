"""EvaluationRepository interface."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from ..entities.evaluation import Evaluation


class EvaluationRepository(ABC):
    """Repository interface for Evaluation aggregate persistence.

    Defines the contract for storing, retrieving, and managing Evaluation
    entities while maintaining aggregate consistency and encapsulation.
    """

    @abstractmethod
    async def save(self, evaluation: Evaluation) -> None:
        """Persist an evaluation entity.

        Args:
            evaluation: The evaluation to persist

        Raises:
            RepositoryError: If persistence fails
        """

    @abstractmethod
    async def get_by_id(self, evaluation_id: uuid.UUID) -> Evaluation | None:
        """Retrieve evaluation by ID.

        Args:
            evaluation_id: Unique identifier of the evaluation

        Returns:
            Evaluation entity if found, None otherwise

        Raises:
            RepositoryError: If retrieval fails
        """

    @abstractmethod
    async def list_by_status(self, status: str) -> list[Evaluation]:
        """List evaluations by status.

        Args:
            status: Evaluation status to filter by

        Returns:
            List of evaluations with the specified status

        Raises:
            RepositoryError: If retrieval fails
        """

    @abstractmethod
    async def list_by_benchmark_id(self, benchmark_id: uuid.UUID) -> list[Evaluation]:
        """List evaluations for a specific benchmark.

        Args:
            benchmark_id: Benchmark ID to filter by

        Returns:
            List of evaluations for the benchmark

        Raises:
            RepositoryError: If retrieval fails
        """

    @abstractmethod
    async def update(self, evaluation: Evaluation) -> None:
        """Update an existing evaluation.

        Args:
            evaluation: The evaluation with updated state

        Raises:
            RepositoryError: If update fails
            EntityNotFoundError: If evaluation doesn't exist
        """

    @abstractmethod
    async def delete(self, evaluation_id: uuid.UUID) -> None:
        """Delete an evaluation by ID.

        Args:
            evaluation_id: ID of evaluation to delete

        Raises:
            RepositoryError: If deletion fails
            EntityNotFoundError: If evaluation doesn't exist
        """

    @abstractmethod
    async def exists(self, evaluation_id: uuid.UUID) -> bool:
        """Check if evaluation exists.

        Args:
            evaluation_id: ID to check

        Returns:
            True if evaluation exists, False otherwise

        Raises:
            RepositoryError: If check fails
        """

    @abstractmethod
    async def list_all(self, limit: int | None = None) -> list[Evaluation]:
        """List all evaluations with optional limit.

        Args:
            limit: Maximum number of evaluations to return

        Returns:
            List of evaluations

        Raises:
            RepositoryError: If retrieval fails
        """
