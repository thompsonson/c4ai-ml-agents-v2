"""Exceptions for structured output parsing."""

from typing import Any


class ParserException(Exception):
    """Single exception type for all parsing failures with rich context.

    This exception provides comprehensive context for debugging parsing failures,
    including parser type, model, stage of failure, content, and original error.
    """

    def __init__(
        self,
        parser_type: str,  # "InstructorParser" | "StructuredLogProbsParser"
        model: str,
        provider: str,
        stage: str,  # "json_parse" | "schema_validation" | "response_empty"
        content: str,
        error: Exception,
    ):
        self.parser_type = parser_type
        self.model = model
        self.provider = provider
        self.stage = stage
        self.content = content
        self.original_error = error
        super().__init__(f"{parser_type} failed at {stage}: {error}")

    def get_truncated_content(self, limit: int = 200) -> str:
        """Return truncated content for logging purposes."""
        if len(self.content) <= limit:
            return self.content
        return self.content[:limit] + "..."

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for logging/serialization."""
        return {
            "parser_type": self.parser_type,
            "model": self.model,
            "provider": self.provider,
            "stage": self.stage,
            "content": self.get_truncated_content(),
            "original_error_type": type(self.original_error).__name__,
            "original_error_message": str(self.original_error),
        }
