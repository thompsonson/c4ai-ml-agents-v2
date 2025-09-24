"""Evaluation orchestration service."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from dataclasses import replace
from datetime import datetime

# Type import to avoid circular dependencies
from typing import TYPE_CHECKING

from ...domain.entities.evaluation import Evaluation
from ...domain.entities.preprocessed_benchmark import PreprocessedBenchmark
from ...domain.repositories.evaluation_repository import EvaluationRepository
from ...domain.repositories.preprocessed_benchmark_repository import (
    PreprocessedBenchmarkRepository,
)
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
        benchmark_repository: PreprocessedBenchmarkRepository,
        reasoning_infrastructure_service: ReasoningInfrastructureService,
        domain_service_registry: dict[str, ReasoningAgentService],
    ) -> None:
        """Initialize the evaluation orchestrator.

        Args:
            evaluation_repository: Repository for evaluation persistence
            benchmark_repository: Repository for benchmark access
            reasoning_infrastructure_service: Infrastructure service for LLM calls
            domain_service_registry: Registry of domain reasoning services
        """
        self._evaluation_repo = evaluation_repository
        self._benchmark_repo = benchmark_repository
        self._reasoning_infrastructure = reasoning_infrastructure_service
        self._domain_services = domain_service_registry
        self._logger = logging.getLogger(__name__)

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
        started_at = datetime.now()
        running_evaluation = replace(
            evaluation,
            status="running",
            started_at=started_at,
        )
        self._evaluation_repo.update(running_evaluation)

        try:
            # Execute questions
            results = await self._execute_questions(
                running_evaluation, benchmark, progress_callback
            )

            # Complete evaluation
            completed_at = datetime.now()
            completed_evaluation = replace(
                running_evaluation,
                status="completed",
                completed_at=completed_at,
                results=results,
            )
            self._evaluation_repo.update(completed_evaluation)

            self._logger.info(
                "Evaluation completed successfully",
                extra={
                    "evaluation_id": str(evaluation_id),
                    "accuracy": results.accuracy,
                    "duration_minutes": (
                        results.average_execution_time * results.total_questions
                    )
                    / 60,
                },
            )

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

            failed_evaluation = replace(
                running_evaluation,
                status="failed",
                completed_at=datetime.now(),
                failure_reason=failure_reason,
            )
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

        if evaluation.status != "completed" or evaluation.results is None:
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

        return EvaluationSummary(
            evaluation_id=evaluation.evaluation_id,
            agent_type=evaluation.agent_config.agent_type,
            model_name=evaluation.agent_config.model_name,
            benchmark_name=benchmark.name,
            status=evaluation.status,
            total_questions=evaluation.results.total_questions,
            correct_answers=evaluation.results.correct_answers,
            accuracy=evaluation.results.accuracy,
            execution_time_minutes=execution_time,
            total_tokens=evaluation.results.total_tokens,
            average_time_per_question=evaluation.results.average_execution_time,
            error_count=evaluation.results.error_count,
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
        total_tokens = 0

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
                    if result.token_usage:
                        total_tokens += result.token_usage.total_tokens

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
            "average_tokens_per_question": (
                total_tokens / total_questions if total_questions > 0 else 0
            ),
            "success_rate": accuracy,
            "error_rate": error_count / total_questions if total_questions > 0 else 0,
        }

        return EvaluationResults(
            total_questions=total_questions,
            correct_answers=correct_count,
            accuracy=accuracy,
            average_execution_time=avg_execution_time,
            total_tokens=total_tokens,
            error_count=error_count,
            detailed_results=question_results,
            summary_statistics=summary_stats,
        )

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
