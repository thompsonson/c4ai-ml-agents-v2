"""Error mapping from infrastructure to domain failures."""

from __future__ import annotations

import logging
from typing import Any

from ...domain.value_objects.failure_reason import FailureReason
from .exceptions import (
    BenchmarkNotFoundError,
    EvaluationExecutionError,
    EvaluationNotFoundError,
    ExternalServiceError,
    ValidationError,
)


class ApplicationErrorMapper:
    """Maps infrastructure errors to domain failure reasons and application exceptions.

    Provides centralized error handling and mapping logic to convert
    low-level infrastructure errors into meaningful domain failures
    and appropriate application-level exceptions.
    """

    def __init__(self) -> None:
        """Initialize the error mapper."""
        self._logger = logging.getLogger(__name__)

    def map_openrouter_error(self, error: Exception) -> FailureReason:
        """Map OpenRouter API errors to domain failure reasons.

        Args:
            error: Exception from OpenRouter client

        Returns:
            Appropriate FailureReason value object
        """
        error_str = str(error).lower()
        error_type = type(error).__name__

        self._logger.debug(
            "Mapping OpenRouter error",
            extra={"error_type": error_type, "error_message": str(error)},
        )

        from datetime import datetime

        # Map specific OpenAI/OpenRouter exceptions
        if "ratelimiterror" in error_type.lower():
            return FailureReason(
                category="rate_limit_exceeded",
                description="API rate limit exceeded",
                technical_details=str(error),
                occurred_at=datetime.now(),
                recoverable=True,
            )

        if "timeouterror" in error_type.lower() or "timeout" in error_str:
            return FailureReason(
                category="network_timeout",
                description="Request timed out",
                technical_details=str(error),
                occurred_at=datetime.now(),
                recoverable=True,
            )

        if "authenticationerror" in error_type.lower() or "401" in error_str:
            return FailureReason(
                category="authentication_error",
                description="API authentication failed",
                technical_details=str(error),
                occurred_at=datetime.now(),
                recoverable=False,
            )

        # Check for specific HTTP status codes in error message
        if "402" in error_str or "insufficient" in error_str:
            return FailureReason(
                category="credit_limit_exceeded",
                description="Insufficient API credits",
                technical_details=str(error),
                occurred_at=datetime.now(),
                recoverable=False,
            )

        if "400" in error_str or "bad request" in error_str:
            return FailureReason(
                category="parsing_error",
                description="Invalid request format",
                technical_details=str(error),
                occurred_at=datetime.now(),
                recoverable=False,
            )

        if "content policy" in error_str or "guardrail" in error_str:
            return FailureReason(
                category="content_guardrail",
                description="Content policy violation",
                technical_details=str(error),
                occurred_at=datetime.now(),
                recoverable=False,
            )

        if "refused" in error_str or "declined" in error_str:
            return FailureReason(
                category="model_refusal",
                description="Model refused to answer",
                technical_details=str(error),
                occurred_at=datetime.now(),
                recoverable=False,
            )

        if "token" in error_str and ("limit" in error_str or "exceeded" in error_str):
            return FailureReason(
                category="token_limit_exceeded",
                description="Token limit exceeded",
                technical_details=str(error),
                occurred_at=datetime.now(),
                recoverable=False,
            )

        # Default to unknown failure
        return FailureReason(
            category="unknown",
            description="Unexpected OpenRouter error",
            technical_details=str(error),
            occurred_at=datetime.now(),
            recoverable=False,
        )

    def map_repository_error(self, error: Exception, operation: str) -> Exception:
        """Map repository errors to appropriate application exceptions.

        Args:
            error: Exception from repository layer
            operation: Description of the operation that failed

        Returns:
            Appropriate application-level exception
        """
        error_str = str(error).lower()
        error_type = type(error).__name__

        self._logger.debug(
            "Mapping repository error",
            extra={
                "error_type": error_type,
                "operation": operation,
                "error_message": str(error),
            },
        )

        # Map specific repository exceptions
        if "notfound" in error_type.lower() or "not found" in error_str:
            if "evaluation" in operation.lower():
                return EvaluationNotFoundError(
                    f"Evaluation not found during {operation}", cause=error
                )
            elif "benchmark" in operation.lower():
                return BenchmarkNotFoundError(
                    f"Benchmark not found during {operation}", cause=error
                )

        if "constraint" in error_str or "duplicate" in error_str:
            return ValidationError(
                f"Data constraint violation during {operation}",
                ["Duplicate or invalid data detected"],
                cause=error,
            )

        if "connection" in error_str or "database" in error_str:
            return ExternalServiceError(
                f"Database error during {operation}",
                service_name="database",
                recoverable=True,
                cause=error,
            )

        if "timeout" in error_str:
            return ExternalServiceError(
                f"Database timeout during {operation}",
                service_name="database",
                recoverable=True,
                cause=error,
            )

        # Default to external service error
        return ExternalServiceError(
            f"Repository error during {operation}: {error}",
            service_name="repository",
            recoverable=False,
            cause=error,
        )

    def map_reasoning_agent_error(self, error: Exception) -> FailureReason:
        """Map reasoning agent errors to domain failure reasons.

        Args:
            error: Exception from reasoning agent

        Returns:
            Appropriate FailureReason value object
        """
        error_str = str(error).lower()
        error_type = type(error).__name__

        self._logger.debug(
            "Mapping reasoning agent error",
            extra={"error_type": error_type, "error_message": str(error)},
        )

        from datetime import datetime

        if "parsing" in error_str or "json" in error_str or "format" in error_str:
            return FailureReason(
                category="parsing_error",
                description="Failed to parse model response",
                technical_details=str(error),
                occurred_at=datetime.now(),
                recoverable=False,
            )

        if "timeout" in error_str:
            return FailureReason(
                category="network_timeout",
                description="Reasoning agent timeout",
                technical_details=str(error),
                occurred_at=datetime.now(),
                recoverable=True,
            )

        if "configuration" in error_str or "invalid" in error_str:
            return FailureReason(
                category="parsing_error",
                description="Invalid agent configuration",
                technical_details=str(error),
                occurred_at=datetime.now(),
                recoverable=False,
            )

        # Check if it's an OpenRouter error wrapped by the agent
        if (
            hasattr(error, "__cause__")
            and error.__cause__
            and isinstance(error.__cause__, Exception)
        ):
            return self.map_openrouter_error(error.__cause__)

        return FailureReason(
            category="unknown",
            description="Reasoning agent error",
            technical_details=str(error),
            occurred_at=datetime.now(),
            recoverable=False,
        )

    def should_retry_error(self, error: Exception) -> bool:
        """Determine if an error is recoverable and should be retried.

        Args:
            error: Exception to analyze

        Returns:
            True if the error might succeed on retry
        """
        error_str = str(error).lower()

        # Retriable conditions
        retriable_patterns = [
            "timeout",
            "connection",
            "rate limit",
            "temporary",
            "503",  # Service unavailable
            "502",  # Bad gateway
            "504",  # Gateway timeout
        ]

        # Non-retriable conditions
        non_retriable_patterns = [
            "401",  # Unauthorized
            "403",  # Forbidden
            "402",  # Payment required
            "400",  # Bad request
            "not found",
            "authentication",
            "authorization",
            "credit",
            "quota",
        ]

        # Check non-retriable first (more specific)
        for pattern in non_retriable_patterns:
            if pattern in error_str:
                return False

        # Check retriable patterns
        for pattern in retriable_patterns:
            if pattern in error_str:
                return True

        # Check exception types
        if isinstance(error, ExternalServiceError):
            return error.recoverable

        # Default to non-retriable for unknown errors
        return False

    def create_execution_error(
        self,
        operation: str,
        errors: list[Exception],
        context: dict[str, Any] | None = None,
    ) -> EvaluationExecutionError:
        """Create a comprehensive execution error from multiple failures.

        Args:
            operation: Description of the failed operation
            errors: List of underlying errors
            context: Optional context information

        Returns:
            Comprehensive execution error
        """
        if not errors:
            return EvaluationExecutionError(f"Unknown error during {operation}")

        primary_error = errors[0]
        error_count = len(errors)

        if error_count == 1:
            message = f"{operation} failed: {primary_error}"
        else:
            message = f"{operation} failed with {error_count} errors. Primary: {primary_error}"

        execution_error = EvaluationExecutionError(message, cause=primary_error)

        # Add context if provided (using a type ignore since we're adding dynamic attribute)
        if context:
            execution_error.context = context  # type: ignore[attr-defined]

        return execution_error

    def categorize_failure_severity(self, failure_reason: FailureReason) -> str:
        """Categorize the severity of a failure reason.

        Args:
            failure_reason: FailureReason to categorize

        Returns:
            Severity level: "low", "medium", "high", "critical"
        """
        category = failure_reason.category.lower()

        # Critical - system-level failures that prevent operation
        if category in ["authentication_error", "credit_limit_exceeded"]:
            return "critical"

        # High - likely to affect multiple questions
        if category in ["network_timeout", "rate_limit_exceeded"]:
            return "high"

        # Medium - may affect individual questions but evaluation can continue
        if category in [
            "parsing_error",
            "content_guardrail_triggered",
            "model_refusal",
        ]:
            return "medium"

        # Low - expected occasional failures
        if category in ["token_limit_exceeded"]:
            return "low"

        # Unknown - treat as medium
        return "medium"
