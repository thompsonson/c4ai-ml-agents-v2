"""Evaluation orchestration service."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import datetime

# Type import to avoid circular dependencies
from typing import TYPE_CHECKING

import structlog

from ...domain.entities.evaluation import Evaluation
from ...domain.entities.evaluation_question_result import EvaluationQuestionResult
from ...domain.entities.preprocessed_benchmark import PreprocessedBenchmark
from ...domain.repositories.evaluation_question_result_repository import (
    EvaluationQuestionResultRepository,
)
from ...domain.repositories.evaluation_repository import EvaluationRepository
from ...domain.repositories.preprocessed_benchmark_repository import (
    PreprocessedBenchmarkRepository,
)
from ...domain.services.export_service import ExportService
from ...domain.services.reasoning.reasoning_agent_service import ReasoningAgentService
from ...domain.value_objects.agent_config import AgentConfig

if TYPE_CHECKING:
    from ....infrastructure.reasoning_service import ReasoningInfrastructureService
from ...domain.value_objects.answer import Answer
from ...domain.value_objects.evaluation_results import EvaluationResults
from ...domain.value_objects.failure_reason import FailureReason
from ..dto.evaluation_info import EvaluationInfo
from ..dto.evaluation_summary import EvaluationSummary
from ..dto.progress_info import ProgressInfo
from ..dto.validation_result import ValidationResult
from .exceptions import (
    BenchmarkNotFoundError,
    EvaluationExecutionError,
    EvaluationNotFoundError,
    InvalidEvaluationStateError,
)


class EvaluationOrchestrator:
    """Orchestrates evaluation lifecycle and execution.

    Primary application service that coordinates evaluation creation,
    execution, and status management while maintaining transaction
    boundaries and coordinating between domain and infrastructure layers.
    """

    def __init__(
        self,
        evaluation_repository: EvaluationRepository,
        evaluation_question_result_repository: EvaluationQuestionResultRepository,
        benchmark_repository: PreprocessedBenchmarkRepository,
        reasoning_infrastructure_service: ReasoningInfrastructureService,
        domain_service_registry: dict[str, ReasoningAgentService],
        export_service: ExportService,
    ) -> None:
        """Initialize the evaluation orchestrator.

        Args:
            evaluation_repository: Repository for evaluation persistence
            evaluation_question_result_repository: Repository for individual question results
            benchmark_repository: Repository for benchmark access
            reasoning_infrastructure_service: Infrastructure service for LLM calls
            domain_service_registry: Registry of domain reasoning services
            export_service: Service for exporting evaluation results
        """
        self._evaluation_repo = evaluation_repository
        self._question_result_repo = evaluation_question_result_repository
        self._benchmark_repo = benchmark_repository
        self._reasoning_infrastructure = reasoning_infrastructure_service
        self._domain_services = domain_service_registry
        self._export_service = export_service
        self._logger = structlog.get_logger(__name__)

    def create_evaluation(
        self,
        agent_config: AgentConfig,
        benchmark_name: str,
    ) -> uuid.UUID:
        """Create a new evaluation in pending state.

        Args:
            agent_config: Configuration for the reasoning agent
            benchmark_name: Name of the benchmark to evaluate against

        Returns:
            ID of the created evaluation

        Raises:
            BenchmarkNotFoundError: If benchmark doesn't exist
            InvalidConfigurationError: If agent config is invalid
        """
        self._logger.info(
            "Creating evaluation",
            extra={
                "agent_type": agent_config.agent_type,
                "model": agent_config.model_name,
                "benchmark": benchmark_name,
            },
        )

        # Validate benchmark exists
        try:
            benchmark = self._benchmark_repo.get_by_name(benchmark_name)
        except Exception as e:
            from ...domain.repositories.exceptions import EntityNotFoundError

            if isinstance(e, EntityNotFoundError):
                raise BenchmarkNotFoundError(
                    f"Benchmark '{benchmark_name}' not found"
                ) from e
            else:
                # Other repository errors (connection, etc.)
                raise BenchmarkNotFoundError(
                    f"Failed to retrieve benchmark '{benchmark_name}': {e}"
                ) from e

        # Validate agent configuration
        validation_result = self._validate_agent_config(agent_config)
        if not validation_result.is_valid:
            from ...domain.services.reasoning.exceptions import (
                InvalidConfigurationError,
            )

            raise InvalidConfigurationError(
                f"Invalid agent configuration: {', '.join(validation_result.errors)}",
                agent_config.agent_type,
            )

        # Create evaluation entity
        evaluation_id = uuid.uuid4()
        evaluation = Evaluation(
            evaluation_id=evaluation_id,
            agent_config=agent_config,
            preprocessed_benchmark_id=benchmark.benchmark_id,
            status="pending",
            created_at=datetime.now(),
            started_at=None,
            completed_at=None,
            results=None,
            failure_reason=None,
        )

        # Persist evaluation
        self._evaluation_repo.save(evaluation)

        self._logger.info(
            "Evaluation created successfully",
            extra={"evaluation_id": str(evaluation_id)},
        )

        return evaluation_id

    async def execute_evaluation(
        self,
        evaluation_id: uuid.UUID,
        progress_callback: Callable[[ProgressInfo], None] | None = None,
    ) -> None:
        """Execute an evaluation against its benchmark.

        Args:
            evaluation_id: ID of the evaluation to execute
            progress_callback: Optional callback for progress updates

        Raises:
            EvaluationNotFoundError: If evaluation doesn't exist
            InvalidEvaluationStateError: If evaluation cannot be executed
            EvaluationExecutionError: If execution fails
        """
        self._logger.info(
            "Starting evaluation execution",
            extra={"evaluation_id": str(evaluation_id)},
        )

        # Get evaluation and validate state
        try:
            evaluation = self._evaluation_repo.get_by_id(evaluation_id)
        except Exception as e:
            raise EvaluationNotFoundError(
                f"Evaluation {evaluation_id} not found"
            ) from e

        if evaluation.status not in ["pending", "interrupted"]:
            raise InvalidEvaluationStateError(
                f"Cannot execute evaluation in '{evaluation.status}' state"
            )

        # Get benchmark
        try:
            benchmark = self._benchmark_repo.get_by_id(
                evaluation.preprocessed_benchmark_id
            )
        except Exception as e:
            raise EvaluationExecutionError(f"Failed to load benchmark: {e}") from e

        # Transition to running state
        running_evaluation = evaluation.start_execution()
        self._evaluation_repo.update(running_evaluation)

        try:
            # Execute questions with incremental persistence (Phase 8 pattern)
            await self._execute_questions_incrementally(
                running_evaluation, benchmark, progress_callback
            )

            # Complete evaluation (no results parameter - computed from questions)
            completed_evaluation = running_evaluation.complete()
            self._evaluation_repo.update(completed_evaluation)

            # Compute final results for logging from saved question results
            question_results = self._question_result_repo.get_by_evaluation_id(
                evaluation_id
            )
            computed_results = EvaluationResults.from_question_results(question_results)

            self._logger.info(
                "Evaluation completed successfully",
                extra={
                    "evaluation_id": str(evaluation_id),
                    "accuracy": computed_results.accuracy,
                    "total_questions": computed_results.total_questions,
                    "correct_answers": computed_results.correct_answers,
                },
            )

        except KeyboardInterrupt:
            # Handle graceful interruption (Ctrl+C)
            self._logger.info(
                "Evaluation interrupted by user",
                extra={"evaluation_id": str(evaluation_id)},
            )

            interrupted_evaluation = running_evaluation.interrupt()
            self._evaluation_repo.update(interrupted_evaluation)

            # Log partial progress
            question_results = self._question_result_repo.get_by_evaluation_id(
                evaluation_id
            )
            self._logger.info(
                f"Evaluation interrupted: {len(question_results)}/{len(benchmark.questions)} questions completed"
            )

            raise  # Re-raise to propagate interruption

        except Exception as e:
            # Handle execution failure
            self._logger.error(
                "Evaluation execution failed",
                extra={"evaluation_id": str(evaluation_id), "error": str(e)},
            )

            failure_reason = FailureReason(
                category="unknown",
                description="Evaluation execution failed",
                technical_details=str(e),
                occurred_at=datetime.now(),
                recoverable=False,
            )

            failed_evaluation = running_evaluation.fail_with_reason(failure_reason)
            self._evaluation_repo.update(failed_evaluation)

            raise EvaluationExecutionError(f"Execution failed: {e}") from e

    def get_evaluation_status(self, evaluation_id: uuid.UUID) -> str:
        """Get current evaluation status.

        Args:
            evaluation_id: ID of the evaluation

        Returns:
            Current status string

        Raises:
            EvaluationNotFoundError: If evaluation doesn't exist
        """
        try:
            evaluation = self._evaluation_repo.get_by_id(evaluation_id)
            return evaluation.status
        except Exception as e:
            from ...domain.repositories.exceptions import EntityNotFoundError

            if isinstance(e, EntityNotFoundError):
                raise EvaluationNotFoundError(
                    f"Evaluation {evaluation_id} not found"
                ) from e
            else:
                # Other repository errors
                raise EvaluationNotFoundError(
                    f"Failed to retrieve evaluation {evaluation_id}: {e}"
                ) from e

    def get_evaluation_results(self, evaluation_id: uuid.UUID) -> EvaluationSummary:
        """Get detailed evaluation results.

        Args:
            evaluation_id: ID of the evaluation

        Returns:
            Detailed evaluation summary

        Raises:
            EvaluationNotFoundError: If evaluation doesn't exist
            InvalidEvaluationStateError: If evaluation not completed
        """
        try:
            evaluation = self._evaluation_repo.get_by_id(evaluation_id)
        except Exception as e:
            raise EvaluationNotFoundError(
                f"Evaluation {evaluation_id} not found"
            ) from e

        if evaluation.status != "completed":
            raise InvalidEvaluationStateError(
                f"Evaluation not completed (status: {evaluation.status})"
            )

        # Get benchmark for name
        benchmark = self._benchmark_repo.get_by_id(evaluation.preprocessed_benchmark_id)

        # Calculate execution time
        if evaluation.started_at and evaluation.completed_at:
            execution_time = (
                evaluation.completed_at - evaluation.started_at
            ).total_seconds() / 60
        else:
            execution_time = 0.0

        # Get results - either from stored results or compute from question results
        if evaluation.results is not None:
            # Use stored results
            results = evaluation.results
        else:
            # Compute results from individual question results (Phase 8 pattern)
            question_results = self._question_result_repo.get_by_evaluation_id(
                evaluation.evaluation_id
            )
            if not question_results:
                raise InvalidEvaluationStateError(
                    f"Evaluation {evaluation.evaluation_id} has no question results"
                )
            results = EvaluationResults.from_question_results(question_results)

        return EvaluationSummary(
            evaluation_id=evaluation.evaluation_id,
            agent_type=evaluation.agent_config.agent_type,
            model_name=evaluation.agent_config.model_name,
            benchmark_name=benchmark.name,
            status=evaluation.status,
            total_questions=results.total_questions,
            correct_answers=results.correct_answers,
            accuracy=results.accuracy,
            execution_time_minutes=execution_time,
            average_time_per_question=results.average_execution_time,
            error_count=results.error_count,
            created_at=evaluation.created_at,
            completed_at=evaluation.completed_at,
        )

    def list_evaluations(
        self,
        status_filter: str | None = None,
        benchmark_name_filter: str | None = None,
        limit: int | None = None,
    ) -> list[EvaluationInfo]:
        """List evaluations with optional filtering.

        Args:
            status_filter: Optional status to filter by
            benchmark_name_filter: Optional benchmark name to filter by
            limit: Optional limit on number of results

        Returns:
            List of evaluation information objects
        """
        # Get evaluations based on filters
        if status_filter:
            evaluations = self._evaluation_repo.list_by_status(status_filter)
        else:
            evaluations = self._evaluation_repo.list_all(limit)

        # Convert to DTOs with benchmark names
        evaluation_infos = []
        for evaluation in evaluations:
            try:
                benchmark = self._benchmark_repo.get_by_id(
                    evaluation.preprocessed_benchmark_id
                )

                # Apply benchmark name filter if specified
                if benchmark_name_filter and benchmark.name != benchmark_name_filter:
                    continue

                evaluation_info = self._evaluation_to_info(evaluation, benchmark)
                evaluation_infos.append(evaluation_info)

            except Exception as e:
                self._logger.warning(
                    "Failed to load benchmark for evaluation",
                    extra={
                        "evaluation_id": str(evaluation.evaluation_id),
                        "benchmark_id": str(evaluation.preprocessed_benchmark_id),
                        "error": str(e),
                    },
                )
                continue

        return evaluation_infos

    async def _execute_questions(
        self,
        evaluation: Evaluation,
        benchmark: PreprocessedBenchmark,
        progress_callback: Callable[[ProgressInfo], None] | None,
    ) -> EvaluationResults:
        """Execute all questions in the benchmark.

        Args:
            evaluation: The evaluation being executed
            benchmark: The benchmark to process
            progress_callback: Optional progress callback

        Returns:
            Compiled evaluation results
        """
        # Get domain service for the agent type
        domain_service = self._domain_services[evaluation.agent_config.agent_type]

        questions = benchmark.get_questions()
        total_questions = len(questions)
        results = []
        correct_count = 0
        error_count = 0
        total_execution_time = 0.0

        for i, question in enumerate(questions):
            try:
                # Execute reasoning using infrastructure service
                result = await self._reasoning_infrastructure.execute_reasoning(
                    domain_service, question, evaluation.agent_config
                )

                if isinstance(result, Answer):
                    # Check if answer is correct
                    is_correct = (
                        result.extracted_answer.strip().lower()
                        == question.expected_answer.strip().lower()
                    )
                    if is_correct:
                        correct_count += 1

                    # Accumulate metrics
                    total_execution_time += result.execution_time

                    results.append(
                        {
                            "question_id": question.id,
                            "extracted_answer": result.extracted_answer,
                            "is_correct": is_correct,
                            "execution_time": result.execution_time,
                            "reasoning_trace": result.reasoning_trace,
                        }
                    )

                else:  # FailureReason
                    error_count += 1
                    results.append(
                        {
                            "question_id": question.id,
                            "error": str(result.description),
                            "is_correct": False,
                            "execution_time": 0.0,
                        }
                    )

                # Update progress
                if progress_callback:
                    from datetime import datetime

                    now = datetime.now()
                    progress = ProgressInfo(
                        evaluation_id=evaluation.evaluation_id,
                        current_question=i + 1,
                        total_questions=total_questions,
                        successful_answers=correct_count,
                        failed_questions=error_count,
                        started_at=evaluation.started_at or now,
                        last_updated=now,
                    )
                    progress_callback(progress)

            except Exception as e:
                error_count += 1
                self._logger.error(
                    "Question execution failed",
                    extra={"question_id": question.id, "error": str(e)},
                )

        # Calculate final metrics
        accuracy = correct_count / total_questions if total_questions > 0 else 0.0
        avg_execution_time = (
            total_execution_time / total_questions if total_questions > 0 else 0.0
        )

        # Convert dict results to QuestionResult objects
        from ...domain.value_objects.evaluation_results import QuestionResult

        question_results = []
        for result_dict in results:
            if "error" not in result_dict:
                # Find the corresponding question for additional details
                question = next(
                    q for q in questions if q.id == result_dict["question_id"]
                )
                question_results.append(
                    QuestionResult(
                        question_id=str(result_dict["question_id"]),
                        question_text=question.text,
                        expected_answer=question.expected_answer,
                        actual_answer=str(result_dict["extracted_answer"]),
                        is_correct=bool(result_dict["is_correct"]),
                    )
                )

        # Create summary statistics
        summary_stats = {
            "total_runtime_minutes": total_execution_time / 60,
            "success_rate": accuracy,
            "error_rate": error_count / total_questions if total_questions > 0 else 0,
        }

        return EvaluationResults(
            total_questions=total_questions,
            correct_answers=correct_count,
            accuracy=accuracy,
            average_execution_time=avg_execution_time,
            error_count=error_count,
            detailed_results=question_results,
            summary_statistics=summary_stats,
        )

    async def _execute_questions_incrementally(
        self,
        evaluation: Evaluation,
        benchmark: PreprocessedBenchmark,
        progress_callback: Callable[[ProgressInfo], None] | None,
    ) -> None:
        """Execute questions with incremental persistence (Phase 8 pattern).

        Each question result is saved immediately upon completion, enabling
        graceful interruption and resume capability.

        Args:
            evaluation: The evaluation being executed
            benchmark: The benchmark to process
            progress_callback: Optional progress callback
        """
        # Get domain service for the agent type
        domain_service = self._domain_services[evaluation.agent_config.agent_type]

        questions = benchmark.get_questions()
        total_questions = len(questions)

        for _i, question in enumerate(questions):
            # Check if already completed (for resume capability)
            if self._question_result_repo.exists(evaluation.evaluation_id, question.id):
                self._logger.debug(f"Skipping already completed question {question.id}")
                continue

            try:
                from datetime import datetime as dt

                start_time = dt.now()

                # Execute reasoning using infrastructure service
                result = await self._reasoning_infrastructure.execute_reasoning(
                    domain_service, question, evaluation.agent_config
                )

                execution_time = (dt.now() - start_time).total_seconds()

                if isinstance(result, Answer):
                    # Check if answer is correct
                    is_correct = (
                        result.extracted_answer.strip().lower()
                        == question.expected_answer.strip().lower()
                    )

                    # Create successful question result
                    question_result = EvaluationQuestionResult.create_successful(
                        evaluation_id=evaluation.evaluation_id,
                        question_id=question.id,
                        question_text=question.text,
                        expected_answer=question.expected_answer,
                        actual_answer=result.extracted_answer,
                        is_correct=is_correct,
                        execution_time=execution_time,
                        reasoning_trace=result.reasoning_trace,
                    )

                else:  # FailureReason
                    # Log failure with technical details for debugging
                    self._logger.warning(
                        "Question processing failed",
                        question_id=question.id,
                        error_category=result.category,
                        error_description=result.description,
                        technical_details=result.technical_details,
                        recoverable=result.recoverable,
                    )

                    # Create failed question result
                    question_result = EvaluationQuestionResult.create_failed(
                        evaluation_id=evaluation.evaluation_id,
                        question_id=question.id,
                        question_text=question.text,
                        expected_answer=question.expected_answer,
                        error_message=result.description,
                        execution_time=execution_time,
                        technical_details=result.technical_details,
                    )

                # Save immediately (incremental persistence)
                self._question_result_repo.save(question_result)

                # Update progress using real saved data
                if progress_callback:
                    domain_progress = self._question_result_repo.get_progress(
                        evaluation.evaluation_id, total_questions
                    )
                    # Convert to application DTO
                    # Parse latest_processed_at if it's a string, fallback to created_at
                    from datetime import datetime

                    from ..dto.progress_info import ProgressInfo

                    last_updated = evaluation.created_at
                    if domain_progress.latest_processed_at:
                        try:
                            last_updated = datetime.fromisoformat(
                                domain_progress.latest_processed_at
                            )
                        except ValueError:
                            last_updated = evaluation.created_at

                    progress_info = ProgressInfo(
                        evaluation_id=domain_progress.evaluation_id,
                        current_question=domain_progress.completed_questions,
                        total_questions=domain_progress.total_questions,
                        successful_answers=domain_progress.successful_questions,
                        failed_questions=domain_progress.failed_questions,
                        started_at=evaluation.started_at or evaluation.created_at,
                        last_updated=last_updated,
                    )
                    progress_callback(progress_info)

            except Exception as e:
                # Handle unexpected errors during question processing
                self._logger.error(
                    "Question execution failed",
                    extra={
                        "question_id": question.id,
                        "error": str(e),
                        "technical_details": f"{type(e).__name__}: {str(e)}",
                    },
                )

                # Save failed question result
                execution_time = (dt.now() - start_time).total_seconds()
                failed_question_result = EvaluationQuestionResult.create_failed(
                    evaluation_id=evaluation.evaluation_id,
                    question_id=question.id,
                    question_text=question.text,
                    expected_answer=question.expected_answer,
                    error_message=f"Unexpected error: {str(e)}",
                    execution_time=execution_time,
                    technical_details=f"{type(e).__name__}: {str(e)}",
                )
                self._question_result_repo.save(failed_question_result)

    def _validate_agent_config(self, agent_config: AgentConfig) -> ValidationResult:
        """Validate agent configuration.

        Args:
            agent_config: Configuration to validate

        Returns:
            Validation result
        """
        errors = []

        # Check if agent type is supported
        if agent_config.agent_type not in self._domain_services:
            available_types = list(self._domain_services.keys())
            errors.append(
                f"Unsupported agent type '{agent_config.agent_type}'. "
                f"Available: {available_types}"
            )
        else:
            # Use domain service for validation
            domain_service = self._domain_services[agent_config.agent_type]
            domain_validation = domain_service.validate_config(agent_config)
            if not domain_validation.is_valid:
                errors.extend(domain_validation.errors)

        # Additional validation
        if agent_config.model_parameters.get("temperature", 1.0) < 0:
            errors.append("Temperature must be non-negative")

        if agent_config.model_parameters.get("max_tokens", 1000) <= 0:
            errors.append("Max tokens must be positive")

        if errors:
            return ValidationResult.failure(errors)
        return ValidationResult.success()

    def _evaluation_to_info(
        self, evaluation: Evaluation, benchmark: PreprocessedBenchmark
    ) -> EvaluationInfo:
        """Convert evaluation entity to info DTO.

        Args:
            evaluation: Domain evaluation entity
            benchmark: Associated benchmark entity

        Returns:
            Evaluation info DTO
        """
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

    def get_evaluation_progress(self, evaluation_id: uuid.UUID) -> ProgressInfo:
        """Get current progress for an evaluation.

        Args:
            evaluation_id: ID of the evaluation

        Returns:
            Progress information computed from saved question results

        Raises:
            EvaluationNotFoundError: If evaluation doesn't exist
        """
        # Verify evaluation exists and get benchmark info
        try:
            evaluation = self._evaluation_repo.get_by_id(evaluation_id)
            benchmark = self._benchmark_repo.get_by_id(
                evaluation.preprocessed_benchmark_id
            )
        except Exception as e:
            raise EvaluationNotFoundError(
                f"Evaluation {evaluation_id} not found"
            ) from e

        # Get progress from repository and convert to application DTO
        domain_progress = self._question_result_repo.get_progress(
            evaluation_id, len(benchmark.questions)
        )

        # Convert domain ProgressInfo to application ProgressInfo
        from datetime import datetime

        from ..dto.progress_info import ProgressInfo

        # Parse latest_processed_at if it's a string, fallback to created_at
        last_updated = evaluation.created_at
        if domain_progress.latest_processed_at:
            try:
                last_updated = datetime.fromisoformat(
                    domain_progress.latest_processed_at
                )
            except ValueError:
                last_updated = evaluation.created_at

        return ProgressInfo(
            evaluation_id=domain_progress.evaluation_id,
            current_question=domain_progress.completed_questions,
            total_questions=domain_progress.total_questions,
            successful_answers=domain_progress.successful_questions,
            failed_questions=domain_progress.failed_questions,
            started_at=evaluation.started_at or evaluation.created_at,
            last_updated=last_updated,
        )

    def get_evaluation_info(self, evaluation_id: uuid.UUID) -> EvaluationInfo:
        """Get evaluation information for a single evaluation.

        Phase 8 pattern: For evaluations with question results, compute accuracy
        and question counts from saved question records rather than stored results.

        Args:
            evaluation_id: ID of the evaluation

        Returns:
            Evaluation information DTO

        Raises:
            EvaluationNotFoundError: If evaluation doesn't exist
        """
        try:
            evaluation = self._evaluation_repo.get_by_id(evaluation_id)
            benchmark = self._benchmark_repo.get_by_id(
                evaluation.preprocessed_benchmark_id
            )
        except Exception as e:
            from ...domain.repositories.exceptions import EntityNotFoundError

            if isinstance(e, EntityNotFoundError):
                raise EvaluationNotFoundError(
                    f"Evaluation {evaluation_id} not found"
                ) from e
            else:
                raise EvaluationNotFoundError(
                    f"Failed to retrieve evaluation {evaluation_id}: {e}"
                ) from e

        # Phase 8: For evaluations with question results, compute from saved data
        # Check if we have question results (Phase 8 pattern)
        question_results = self._question_result_repo.get_by_evaluation_id(
            evaluation_id
        )

        if question_results:
            # Use Phase 8 pattern: compute from individual question results
            computed_results = EvaluationResults.from_question_results(question_results)

            # Create updated evaluation info with computed values
            return EvaluationInfo(
                evaluation_id=evaluation.evaluation_id,
                agent_type=evaluation.agent_config.agent_type,
                model_name=evaluation.agent_config.model_name,
                benchmark_name=benchmark.name,
                status=evaluation.status,
                accuracy=computed_results.accuracy,
                created_at=evaluation.created_at,
                completed_at=evaluation.completed_at,
                total_questions=computed_results.total_questions,
                correct_answers=computed_results.correct_answers,
            )
        else:
            # Fallback to existing pattern for backward compatibility
            return self._evaluation_to_info(evaluation, benchmark)

    def export_evaluation_results(
        self, evaluation_id: uuid.UUID, export_format: str, output_path: str
    ) -> None:
        """Export evaluation results to specified format and location.

        Args:
            evaluation_id: ID of the evaluation to export
            export_format: Format for export (currently supports 'csv')
            output_path: Path where the export file should be written

        Raises:
            EvaluationNotFoundError: If evaluation doesn't exist
            InvalidExportDataError: If evaluation has no results to export
            ExportFormatError: If export_format is not supported
            ExportFileError: If file cannot be written
        """
        self._logger.info(
            "Exporting evaluation results",
            extra={
                "evaluation_id": str(evaluation_id),
                "format": export_format,
                "output_path": output_path,
            },
        )

        # Validate evaluation exists
        try:
            evaluation = self._evaluation_repo.get_by_id(evaluation_id)
            self._logger.debug(
                f"Found evaluation {evaluation_id} with status: {evaluation.status}"
            )
        except Exception as e:
            raise EvaluationNotFoundError(
                f"Evaluation {evaluation_id} not found"
            ) from e

        # Get question results for this evaluation
        question_results = self._question_result_repo.get_by_evaluation_id(
            evaluation_id
        )

        if not question_results:
            raise EvaluationNotFoundError(
                f"No question results found for evaluation {evaluation_id}. "
                "The evaluation may not have been executed yet."
            )

        # Delegate to appropriate export service method based on format
        if export_format.lower() == "csv":
            self._export_service.export_to_csv(question_results, output_path)
        else:
            from ...domain.services.export_exceptions import ExportFormatError

            raise ExportFormatError(export_format, ["csv"])

        self._logger.info(
            "Successfully exported evaluation results",
            extra={
                "evaluation_id": str(evaluation_id),
                "format": export_format,
                "output_path": output_path,
                "question_count": len(question_results),
            },
        )
