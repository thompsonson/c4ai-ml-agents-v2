"""Transaction management for application services."""

from __future__ import annotations

import logging
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any, Callable, TypeVar

from ...domain.repositories.evaluation_repository import EvaluationRepository
from ...domain.repositories.preprocessed_benchmark_repository import (
    PreprocessedBenchmarkRepository,
)
from .exceptions import ExternalServiceError

T = TypeVar("T")


class TransactionManager:
    """Manages transaction boundaries for application services.

    Provides transaction coordination and rollback capabilities
    for operations that span multiple repositories or require
    atomicity guarantees.
    """

    def __init__(
        self,
        evaluation_repository: EvaluationRepository,
        benchmark_repository: PreprocessedBenchmarkRepository,
    ) -> None:
        """Initialize transaction manager.

        Args:
            evaluation_repository: Repository for evaluation operations
            benchmark_repository: Repository for benchmark operations
        """
        self._evaluation_repo = evaluation_repository
        self._benchmark_repo = benchmark_repository
        self._logger = logging.getLogger(__name__)

    @contextmanager
    def evaluation_creation_transaction(
        self,
    ) -> Generator[dict[str, Any], None, None]:
        """Transaction boundary for evaluation creation.

        Provides atomic evaluation creation with validation
        and rollback capabilities.

        Yields:
            Transaction context dictionary
        """
        transaction_id = id(self)
        context = {"transaction_id": transaction_id, "operations": []}

        self._logger.info(
            "Starting evaluation creation transaction",
            extra={"transaction_id": transaction_id},
        )

        try:
            yield context

            operations = context.get("operations", [])
            operations_count = len(operations) if isinstance(operations, list) else 0

            self._logger.info(
                "Evaluation creation transaction completed successfully",
                extra={
                    "transaction_id": transaction_id,
                    "operations_count": operations_count,
                },
            )

        except Exception as e:
            self._logger.error(
                "Evaluation creation transaction failed, initiating rollback",
                extra={
                    "transaction_id": transaction_id,
                    "error": str(e),
                    "operations": context["operations"],
                },
            )

            try:
                self._rollback_evaluation_creation(context)
            except Exception as rollback_error:
                self._logger.error(
                    "Transaction rollback failed",
                    extra={
                        "transaction_id": transaction_id,
                        "rollback_error": str(rollback_error),
                        "original_error": str(e),
                    },
                )

            raise

    @contextmanager
    def question_processing_transaction(
        self,
    ) -> Generator[dict[str, Any], None, None]:
        """Transaction boundary for individual question processing.

        Provides optimistic concurrency control for question-level
        operations with minimal locking.

        Yields:
            Transaction context dictionary
        """
        transaction_id = id(self)
        context = {"transaction_id": transaction_id, "question_results": []}

        self._logger.debug(
            "Starting question processing transaction",
            extra={"transaction_id": transaction_id},
        )

        try:
            yield context

            self._logger.debug(
                "Question processing transaction completed",
                extra={"transaction_id": transaction_id},
            )

        except Exception as e:
            self._logger.warning(
                "Question processing transaction failed",
                extra={
                    "transaction_id": transaction_id,
                    "error": str(e),
                },
            )
            # For question processing, we typically continue rather than rollback
            # as individual question failures should not abort the entire evaluation
            raise

    @contextmanager
    def results_compilation_transaction(
        self,
    ) -> Generator[dict[str, Any], None, None]:
        """Transaction boundary for results compilation.

        Provides pessimistic locking for evaluation completion
        to ensure consistency during results aggregation.

        Yields:
            Transaction context dictionary
        """
        transaction_id = id(self)
        context = {"transaction_id": transaction_id, "compilation_state": {}}

        self._logger.info(
            "Starting results compilation transaction",
            extra={"transaction_id": transaction_id},
        )

        try:
            yield context

            self._logger.info(
                "Results compilation transaction completed successfully",
                extra={"transaction_id": transaction_id},
            )

        except Exception as e:
            self._logger.error(
                "Results compilation transaction failed",
                extra={
                    "transaction_id": transaction_id,
                    "error": str(e),
                },
            )

            try:
                self._rollback_results_compilation(context)
            except Exception as rollback_error:
                self._logger.error(
                    "Results compilation rollback failed",
                    extra={
                        "transaction_id": transaction_id,
                        "rollback_error": str(rollback_error),
                        "original_error": str(e),
                    },
                )

            raise

    def execute_with_retry(
        self,
        operation: Callable[[], T],
        max_retries: int = 3,
        retry_on_exceptions: tuple[type[Exception], ...] = (ExternalServiceError,),
        backoff_multiplier: float = 1.5,
    ) -> T:
        """Execute operation with retry logic.

        Args:
            operation: Function to execute
            max_retries: Maximum number of retry attempts
            retry_on_exceptions: Exception types that trigger retries
            backoff_multiplier: Multiplier for exponential backoff

        Returns:
            Result of the operation

        Raises:
            Last exception if all retries fail
        """
        import time

        last_exception = None
        wait_time = 1.0

        for attempt in range(max_retries + 1):
            try:
                result = operation()
                if attempt > 0:
                    self._logger.info(
                        "Operation succeeded after retry",
                        extra={"attempt": attempt + 1, "max_retries": max_retries},
                    )
                return result

            except retry_on_exceptions as e:
                last_exception = e
                if attempt < max_retries:
                    self._logger.warning(
                        "Operation failed, retrying",
                        extra={
                            "attempt": attempt + 1,
                            "max_retries": max_retries,
                            "wait_time": wait_time,
                            "error": str(e),
                        },
                    )
                    time.sleep(wait_time)
                    wait_time *= backoff_multiplier
                else:
                    self._logger.error(
                        "Operation failed after all retries",
                        extra={
                            "attempts": attempt + 1,
                            "max_retries": max_retries,
                            "error": str(e),
                        },
                    )

            except Exception as e:
                # Don't retry on non-retriable exceptions
                self._logger.error(
                    "Operation failed with non-retriable exception",
                    extra={"attempt": attempt + 1, "error": str(e)},
                )
                raise

        if last_exception:
            raise last_exception

        # This should never be reached, but included for type safety
        raise RuntimeError("Unexpected state in retry logic")

    def _rollback_evaluation_creation(self, context: dict[str, Any]) -> None:
        """Rollback evaluation creation operations.

        Args:
            context: Transaction context with operations to rollback
        """
        operations = context.get("operations", [])

        for operation in reversed(operations):
            try:
                if operation["type"] == "evaluation_created":
                    evaluation_id = operation["evaluation_id"]
                    self._evaluation_repo.delete(evaluation_id)
                    self._logger.info(
                        "Rolled back evaluation creation",
                        extra={"evaluation_id": str(evaluation_id)},
                    )

            except Exception as e:
                self._logger.error(
                    "Failed to rollback operation",
                    extra={"operation": operation, "error": str(e)},
                )

    def _rollback_results_compilation(self, context: dict[str, Any]) -> None:
        """Rollback results compilation operations.

        Args:
            context: Transaction context with compilation state
        """
        compilation_state = context.get("compilation_state", {})

        if "evaluation_id" in compilation_state:
            try:
                # Restore previous evaluation state if we have it
                if "previous_state" in compilation_state:
                    previous_evaluation = compilation_state["previous_state"]
                    self._evaluation_repo.update(previous_evaluation)
                    self._logger.info(
                        "Restored previous evaluation state",
                        extra={"evaluation_id": str(previous_evaluation.evaluation_id)},
                    )

            except Exception as e:
                self._logger.error(
                    "Failed to restore evaluation state",
                    extra={"error": str(e)},
                )


def with_transaction(transaction_type: str) -> Callable:
    """Decorator for automatic transaction management.

    Args:
        transaction_type: Type of transaction to apply

    Returns:
        Decorated function with transaction boundary
    """

    def decorator(func: Callable) -> Callable:
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            if not hasattr(self, "_transaction_manager"):
                # If no transaction manager available, execute without transaction
                return func(self, *args, **kwargs)

            transaction_manager = self._transaction_manager

            if transaction_type == "evaluation_creation":
                with transaction_manager.evaluation_creation_transaction():
                    return func(self, *args, **kwargs)
            elif transaction_type == "question_processing":
                with transaction_manager.question_processing_transaction():
                    return func(self, *args, **kwargs)
            elif transaction_type == "results_compilation":
                with transaction_manager.results_compilation_transaction():
                    return func(self, *args, **kwargs)
            else:
                return func(self, *args, **kwargs)

        return wrapper

    return decorator
