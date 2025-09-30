"""Benchmark processing service."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from ....infrastructure.csv.benchmark_csv_reader import BenchmarkCsvReader
from ...domain.entities.preprocessed_benchmark import PreprocessedBenchmark
from ...domain.repositories.preprocessed_benchmark_repository import (
    PreprocessedBenchmarkRepository,
)
from ..dto.benchmark_info import BenchmarkInfo
from ..dto.validation_result import ValidationResult
from .exceptions import BenchmarkNotFoundError


class BenchmarkProcessor:
    """Handles benchmark preprocessing and management.

    Application service responsible for benchmark lifecycle management,
    validation, and metadata operations while maintaining clean separation
    between domain and infrastructure concerns.
    """

    def __init__(
        self,
        benchmark_repository: PreprocessedBenchmarkRepository,
    ) -> None:
        """Initialize the benchmark processor.

        Args:
            benchmark_repository: Repository for benchmark persistence
        """
        self._benchmark_repo = benchmark_repository
        self._csv_reader = BenchmarkCsvReader()
        self._logger = logging.getLogger(__name__)

    def list_available_benchmarks(self) -> list[BenchmarkInfo]:
        """Get all available preprocessed benchmarks.

        Returns:
            List of benchmark information objects

        Raises:
            ExternalServiceError: If repository access fails
        """
        self._logger.info("Listing available benchmarks")

        try:
            benchmarks = self._benchmark_repo.list_all()
            benchmark_infos = [
                self._benchmark_to_info(benchmark) for benchmark in benchmarks
            ]

            self._logger.info(
                "Successfully retrieved benchmarks",
                extra={"count": len(benchmark_infos)},
            )

            return benchmark_infos

        except Exception as e:
            self._logger.error(
                "Failed to list benchmarks",
                extra={"error": str(e)},
            )
            from .exceptions import ExternalServiceError

            raise ExternalServiceError(
                "Failed to retrieve benchmark list",
                service_name="benchmark_repository",
            ) from e

    def get_benchmark_details(self, benchmark_name: str) -> BenchmarkInfo:
        """Get detailed information about a specific benchmark.

        Args:
            benchmark_name: Name of the benchmark to retrieve

        Returns:
            Detailed benchmark information

        Raises:
            BenchmarkNotFoundError: If benchmark doesn't exist
            ExternalServiceError: If repository access fails
        """
        self._logger.info(
            "Getting benchmark details",
            extra={"benchmark_name": benchmark_name},
        )

        try:
            benchmark = self._benchmark_repo.get_by_name(benchmark_name)
            benchmark_info = self._benchmark_to_info(benchmark)

            self._logger.info(
                "Successfully retrieved benchmark details",
                extra={
                    "benchmark_name": benchmark_name,
                    "question_count": benchmark_info.question_count,
                },
            )

            return benchmark_info

        except Exception as e:
            self._logger.error(
                "Failed to get benchmark details",
                extra={"benchmark_name": benchmark_name, "error": str(e)},
            )

            # Check if it's a not found error vs other repository errors
            if "not found" in str(e).lower():
                raise BenchmarkNotFoundError(
                    f"Benchmark '{benchmark_name}' not found"
                ) from e

            from .exceptions import ExternalServiceError

            raise ExternalServiceError(
                f"Failed to retrieve benchmark '{benchmark_name}'",
                service_name="benchmark_repository",
            ) from e

    def get_benchmark_by_id(self, benchmark_id: uuid.UUID) -> BenchmarkInfo:
        """Get benchmark information by ID.

        Args:
            benchmark_id: ID of the benchmark to retrieve

        Returns:
            Benchmark information

        Raises:
            BenchmarkNotFoundError: If benchmark doesn't exist
            ExternalServiceError: If repository access fails
        """
        self._logger.info(
            "Getting benchmark by ID",
            extra={"benchmark_id": str(benchmark_id)},
        )

        try:
            benchmark = self._benchmark_repo.get_by_id(benchmark_id)
            return self._benchmark_to_info(benchmark)

        except Exception as e:
            self._logger.error(
                "Failed to get benchmark by ID",
                extra={"benchmark_id": str(benchmark_id), "error": str(e)},
            )

            if "not found" in str(e).lower():
                raise BenchmarkNotFoundError(
                    f"Benchmark with ID {benchmark_id} not found"
                ) from e

            from .exceptions import ExternalServiceError

            raise ExternalServiceError(
                f"Failed to retrieve benchmark {benchmark_id}",
                service_name="benchmark_repository",
            ) from e

    def search_benchmarks(
        self,
        format_version: str | None = None,
        metadata_filters: dict[str, Any] | None = None,
    ) -> list[BenchmarkInfo]:
        """Search benchmarks by criteria.

        Args:
            format_version: Optional format version to filter by
            metadata_filters: Optional metadata criteria

        Returns:
            List of matching benchmark information objects

        Raises:
            ExternalServiceError: If repository access fails
        """
        self._logger.info(
            "Searching benchmarks",
            extra={
                "format_version": format_version,
                "metadata_filters": metadata_filters,
            },
        )

        try:
            if format_version:
                benchmarks = self._benchmark_repo.list_by_format_version(format_version)
            elif metadata_filters:
                benchmarks = self._benchmark_repo.search_by_metadata(metadata_filters)
            else:
                benchmarks = self._benchmark_repo.list_all()

            benchmark_infos = [
                self._benchmark_to_info(benchmark) for benchmark in benchmarks
            ]

            self._logger.info(
                "Successfully searched benchmarks",
                extra={"results_count": len(benchmark_infos)},
            )

            return benchmark_infos

        except Exception as e:
            self._logger.error(
                "Failed to search benchmarks",
                extra={"error": str(e)},
            )
            from .exceptions import ExternalServiceError

            raise ExternalServiceError(
                "Failed to search benchmarks",
                service_name="benchmark_repository",
            ) from e

    def get_benchmark_summary_stats(self) -> dict[str, Any]:
        """Get summary statistics about all benchmarks.

        Returns:
            Dictionary with benchmark statistics

        Raises:
            ExternalServiceError: If repository access fails
        """
        self._logger.info("Getting benchmark summary statistics")

        try:
            stats = self._benchmark_repo.get_summary_stats()

            self._logger.info(
                "Successfully retrieved benchmark statistics",
                extra={"total_benchmarks": stats.get("total_count", 0)},
            )

            return stats

        except Exception as e:
            self._logger.error(
                "Failed to get benchmark statistics",
                extra={"error": str(e)},
            )
            from .exceptions import ExternalServiceError

            raise ExternalServiceError(
                "Failed to retrieve benchmark statistics",
                service_name="benchmark_repository",
            ) from e

    def validate_benchmark_name(self, name: str) -> ValidationResult:
        """Validate a benchmark name for availability.

        Args:
            name: Benchmark name to validate

        Returns:
            Validation result indicating availability
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Check name format
        if not name or name.strip() != name:
            errors.append(
                "Benchmark name cannot be empty or have leading/trailing spaces"
            )

        if len(name) > 100:
            errors.append("Benchmark name cannot exceed 100 characters")

        # Check if name already exists
        try:
            existing = self._benchmark_repo.get_by_name(name)
            if existing:
                errors.append(f"Benchmark with name '{name}' already exists")
        except Exception:
            # Name doesn't exist, which is good for validation
            pass

        if errors:
            return ValidationResult.failure(errors, warnings)
        return ValidationResult.success(warnings)

    def import_benchmark_from_csv(
        self,
        csv_file_path: str,
        benchmark_name: str | None = None,
        description: str | None = None,
    ) -> BenchmarkInfo:
        """Import benchmark from CSV file with INPUT,OUTPUT columns.

        Args:
            csv_file_path: Path to CSV file containing INPUT,OUTPUT columns
            benchmark_name: Optional custom name (defaults to filename)
            description: Optional benchmark description

        Returns:
            BenchmarkInfo for the imported benchmark

        Raises:
            BenchmarkNotFoundError: If CSV file doesn't exist
            ValidationError: If benchmark name already exists or CSV format invalid
            ExternalServiceError: If repository save operation fails
        """
        self._logger.info(
            "Importing benchmark from CSV",
            extra={"csv_file_path": csv_file_path, "benchmark_name": benchmark_name},
        )

        try:
            # Validate CSV file exists and has correct format
            csv_path = Path(csv_file_path)
            if not csv_path.exists():
                raise BenchmarkNotFoundError(f"CSV file not found: {csv_file_path}")

            # Validate CSV format before processing
            is_valid, validation_errors = self._csv_reader.validate_csv_format(
                csv_file_path
            )
            if not is_valid:
                from .exceptions import ValidationError

                raise ValidationError(
                    f"Invalid CSV format: {'; '.join(validation_errors)}",
                    validation_errors,
                )

            # Generate benchmark name from filename if not provided
            if benchmark_name is None:
                benchmark_name = csv_path.stem  # Filename without extension

            # Generate description if not provided
            if description is None:
                description = f"Benchmark imported from {csv_path.name}"

            # Validate benchmark name doesn't already exist
            name_validation = self.validate_benchmark_name(benchmark_name)
            if not name_validation.is_valid:
                from .exceptions import ValidationError

                raise ValidationError(
                    f"Benchmark name validation failed: {'; '.join(name_validation.errors)}",
                    name_validation.errors,
                )

            # Read questions from CSV
            questions = self._csv_reader.read_questions_from_csv(csv_file_path)

            if not questions:
                from .exceptions import ValidationError

                raise ValidationError(
                    "No valid questions found in CSV file",
                    ["No valid questions found in CSV file"],
                )

            # Create PreprocessedBenchmark entity
            benchmark = PreprocessedBenchmark(
                benchmark_id=uuid.uuid4(),
                name=benchmark_name,
                description=description,
                questions=questions,
                metadata={
                    "source_file": str(csv_path),
                    "import_date": datetime.now().isoformat(),
                    "format_version": "1.0",
                },
                created_at=datetime.now(),
                question_count=len(questions),
                format_version="1.0",
            )

            # Save to repository
            self._benchmark_repo.save(benchmark)

            # Convert to BenchmarkInfo for return
            benchmark_info = self._benchmark_to_info(benchmark)

            self._logger.info(
                "Successfully imported benchmark from CSV",
                extra={
                    "benchmark_name": benchmark_name,
                    "question_count": len(questions),
                    "csv_file": csv_file_path,
                },
            )

            return benchmark_info

        except BenchmarkNotFoundError:
            raise
        except Exception as e:
            self._logger.error(
                "Failed to import benchmark from CSV",
                extra={"csv_file_path": csv_file_path, "error": str(e)},
            )

            # Map specific exception types
            if "validation" in str(e).lower() or "invalid" in str(e).lower():
                from .exceptions import ValidationError

                raise ValidationError(
                    f"Benchmark import validation failed: {e}", [str(e)]
                ) from e

            from .exceptions import ExternalServiceError

            raise ExternalServiceError(
                f"Failed to import benchmark from CSV: {e}",
                service_name="benchmark_processor",
            ) from e

    def _benchmark_to_info(self, benchmark: PreprocessedBenchmark) -> BenchmarkInfo:
        """Convert benchmark entity to info DTO.

        Args:
            benchmark: Domain benchmark entity

        Returns:
            Benchmark info DTO
        """
        # Extract categories from metadata if available
        categories = None
        average_length = None

        if benchmark.metadata:
            categories = benchmark.metadata.get("categories")
            average_length = benchmark.metadata.get("average_question_length")

        return BenchmarkInfo(
            benchmark_id=benchmark.benchmark_id,
            name=benchmark.name,
            description=benchmark.description,
            question_count=benchmark.question_count,
            created_at=benchmark.created_at,
            format_version=benchmark.format_version,
            categories=categories,
            average_question_length=average_length,
        )
