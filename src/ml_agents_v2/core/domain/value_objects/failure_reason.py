"""FailureReason value object."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Final

VALID_FAILURE_CATEGORIES: Final = {
    "parsing_error",
    "token_limit_exceeded",
    "content_guardrail",
    "model_refusal",
    "network_timeout",
    "rate_limit_exceeded",
    "credit_limit_exceeded",
    "authentication_error",
    "unknown",
}

FAILURE_CATEGORY_DESCRIPTIONS: Final = {
    "parsing_error": "Model response could not be parsed into expected format",
    "token_limit_exceeded": "Request exceeded the model's token capacity limit",
    "content_guardrail": "Model safety systems prevented response generation",
    "model_refusal": "Model explicitly declined to answer the question",
    "network_timeout": "Network communication with model provider failed",
    "rate_limit_exceeded": "API rate limit reached, retry after delay",
    "credit_limit_exceeded": "Insufficient API credits or budget remaining",
    "authentication_error": "Invalid API key or authentication failure",
    "unknown": "Unexpected error not fitting other defined categories",
}


@dataclass(frozen=True)
class FailureReason:
    """Detailed categorization of evaluation failures.

    Understanding why evaluations fail is crucial for researchers to improve
    their approaches and identify systematic issues.
    """

    category: str
    description: str
    technical_details: str
    occurred_at: datetime
    recoverable: bool

    def __post_init__(self) -> None:
        """Validate FailureReason attributes after construction."""
        if self.category not in VALID_FAILURE_CATEGORIES:
            raise ValueError(
                f"Invalid failure category '{self.category}'. "
                f"Must be one of: {', '.join(sorted(VALID_FAILURE_CATEGORIES))}"
            )

        if not self.description or not self.description.strip():
            raise ValueError("Description cannot be empty")

    def is_recoverable(self) -> bool:
        """Return whether this failure type might succeed on retry."""
        return self.recoverable

    def get_category_description(self) -> str:
        """Return human-friendly explanation of failure type."""
        return FAILURE_CATEGORY_DESCRIPTIONS[self.category]
