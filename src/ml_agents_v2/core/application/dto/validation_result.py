"""Validation result DTO for application layer."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ValidationResult:
    """Data transfer object for validation results.

    Used for reporting validation outcomes across different layers
    with detailed error and warning information.
    """

    is_valid: bool
    errors: list[str]
    warnings: list[str]

    @classmethod
    def success(cls, warnings: list[str] | None = None) -> ValidationResult:
        """Create a successful validation result.

        Args:
            warnings: Optional list of warning messages

        Returns:
            ValidationResult indicating success
        """
        return cls(is_valid=True, errors=[], warnings=warnings or [])

    @classmethod
    def failure(
        cls, errors: list[str], warnings: list[str] | None = None
    ) -> ValidationResult:
        """Create a failed validation result.

        Args:
            errors: List of error messages
            warnings: Optional list of warning messages

        Returns:
            ValidationResult indicating failure
        """
        return cls(is_valid=False, errors=errors, warnings=warnings or [])

    @classmethod
    def single_error(cls, error: str) -> ValidationResult:
        """Create a failed validation result with a single error.

        Args:
            error: Single error message

        Returns:
            ValidationResult indicating failure
        """
        return cls.failure([error])

    @property
    def has_warnings(self) -> bool:
        """Check if validation has warnings."""
        return len(self.warnings) > 0

    @property
    def has_errors(self) -> bool:
        """Check if validation has errors."""
        return len(self.errors) > 0

    def add_error(self, error: str) -> ValidationResult:
        """Add an error to the validation result.

        Args:
            error: Error message to add

        Returns:
            New ValidationResult with the added error
        """
        return ValidationResult(
            is_valid=False, errors=self.errors + [error], warnings=self.warnings
        )

    def add_warning(self, warning: str) -> ValidationResult:
        """Add a warning to the validation result.

        Args:
            warning: Warning message to add

        Returns:
            New ValidationResult with the added warning
        """
        return ValidationResult(
            is_valid=self.is_valid,
            errors=self.errors,
            warnings=self.warnings + [warning],
        )

    def combine(self, other: ValidationResult) -> ValidationResult:
        """Combine this validation result with another.

        Args:
            other: Another validation result to combine

        Returns:
            New ValidationResult with combined errors and warnings
        """
        return ValidationResult(
            is_valid=self.is_valid and other.is_valid,
            errors=self.errors + other.errors,
            warnings=self.warnings + other.warnings,
        )
