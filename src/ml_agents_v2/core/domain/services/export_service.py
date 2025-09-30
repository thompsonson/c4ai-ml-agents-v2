"""Export service interface for evaluation results.

Domain service interface defining the contract for exporting evaluation
results to various formats while maintaining domain layer purity.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..entities.evaluation_question_result import EvaluationQuestionResult


class ExportService(ABC):
    """Domain service interface for exporting evaluation results.

    Defines the contract for converting evaluation question results
    into various export formats without coupling to specific file
    formats or I/O operations.
    """

    @abstractmethod
    def export_to_csv(
        self, question_results: list[EvaluationQuestionResult], output_path: str
    ) -> None:
        """Export evaluation question results to CSV format.

        Args:
            question_results: List of evaluation question results to export
            output_path: Path where the CSV file should be written

        Raises:
            ExportError: If export operation fails
            InvalidExportDataError: If question_results is empty
            ExportFileError: If output_path is invalid or file cannot be written
        """
