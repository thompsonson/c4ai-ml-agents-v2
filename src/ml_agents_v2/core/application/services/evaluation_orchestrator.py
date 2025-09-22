"""Evaluation orchestration service."""

from __future__ import annotations

import logging
import uuid
from dataclasses import replace
from datetime import datetime
from typing import Callable

from ...domain.entities.evaluation import Evaluation
from ...domain.entities.preprocessed_benchmark import PreprocessedBenchmark
from ...domain.repositories.evaluation_repository import EvaluationRepository
from ...domain.repositories.preprocessed_benchmark_repository import (
    PreprocessedBenchmarkRepository,
)
from ...domain.services.reasoning.reasoning_agent_factory import ReasoningAgentFactory
from ...domain.value_objects.agent_config import AgentConfig
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
        reasoning_agent_factory: ReasoningAgentFactory,
    ) -> None:
        """Initialize the evaluation orchestrator.

        Args:
            evaluation_repository: Repository for evaluation persistence
            benchmark_repository: Repository for benchmark access
            reasoning_agent_factory: Factory for creating reasoning agents
        """
        self._evaluation_repo = evaluation_repository
        self._benchmark_repo = benchmark_repository
        self._reasoning_factory = reasoning_agent_factory
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
        # Create reasoning agent
        reasoning_agent = self._reasoning_factory.create_service(
            evaluation.agent_config
        )

        questions = benchmark.get_questions()
        answers: list[Answer] = []
        errors: list[FailureReason] = []
        start_time = datetime.now()

        for i, question in enumerate(questions, 1):
            question_start = datetime.now()

            # Report progress
            if progress_callback:
                progress_info = ProgressInfo(
                    evaluation_id=evaluation.evaluation_id,
                    current_question=i,
                    total_questions=len(questions),
                    successful_answers=len(answers),
                    failed_questions=len(errors),
                    started_at=evaluation.started_at or start_time,
                    last_updated=datetime.now(),
                    current_question_text=(
                        question.text[:100] + "..."
                        if len(question.text) > 100
                        else question.text
                    ),
                )
                progress_callback(progress_info)

            try:
                # Process question with reasoning agent
                answer = await reasoning_agent.answer_question(
                    question, evaluation.agent_config
                )
                answers.append(answer)

                self._logger.debug(
                    "Question processed successfully",
                    extra={
                        "evaluation_id": str(evaluation.evaluation_id),
                        "question_id": question.id,
                        "execution_time": (
                            datetime.now() - question_start
                        ).total_seconds(),
                    },
                )

            except Exception as e:
                # Log error but continue execution
                error_reason = FailureReason(
                    category="unknown",
                    description=f"Question {question.id} processing failed",
                    technical_details=str(e),
                    occurred_at=datetime.now(),
                    recoverable=False,
                )
                errors.append(error_reason)

                self._logger.warning(
                    "Question processing failed",
                    extra={
                        "evaluation_id": str(evaluation.evaluation_id),
                        "question_id": question.id,
                        "error": str(e),
                    },
                )

        # Compile results
        total_time = (datetime.now() - start_time).total_seconds()

        # Create detailed results for each question
        from ...domain.value_objects.evaluation_results import QuestionResult

        detailed_results = []
        correct_answers = 0

        for i, question in enumerate(questions):
            if i < len(answers):
                answer = answers[i]
                is_correct = answer.extracted_answer == question.expected_answer
                if is_correct:
                    correct_answers += 1

                detailed_result = QuestionResult(
                    question_id=question.id,
                    question_text=question.text,
                    expected_answer=question.expected_answer,
                    actual_answer=answer.extracted_answer,
                    is_correct=is_correct,
                )
                detailed_results.append(detailed_result)

        return EvaluationResults(
            total_questions=len(questions),
            correct_answers=correct_answers,
            accuracy=(correct_answers / len(questions)) * 100 if questions else 0,
            average_execution_time=total_time / len(questions) if questions else 0,
            total_tokens=sum(answer.token_usage.total_tokens for answer in answers),
            error_count=len(errors),
            detailed_results=detailed_results,
            summary_statistics={},  # Empty for now
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
        if not self._reasoning_factory.is_agent_type_supported(agent_config.agent_type):
            available_types = self._reasoning_factory.get_supported_agent_types()
            errors.append(
                f"Unsupported agent type '{agent_config.agent_type}'. "
                f"Available: {available_types}"
            )

        # Additional validation can be added here
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
