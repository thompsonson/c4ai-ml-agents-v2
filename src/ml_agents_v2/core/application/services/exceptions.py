"""Application service exceptions."""

from __future__ import annotations


class ApplicationServiceError(Exception):
    """Base exception for application service errors."""

    def __init__(self, message: str, cause: Exception | None = None) -> None:
        """Initialize application service error.

        Args:
            message: Error message
            cause: Optional underlying exception
        """
        super().__init__(message)
        self.cause = cause


class EvaluationNotFoundError(ApplicationServiceError):
    """Raised when a requested evaluation cannot be found."""

    pass


class BenchmarkNotFoundError(ApplicationServiceError):
    """Raised when a requested benchmark cannot be found."""

    pass


class InvalidEvaluationStateError(ApplicationServiceError):
    """Raised when an operation is invalid for the current evaluation state."""

    pass


class EvaluationExecutionError(ApplicationServiceError):
    """Raised when evaluation execution fails."""

    pass


class ValidationError(ApplicationServiceError):
    """Raised when input validation fails."""

    def __init__(
        self, message: str, errors: list[str], cause: Exception | None = None
    ) -> None:
        """Initialize validation error.

        Args:
            message: Error message
            errors: List of specific validation errors
            cause: Optional underlying exception
        """
        super().__init__(message, cause)
        self.errors = errors


class ConfigurationError(ApplicationServiceError):
    """Raised when configuration is invalid or missing."""

    pass


class ExternalServiceError(ApplicationServiceError):
    """Raised when external service integration fails."""

    def __init__(
        self,
        message: str,
        service_name: str,
        recoverable: bool = True,
        cause: Exception | None = None,
    ) -> None:
        """Initialize external service error.

        Args:
            message: Error message
            service_name: Name of the external service
            recoverable: Whether the error might succeed on retry
            cause: Optional underlying exception
        """
        super().__init__(message, cause)
        self.service_name = service_name
        self.recoverable = recoverable
