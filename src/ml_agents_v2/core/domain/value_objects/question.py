"""Question value object."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Question:
    """Standardized input data from benchmark.

    This is a value object representing individual test cases from benchmarks.
    Questions are immutable once created and contain the text, expected answer,
    and optional metadata (difficulty, category, etc.).
    """

    id: str
    text: str
    expected_answer: str
    metadata: Mapping[str, Any]

    def __post_init__(self) -> None:
        """Validate question data and ensure immutability."""
        from types import MappingProxyType

        # Validate required fields are not empty
        if not self.id or not self.id.strip():
            raise ValueError("id cannot be empty")
        if not self.text or not self.text.strip():
            raise ValueError("text cannot be empty")
        if not self.expected_answer or not self.expected_answer.strip():
            raise ValueError("expected_answer cannot be empty")

        # Handle None metadata by converting to empty dict
        metadata_dict = dict(self.metadata) if self.metadata is not None else {}

        # Convert to immutable mapping
        object.__setattr__(self, "metadata", MappingProxyType(metadata_dict))

    def equals(self, other: object) -> bool:
        """Value-based equality comparison."""
        if not isinstance(other, Question):
            return False

        return (
            self.id == other.id
            and self.text == other.text
            and self.expected_answer == other.expected_answer
            and self.metadata == other.metadata
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for storage/comparison."""
        return {
            "id": self.id,
            "text": self.text,
            "expected_answer": self.expected_answer,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Question:
        """Create Question from dictionary data."""
        return cls(
            id=data["id"],
            text=data["text"],
            expected_answer=data["expected_answer"],
            metadata=data.get("metadata", {}),
        )
