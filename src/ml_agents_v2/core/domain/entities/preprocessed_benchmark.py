"""PreprocessedBenchmark entity."""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ..value_objects.question import Question


@dataclass(frozen=True)
class PreprocessedBenchmark:
    """Ready-to-evaluate dataset with standardized format.

    Represents a collection of questions that have been preprocessed and
    validated for evaluation. Provides methods for sampling and accessing
    benchmark metadata.
    """

    benchmark_id: uuid.UUID
    name: str
    description: str
    questions: list[Question]
    metadata: dict[str, Any]
    created_at: datetime
    question_count: int
    format_version: str

    def __post_init__(self) -> None:
        """Validate PreprocessedBenchmark state after construction."""
        if not self.name or not self.name.strip():
            raise ValueError("Name cannot be empty")

        if not self.questions:
            raise ValueError("Must have at least one question")

        if self.question_count != len(self.questions):
            raise ValueError(
                f"Question count ({self.question_count}) must match "
                f"actual number of questions ({len(self.questions)})"
            )

        # Validate unique question IDs
        question_ids = [q.id for q in self.questions]
        if len(question_ids) != len(set(question_ids)):
            raise ValueError("Question IDs must be unique within benchmark")

    def get_questions(self) -> list[Question]:
        """Return all questions for evaluation."""
        return list(self.questions)  # Return copy to maintain immutability

    def get_sample(self, size: int) -> list[Question]:
        """Return random sample of questions.

        If requested size exceeds available questions, returns all questions.
        """
        if size >= len(self.questions):
            return list(self.questions)  # Return copy

        return random.sample(self.questions, size)

    def get_metadata(self) -> dict[str, Any]:
        """Return benchmark metadata."""
        return dict(self.metadata)  # Return copy to maintain immutability
