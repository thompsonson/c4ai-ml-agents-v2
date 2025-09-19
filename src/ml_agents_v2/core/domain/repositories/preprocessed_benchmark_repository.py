"""PreprocessedBenchmarkRepository interface."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Any

from ..entities.preprocessed_benchmark import PreprocessedBenchmark


class PreprocessedBenchmarkRepository(ABC):
    """Repository interface for PreprocessedBenchmark aggregate persistence.

    Defines the contract for storing, retrieving, and managing
    PreprocessedBenchmark entities while maintaining aggregate
    consistency and encapsulation.
    """

    @abstractmethod
    async def save(self, benchmark: PreprocessedBenchmark) -> None:
        """Persist a preprocessed benchmark entity.

        Args:
            benchmark: The benchmark to persist

        Raises:
            RepositoryError: If persistence fails
        """

    @abstractmethod
    async def get_by_id(self, benchmark_id: uuid.UUID) -> PreprocessedBenchmark | None:
        """Retrieve benchmark by ID.

        Args:
            benchmark_id: Unique identifier of the benchmark

        Returns:
            PreprocessedBenchmark entity if found, None otherwise

        Raises:
            RepositoryError: If retrieval fails
        """

    @abstractmethod
    async def get_by_name(self, name: str) -> PreprocessedBenchmark | None:
        """Retrieve benchmark by name.

        Args:
            name: Name of the benchmark

        Returns:
            PreprocessedBenchmark entity if found, None otherwise

        Raises:
            RepositoryError: If retrieval fails
        """

    @abstractmethod
    async def list_by_format_version(
        self, format_version: str
    ) -> list[PreprocessedBenchmark]:
        """List benchmarks by format version.

        Args:
            format_version: Format version to filter by

        Returns:
            List of benchmarks with the specified format version

        Raises:
            RepositoryError: If retrieval fails
        """

    @abstractmethod
    async def search_by_metadata(
        self, metadata_filters: dict[str, Any]
    ) -> list[PreprocessedBenchmark]:
        """Search benchmarks by metadata criteria.

        Args:
            metadata_filters: Key-value pairs to filter metadata

        Returns:
            List of benchmarks matching the metadata criteria

        Raises:
            RepositoryError: If search fails
        """

    @abstractmethod
    async def update(self, benchmark: PreprocessedBenchmark) -> None:
        """Update an existing benchmark.

        Args:
            benchmark: The benchmark with updated state

        Raises:
            RepositoryError: If update fails
            EntityNotFoundError: If benchmark doesn't exist
        """

    @abstractmethod
    async def delete(self, benchmark_id: uuid.UUID) -> None:
        """Delete a benchmark by ID.

        Args:
            benchmark_id: ID of benchmark to delete

        Raises:
            RepositoryError: If deletion fails
            EntityNotFoundError: If benchmark doesn't exist
        """

    @abstractmethod
    async def exists(self, benchmark_id: uuid.UUID) -> bool:
        """Check if benchmark exists.

        Args:
            benchmark_id: ID to check

        Returns:
            True if benchmark exists, False otherwise

        Raises:
            RepositoryError: If check fails
        """

    @abstractmethod
    async def list_all(self, limit: int | None = None) -> list[PreprocessedBenchmark]:
        """List all benchmarks with optional limit.

        Args:
            limit: Maximum number of benchmarks to return

        Returns:
            List of benchmarks

        Raises:
            RepositoryError: If retrieval fails
        """

    @abstractmethod
    async def get_summary_stats(self) -> dict[str, Any]:
        """Get summary statistics about stored benchmarks.

        Returns:
            Dictionary with stats like total count, format versions, etc.

        Raises:
            RepositoryError: If stats retrieval fails
        """
