"""Validation result value object."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ValidationResult:
    """Result of validation operations."""

    is_valid: bool
    errors: list[str]
    warnings: list[str] = field(default_factory=list)
