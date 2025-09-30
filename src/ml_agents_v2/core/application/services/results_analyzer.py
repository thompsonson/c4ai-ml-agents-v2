"""Results analysis service."""

from __future__ import annotations

import csv
import json
import logging
import uuid
from io import StringIO
from typing import Any

from ...domain.repositories.evaluation_repository import EvaluationRepository
from ...domain.repositories.preprocessed_benchmark_repository import (
    PreprocessedBenchmarkRepository,
)
from ..dto.evaluation_info import EvaluationInfo
from ..dto.evaluation_summary import EvaluationSummary
from .exceptions import EvaluationNotFoundError, ExternalServiceError, ValidationError


class ResultsAnalyzer:
    """Provides analysis and reporting capabilities for evaluations.

    Application service responsible for results analysis, export functionality,
    and comparative analysis across evaluations while maintaining clean
    separation between domain and infrastructure concerns.
    """

    def __init__(
        self,
        evaluation_repository: EvaluationRepository,
        benchmark_repository: PreprocessedBenchmarkRepository,
    ) -> None:
        """Initialize the results analyzer.

        Args:
            evaluation_repository: Repository for evaluation access
            benchmark_repository: Repository for benchmark access
        """
        self._evaluation_repo = evaluation_repository
        self._benchmark_repo = benchmark_repository
        self._logger = logging.getLogger(__name__)

    def get_evaluation_summary(self, evaluation_id: uuid.UUID) -> EvaluationSummary:
        """Get high-level results summary for an evaluation.

        Args:
            evaluation_id: ID of the evaluation

        Returns:
            Evaluation summary with key metrics

        Raises:
            EvaluationNotFoundError: If evaluation doesn't exist
            ExternalServiceError: If repository access fails
        """
        self._logger.info(
            "Getting evaluation summary",
            extra={"evaluation_id": str(evaluation_id)},
        )

        try:
            evaluation = self._evaluation_repo.get_by_id(evaluation_id)
        except Exception as e:
            self._logger.error(
                "Failed to retrieve evaluation",
                extra={"evaluation_id": str(evaluation_id), "error": str(e)},
            )
            raise EvaluationNotFoundError(
                f"Evaluation {evaluation_id} not found"
            ) from e

        if evaluation.status != "completed" or evaluation.results is None:
            raise ValidationError(
                f"Evaluation not completed (status: {evaluation.status})",
                ["Evaluation must be completed to generate summary"],
            )

        try:
            # Get benchmark information
            benchmark = self._benchmark_repo.get_by_id(
                evaluation.preprocessed_benchmark_id
            )

            # Calculate execution time
            execution_time_minutes = 0.0
            if evaluation.started_at and evaluation.completed_at:
                execution_time_minutes = (
                    evaluation.completed_at - evaluation.started_at
                ).total_seconds() / 60

            summary = EvaluationSummary(
                evaluation_id=evaluation.evaluation_id,
                agent_type=evaluation.agent_config.agent_type,
                model_name=evaluation.agent_config.model_name,
                benchmark_name=benchmark.name,
                status=evaluation.status,
                total_questions=evaluation.results.total_questions,
                correct_answers=evaluation.results.correct_answers,
                accuracy=evaluation.results.accuracy,
                execution_time_minutes=execution_time_minutes,
                average_time_per_question=evaluation.results.average_execution_time,
                error_count=evaluation.results.error_count,
                created_at=evaluation.created_at,
                completed_at=evaluation.completed_at,
            )

            self._logger.info(
                "Successfully generated evaluation summary",
                extra={
                    "evaluation_id": str(evaluation_id),
                    "accuracy": summary.accuracy,
                },
            )

            return summary

        except Exception as e:
            self._logger.error(
                "Failed to generate evaluation summary",
                extra={"evaluation_id": str(evaluation_id), "error": str(e)},
            )
            raise ExternalServiceError(
                "Failed to generate evaluation summary",
                service_name="benchmark_repository",
            ) from e

    def export_detailed_results(
        self,
        evaluation_id: uuid.UUID,
        export_format: str = "csv",
    ) -> str:
        """Export detailed results to specified format.

        Args:
            evaluation_id: ID of the evaluation to export
            export_format: Export format ("csv" or "json")

        Returns:
            Exported data as string

        Raises:
            EvaluationNotFoundError: If evaluation doesn't exist
            ValidationError: If export format is invalid or evaluation incomplete
            ExternalServiceError: If export generation fails
        """
        if export_format not in ["csv", "json"]:
            raise ValidationError(
                f"Unsupported export format: {export_format}",
                ["Export format must be 'csv' or 'json'"],
            )

        self._logger.info(
            "Exporting evaluation results",
            extra={
                "evaluation_id": str(evaluation_id),
                "format": export_format,
            },
        )

        try:
            evaluation = self._evaluation_repo.get_by_id(evaluation_id)
        except Exception as e:
            raise EvaluationNotFoundError(
                f"Evaluation {evaluation_id} not found"
            ) from e

        if evaluation.status != "completed" or evaluation.results is None:
            raise ValidationError(
                f"Evaluation not completed (status: {evaluation.status})",
                ["Evaluation must be completed to export results"],
            )

        try:
            benchmark = self._benchmark_repo.get_by_id(
                evaluation.preprocessed_benchmark_id
            )

            if export_format == "csv":
                return self._export_to_csv(evaluation, benchmark)
            else:
                return self._export_to_json(evaluation, benchmark)

        except Exception as e:
            self._logger.error(
                "Failed to export results",
                extra={
                    "evaluation_id": str(evaluation_id),
                    "format": export_format,
                    "error": str(e),
                },
            )
            raise ExternalServiceError(
                f"Failed to export results in {export_format} format",
                service_name="results_exporter",
            ) from e

    def list_evaluations(
        self,
        status_filter: str | None = None,
        benchmark_name_filter: str | None = None,
        agent_type_filter: str | None = None,
        limit: int | None = None,
    ) -> list[EvaluationInfo]:
        """List evaluations with advanced filtering options.

        Args:
            status_filter: Optional status to filter by
            benchmark_name_filter: Optional benchmark name to filter by
            agent_type_filter: Optional agent type to filter by
            limit: Optional limit on number of results

        Returns:
            List of evaluation information objects

        Raises:
            ExternalServiceError: If repository access fails
        """
        self._logger.info(
            "Listing evaluations with filters",
            extra={
                "status_filter": status_filter,
                "benchmark_filter": benchmark_name_filter,
                "agent_type_filter": agent_type_filter,
                "limit": limit,
            },
        )

        try:
            # Get evaluations based on status filter
            if status_filter:
                evaluations = self._evaluation_repo.list_by_status(status_filter)
            else:
                evaluations = self._evaluation_repo.list_all(limit)

            # Convert to DTOs with additional filtering
            evaluation_infos = []
            for evaluation in evaluations:
                try:
                    # Apply agent type filter
                    if (
                        agent_type_filter
                        and evaluation.agent_config.agent_type != agent_type_filter
                    ):
                        continue

                    benchmark = self._benchmark_repo.get_by_id(
                        evaluation.preprocessed_benchmark_id
                    )

                    # Apply benchmark name filter
                    if (
                        benchmark_name_filter
                        and benchmark.name != benchmark_name_filter
                    ):
                        continue

                    evaluation_info = self._evaluation_to_info(evaluation, benchmark)
                    evaluation_infos.append(evaluation_info)

                except Exception as e:
                    self._logger.warning(
                        "Failed to process evaluation for listing",
                        extra={
                            "evaluation_id": str(evaluation.evaluation_id),
                            "error": str(e),
                        },
                    )
                    continue

            self._logger.info(
                "Successfully listed evaluations",
                extra={"count": len(evaluation_infos)},
            )

            return evaluation_infos

        except Exception as e:
            self._logger.error(
                "Failed to list evaluations",
                extra={"error": str(e)},
            )
            raise ExternalServiceError(
                "Failed to retrieve evaluation list",
                service_name="evaluation_repository",
            ) from e

    def compare_evaluations(self, evaluation_ids: list[uuid.UUID]) -> dict[str, Any]:
        """Compare multiple evaluations and generate comparison report.

        Args:
            evaluation_ids: List of evaluation IDs to compare

        Returns:
            Comparison report with metrics and analysis

        Raises:
            ValidationError: If comparison parameters are invalid
            EvaluationNotFoundError: If any evaluation doesn't exist
            ExternalServiceError: If comparison generation fails
        """
        if len(evaluation_ids) < 2:
            raise ValidationError(
                "At least 2 evaluations required for comparison",
                ["Provide at least 2 evaluation IDs"],
            )

        self._logger.info(
            "Comparing evaluations",
            extra={
                "evaluation_ids": [str(eid) for eid in evaluation_ids],
                "count": len(evaluation_ids),
            },
        )

        try:
            summaries = []
            for evaluation_id in evaluation_ids:
                summary = self.get_evaluation_summary(evaluation_id)
                summaries.append(summary)

            # Generate comparison metrics
            comparison = {
                "evaluations": [
                    {
                        "id": str(summary.evaluation_id),
                        "agent_type": summary.agent_type,
                        "model_name": summary.model_name,
                        "benchmark_name": summary.benchmark_name,
                        "accuracy": summary.accuracy,
                        "execution_time_minutes": summary.execution_time_minutes,
                        "error_count": summary.error_count,
                    }
                    for summary in summaries
                ],
                "best_accuracy": max(s.accuracy for s in summaries),
                "worst_accuracy": min(s.accuracy for s in summaries),
                "average_accuracy": sum(s.accuracy for s in summaries) / len(summaries),
                "fastest_execution": min(s.execution_time_minutes for s in summaries),
                "slowest_execution": max(s.execution_time_minutes for s in summaries),
                "comparison_generated_at": "now",  # Would use datetime in real implementation
            }

            self._logger.info(
                "Successfully generated evaluation comparison",
                extra={
                    "best_accuracy": comparison["best_accuracy"],
                    "evaluation_count": len(summaries),
                },
            )

            return comparison

        except Exception as e:
            self._logger.error(
                "Failed to compare evaluations",
                extra={"error": str(e)},
            )
            raise ExternalServiceError(
                "Failed to generate evaluation comparison",
                service_name="results_analyzer",
            ) from e

    def _export_to_csv(self, evaluation: Any, benchmark: Any) -> str:
        """Export evaluation results to CSV format."""
        output = StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(
            [
                "evaluation_id",
                "agent_type",
                "model_name",
                "benchmark_name",
                "total_questions",
                "correct_answers",
                "accuracy",
                "execution_time_minutes",
                "error_count",
                "created_at",
                "completed_at",
            ]
        )

        # Calculate execution time
        execution_time = 0.0
        if evaluation.started_at and evaluation.completed_at:
            execution_time = (
                evaluation.completed_at - evaluation.started_at
            ).total_seconds() / 60

        # Write data row
        writer.writerow(
            [
                str(evaluation.evaluation_id),
                evaluation.agent_config.agent_type,
                evaluation.agent_config.model_name,
                benchmark.name,
                evaluation.results.total_questions,
                evaluation.results.correct_answers,
                evaluation.results.accuracy,
                execution_time,
                evaluation.results.error_count,
                evaluation.created_at.isoformat(),
                evaluation.completed_at.isoformat() if evaluation.completed_at else "",
            ]
        )

        return output.getvalue()

    def _export_to_json(self, evaluation: Any, benchmark: Any) -> str:
        """Export evaluation results to JSON format."""
        execution_time = 0.0
        if evaluation.started_at and evaluation.completed_at:
            execution_time = (
                evaluation.completed_at - evaluation.started_at
            ).total_seconds() / 60

        data = {
            "evaluation_id": str(evaluation.evaluation_id),
            "agent_config": {
                "agent_type": evaluation.agent_config.agent_type,
                "model_name": evaluation.agent_config.model_name,
                "model_parameters": evaluation.agent_config.model_parameters,
                "agent_parameters": evaluation.agent_config.agent_parameters,
            },
            "benchmark": {
                "id": str(benchmark.benchmark_id),
                "name": benchmark.name,
                "description": benchmark.description,
                "question_count": benchmark.question_count,
            },
            "results": {
                "total_questions": evaluation.results.total_questions,
                "correct_answers": evaluation.results.correct_answers,
                "accuracy": evaluation.results.accuracy,
                "execution_time_minutes": execution_time,
                "average_time_per_question": evaluation.results.average_execution_time,
                "error_count": evaluation.results.error_count,
            },
            "timestamps": {
                "created_at": evaluation.created_at.isoformat(),
                "started_at": (
                    evaluation.started_at.isoformat() if evaluation.started_at else None
                ),
                "completed_at": (
                    evaluation.completed_at.isoformat()
                    if evaluation.completed_at
                    else None
                ),
            },
            "status": evaluation.status,
        }

        return json.dumps(data, indent=2)

    def _evaluation_to_info(self, evaluation: Any, benchmark: Any) -> EvaluationInfo:
        """Convert evaluation entity to info DTO."""
        accuracy = None
        total_questions = None
        correct_answers = None

        if evaluation.results:
            accuracy = evaluation.results.accuracy
            total_questions = evaluation.results.total_questions
            correct_answers = evaluation.results.correct_answers

        return EvaluationInfo(
            evaluation_id=evaluation.evaluation_id,
            agent_type=evaluation.agent_config.agent_type,
            model_name=evaluation.agent_config.model_name,
            benchmark_name=benchmark.name,
            status=evaluation.status,
            accuracy=accuracy,
            created_at=evaluation.created_at,
            completed_at=evaluation.completed_at,
            total_questions=total_questions,
            correct_answers=correct_answers,
        )
