"""ReasoningResult domain value object for processed reasoning output."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .reasoning_trace import ReasoningTrace


@dataclass(frozen=True)
class ReasoningResult:
    """Domain result after applying reasoning strategy."""

    final_answer: str
    reasoning_text: str
    execution_metadata: dict[str, Any]

    def get_answer(self) -> str:
        """Extract final answer using domain rules."""
        return self.final_answer.strip()

    def get_reasoning_trace(self) -> ReasoningTrace:
        """Convert to domain reasoning trace."""
        approach_type = self._determine_approach_type()
        return ReasoningTrace(
            approach_type=approach_type,
            reasoning_text=self.reasoning_text,
            metadata=self.execution_metadata,
        )

    def _determine_approach_type(self) -> str:
        """Domain logic to determine reasoning approach from content."""
        return "chain_of_thought" if self.reasoning_text else "none"
