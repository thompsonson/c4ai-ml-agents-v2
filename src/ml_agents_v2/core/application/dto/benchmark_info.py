"""Benchmark information DTO for application layer."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class BenchmarkInfo:
    """Data transfer object for benchmark summary information.

    Used for displaying benchmark lists and metadata without exposing
    the full domain entity structure.
    """

    benchmark_id: uuid.UUID
    name: str
    description: str
    question_count: int
    created_at: datetime
    format_version: str
    categories: list[str] | None = None
    average_question_length: int | None = None

    @property
    def short_description(self) -> str:
        """Get truncated description for list displays."""
        if len(self.description) <= 80:
            return self.description
        return self.description[:77] + "..."

    @property
    def question_count_display(self) -> str:
        """Get formatted question count."""
        if self.question_count == 1:
            return "1 question"
        return f"{self.question_count:,} questions"

    @property
    def categories_display(self) -> str:
        """Get formatted categories list."""
        if not self.categories:
            return "Mixed"
        if len(self.categories) <= 3:
            return ", ".join(self.categories)
        return f"{', '.join(self.categories[:2])}, +{len(self.categories) - 2} more"
