"""CSV writer for evaluation results export functionality."""

import csv
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from ml_agents_v2.core.domain.services.export_exceptions import (
    ExportFileError,
    InvalidExportDataError,
)
from ml_agents_v2.core.domain.services.export_service import ExportService

if TYPE_CHECKING:
    from ml_agents_v2.core.domain.entities.evaluation_question_result import (
        EvaluationQuestionResult,
    )


class EvaluationResultsCsvWriter(ExportService):
    """Infrastructure implementation for exporting evaluation results to CSV.

    Handles conversion from domain EvaluationQuestionResult objects to CSV format
    with proper formatting and error handling. This is an infrastructure concern
    that handles file I/O and format conversion.
    """

    def __init__(self) -> None:
        """Initialize CSV writer."""
        self._logger = logging.getLogger(__name__)

    def export_to_csv(
        self, question_results: list["EvaluationQuestionResult"], output_path: str
    ) -> None:
        """Export evaluation question results to CSV format.

        Creates a CSV file with columns for all relevant question result data
        including evaluation metadata, question details, answers, and performance metrics.

        Args:
            question_results: List of evaluation question results to export
            output_path: Path where the CSV file should be written

        Raises:
            InvalidExportDataError: If question_results is empty
            ExportFileError: If output_path is invalid or file cannot be written
        """
        if not question_results:
            raise InvalidExportDataError("Cannot export empty question results list")

        output_file = Path(output_path)

        # Validate output directory exists and is writable
        try:
            output_file.parent.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError) as e:
            raise ExportFileError(
                file_path=output_path, operation="create directory", details=str(e)
            ) from e

        self._logger.info(
            f"Exporting {len(question_results)} question results to CSV: {output_path}"
        )

        try:
            with open(output_file, mode="w", newline="", encoding="utf-8") as file:
                # Define CSV columns matching the expected format
                fieldnames = [
                    "evaluation_id",
                    "question_id",
                    "question_text",
                    "expected_answer",
                    "actual_answer",
                    "is_correct",
                    "execution_time",
                    "error_message",
                    "processed_at",
                ]

                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()

                # Write each question result as a CSV row
                for result in question_results:
                    row = {
                        "evaluation_id": str(result.evaluation_id),
                        "question_id": result.question_id,
                        "question_text": result.question_text,
                        "expected_answer": result.expected_answer,
                        "actual_answer": result.actual_answer or "",
                        "is_correct": (
                            "" if result.is_correct is None else str(result.is_correct)
                        ),
                        "execution_time": result.execution_time,
                        "error_message": result.error_message or "",
                        "processed_at": result.processed_at.isoformat(),
                    }
                    writer.writerow(row)

        except (OSError, PermissionError) as e:
            raise ExportFileError(
                file_path=output_path, operation="write", details=str(e)
            ) from e
        except Exception as e:
            raise ExportFileError(
                file_path=output_path,
                operation="write",
                details=f"Unexpected error during CSV export: {str(e)}",
            ) from e

        self._logger.info(
            f"Successfully exported {len(question_results)} results to {output_path}"
        )
