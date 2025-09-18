"""ReasoningTrace value object."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ReasoningTrace:
    """Documentation of the reasoning process used for each question.

    This value object handles different reasoning approaches:
    - 'none': Empty reasoning trace (direct answers)
    - 'chain_of_thought': Step-by-step reasoning text populated

    The trace is immutable once created and contains approach type,
    reasoning text, and optional metadata about the reasoning process.
    """

    approach_type: str
    reasoning_text: str
    metadata: Mapping[str, Any]

    def __post_init__(self) -> None:
        """Validate reasoning trace data and ensure immutability."""
        from types import MappingProxyType

        # Valid approach types (from Phase 1 specifications)
        valid_approaches = {"none", "chain_of_thought"}
        if self.approach_type not in valid_approaches:
            raise ValueError(
                f"approach_type must be one of {valid_approaches}, got '{self.approach_type}'"
            )

        # Validate approach-specific rules
        if self.approach_type == "none":
            if self.reasoning_text.strip():
                raise ValueError("'none' approach must have empty reasoning_text")
        elif self.approach_type == "chain_of_thought":
            if not self.reasoning_text or not self.reasoning_text.strip():
                raise ValueError(
                    "'chain_of_thought' approach must have non-empty reasoning_text"
                )

        # Handle None metadata by converting to empty dict
        metadata_dict = dict(self.metadata) if self.metadata is not None else {}

        # Convert to immutable mapping
        object.__setattr__(self, "metadata", MappingProxyType(metadata_dict))

    def equals(self, other: object) -> bool:
        """Value-based equality comparison."""
        if not isinstance(other, ReasoningTrace):
            return False

        return (
            self.approach_type == other.approach_type
            and self.reasoning_text == other.reasoning_text
            and self.metadata == other.metadata
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for storage/comparison."""
        return {
            "approach_type": self.approach_type,
            "reasoning_text": self.reasoning_text,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReasoningTrace:
        """Create ReasoningTrace from dictionary data."""
        return cls(
            approach_type=data["approach_type"],
            reasoning_text=data["reasoning_text"],
            metadata=data.get("metadata", {}),
        )

    @property
    def is_empty(self) -> bool:
        """Check if this is an empty trace (none approach)."""
        return self.approach_type == "none"

    @property
    def has_reasoning(self) -> bool:
        """Check if this trace contains reasoning steps."""
        return self.approach_type != "none" and bool(self.reasoning_text.strip())
