"""SQLAlchemy implementation of PreprocessedBenchmarkRepository."""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from ml_agents_v2.core.domain.entities.preprocessed_benchmark import (
    PreprocessedBenchmark,
)
from ml_agents_v2.core.domain.repositories.exceptions import (
    EntityNotFoundError,
    RepositoryError,
)
from ml_agents_v2.core.domain.repositories.preprocessed_benchmark_repository import (
    PreprocessedBenchmarkRepository,
)
from ml_agents_v2.infrastructure.database.models.benchmark import BenchmarkModel
from ml_agents_v2.infrastructure.database.session_manager import DatabaseSessionManager

# Benchmark registry mapping user-friendly names to filename patterns
# Updated to match infrastructure requirements documentation and test expectations
BENCHMARK_REGISTRY = {
    "GPQA": "BENCHMARK-01-GPQA.csv",
    "FOLIO": "BENCHMARK-05-FOLIO.csv",
    "BBEH": "BENCHMARK-06-BBEH.csv",
    "MATH3": "BENCHMARK-07-MATH3.csv",
    "LeetCode_Python_Easy": "BENCHMARK-08-LeetCode_Python_Easy.csv",
}


class BenchmarkRepositoryImpl(PreprocessedBenchmarkRepository):
    """SQLAlchemy implementation of PreprocessedBenchmarkRepository interface.

    Provides concrete implementation of benchmark persistence using
    SQLAlchemy ORM with proper domain entity conversion.
    """

    def __init__(self, session_manager: DatabaseSessionManager):
        """Initialize repository with session manager.

        Args:
            session_manager: Database session manager for SQLAlchemy operations
        """
        self.session_manager = session_manager

    def save(self, benchmark: PreprocessedBenchmark) -> None:
        """Save benchmark to database.

        Args:
            benchmark: Domain benchmark entity to save

        Raises:
            RepositoryError: If database operation fails
        """
        try:
            benchmark_model = BenchmarkModel.from_domain(benchmark)

            with self.session_manager.get_session() as session:
                session.add(benchmark_model)
                # Session is automatically committed by context manager
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to save benchmark: {e}") from e

    def get_by_id(self, benchmark_id: uuid.UUID) -> PreprocessedBenchmark:
        """Retrieve benchmark by ID.

        Args:
            benchmark_id: UUID of benchmark to retrieve

        Returns:
            Domain benchmark entity

        Raises:
            EntityNotFoundError: If benchmark not found
            RepositoryError: If database operation fails
        """
        try:
            with self.session_manager.get_session() as session:
                stmt = select(BenchmarkModel).where(
                    BenchmarkModel.benchmark_id == benchmark_id
                )
                result = session.execute(stmt)
                benchmark_model = result.scalar_one_or_none()

                if benchmark_model is None:
                    raise EntityNotFoundError("Benchmark", str(benchmark_id))

                return benchmark_model.to_domain()
        except EntityNotFoundError:
            raise
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to retrieve benchmark: {e}") from e

    def get_by_name(self, name: str) -> PreprocessedBenchmark:
        """Retrieve benchmark by name.

        First tries direct lookup by name, then falls back to registry mapping.
        This supports both user-friendly names stored directly in the database
        and registry-mapped CSV filenames.

        Args:
            name: Name of benchmark to retrieve (user-friendly name or CSV filename)

        Returns:
            Domain benchmark entity

        Raises:
            EntityNotFoundError: If benchmark not found
            RepositoryError: If database operation fails
        """
        try:
            with self.session_manager.get_session() as session:
                # First, try direct lookup by the provided name
                stmt = select(BenchmarkModel).where(BenchmarkModel.name == name)
                result = session.execute(stmt)
                benchmark_model = result.scalar_one_or_none()

                if benchmark_model is not None:
                    return benchmark_model.to_domain()

                # If direct lookup fails, try registry mapping
                filename = BENCHMARK_REGISTRY.get(name)
                if filename is not None and filename != name:
                    stmt = select(BenchmarkModel).where(BenchmarkModel.name == filename)
                    result = session.execute(stmt)
                    benchmark_model = result.scalar_one_or_none()

                    if benchmark_model is not None:
                        return benchmark_model.to_domain()

                # If both lookups fail, raise EntityNotFoundError
                raise EntityNotFoundError("Benchmark", name)

        except EntityNotFoundError:
            raise
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to retrieve benchmark by name: {e}") from e

    def update(self, benchmark: PreprocessedBenchmark) -> None:
        """Update existing benchmark in database.

        Args:
            benchmark: Updated domain benchmark entity

        Raises:
            EntityNotFoundError: If benchmark not found
            RepositoryError: If database operation fails
        """
        try:
            with self.session_manager.get_session() as session:
                stmt = select(BenchmarkModel).where(
                    BenchmarkModel.benchmark_id == benchmark.benchmark_id
                )
                result = session.execute(stmt)
                existing_model = result.scalar_one_or_none()

                if existing_model is None:
                    raise EntityNotFoundError("Benchmark", str(benchmark.benchmark_id))

                # Update the existing model with new data
                updated_model = BenchmarkModel.from_domain(benchmark)

                # Copy all fields from updated model to existing model
                existing_model.name = updated_model.name
                existing_model.description = updated_model.description
                existing_model.format_version = updated_model.format_version
                existing_model.question_count = updated_model.question_count
                existing_model.created_at = updated_model.created_at
                existing_model.questions_json = updated_model.questions_json
                existing_model.metadata_json = updated_model.metadata_json

                # Session is automatically committed by context manager
        except EntityNotFoundError:
            raise
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to update benchmark: {e}") from e

    def delete(self, benchmark_id: uuid.UUID) -> None:
        """Delete benchmark from database.

        Args:
            benchmark_id: UUID of benchmark to delete

        Raises:
            EntityNotFoundError: If benchmark not found
            RepositoryError: If database operation fails
        """
        try:
            with self.session_manager.get_session() as session:
                stmt = select(BenchmarkModel).where(
                    BenchmarkModel.benchmark_id == benchmark_id
                )
                result = session.execute(stmt)
                benchmark_model = result.scalar_one_or_none()

                if benchmark_model is None:
                    raise EntityNotFoundError("Benchmark", str(benchmark_id))

                session.delete(benchmark_model)
                # Session is automatically committed by context manager
        except EntityNotFoundError:
            raise
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to delete benchmark: {e}") from e

    def exists(self, benchmark_id: uuid.UUID) -> bool:
        """Check if benchmark exists in database.

        Args:
            benchmark_id: UUID of benchmark to check

        Returns:
            True if benchmark exists, False otherwise

        Raises:
            RepositoryError: If database operation fails
        """
        try:
            with self.session_manager.get_session() as session:
                stmt = select(BenchmarkModel.benchmark_id).where(
                    BenchmarkModel.benchmark_id == benchmark_id
                )
                result = session.execute(stmt)
                return result.scalar_one_or_none() is not None
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to check benchmark existence: {e}") from e

    def list_all(self, limit: int | None = None) -> list[PreprocessedBenchmark]:
        """List all benchmarks.

        Returns:
            List of all domain benchmark entities

        Raises:
            RepositoryError: If database operation fails
        """
        try:
            with self.session_manager.get_session() as session:
                stmt = select(BenchmarkModel).order_by(BenchmarkModel.created_at.desc())
                if limit is not None:
                    stmt = stmt.limit(limit)
                result = session.execute(stmt)
                benchmark_models = result.scalars().all()

                return [model.to_domain() for model in benchmark_models]
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to list all benchmarks: {e}") from e

    def list_by_format_version(
        self, format_version: str
    ) -> list[PreprocessedBenchmark]:
        """List benchmarks by format version.

        Args:
            format_version: Format version to filter by

        Returns:
            List of domain benchmark entities

        Raises:
            RepositoryError: If database operation fails
        """
        try:
            with self.session_manager.get_session() as session:
                stmt = select(BenchmarkModel).where(
                    BenchmarkModel.format_version == format_version
                )
                result = session.execute(stmt)
                benchmark_models = result.scalars().all()

                return [model.to_domain() for model in benchmark_models]
        except SQLAlchemyError as e:
            raise RepositoryError(
                f"Failed to list benchmarks by format version: {e}"
            ) from e

    def search_by_metadata(
        self, metadata_filters: dict[str, Any]
    ) -> list[PreprocessedBenchmark]:
        """Search benchmarks by metadata criteria.

        Args:
            metadata_filters: Dictionary of metadata key-value pairs to match

        Returns:
            List of domain benchmark entities matching criteria

        Raises:
            RepositoryError: If database operation fails
        """
        try:
            with self.session_manager.get_session() as session:
                # For now, get all benchmarks and filter in Python
                # TODO: Implement JSON querying for better performance
                stmt = select(BenchmarkModel)
                result = session.execute(stmt)
                benchmark_models = result.scalars().all()

                # Convert to domain entities and filter by metadata
                matching_benchmarks = []
                for model in benchmark_models:
                    benchmark = model.to_domain()

                    # Check if all query criteria match the benchmark metadata
                    matches = all(
                        key in benchmark.metadata and benchmark.metadata[key] == value
                        for key, value in metadata_filters.items()
                    )

                    if matches:
                        matching_benchmarks.append(benchmark)

                return matching_benchmarks
        except SQLAlchemyError as e:
            raise RepositoryError(
                f"Failed to search benchmarks by metadata: {e}"
            ) from e

    def get_summary_stats(self) -> dict[str, int]:
        """Get summary statistics for all benchmarks.

        Returns:
            Dictionary with summary statistics

        Raises:
            RepositoryError: If database operation fails
        """
        try:
            with self.session_manager.get_session() as session:
                # Get total count
                stmt = select(BenchmarkModel)
                result = session.execute(stmt)
                benchmarks = result.scalars().all()

                total_benchmarks = len(benchmarks)
                total_questions = sum(model.question_count for model in benchmarks)

                return {
                    "total_benchmarks": total_benchmarks,
                    "total_questions": total_questions,
                }
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to get benchmark summary stats: {e}") from e

    def list_available_names(self) -> list[str]:
        """Return list of user-friendly benchmark names.

        Returns:
            List of short benchmark names from BENCHMARK_REGISTRY

        Raises:
            RepositoryError: If operation fails
        """
        try:
            return list(BENCHMARK_REGISTRY.keys())
        except Exception as e:
            raise RepositoryError(
                f"Failed to list available benchmark names: {e}"
            ) from e
