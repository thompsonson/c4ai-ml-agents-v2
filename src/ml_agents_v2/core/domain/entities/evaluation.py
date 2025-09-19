"""Evaluation entity."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from ..value_objects.agent_config import AgentConfig
from ..value_objects.evaluation_results import EvaluationResults
from ..value_objects.failure_reason import FailureReason


@dataclass(frozen=True)
class Evaluation:
    """Orchestrates the evaluation of an AgentConfig against a PreprocessedBenchmark.

    This is the main aggregate root that manages the evaluation lifecycle,
    enforces business rules, and maintains state consistency.
    """

    evaluation_id: uuid.UUID
    agent_config: AgentConfig
    preprocessed_benchmark_id: uuid.UUID
    status: str
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    results: EvaluationResults | None
    failure_reason: FailureReason | None

    VALID_STATUSES = {"pending", "running", "completed", "failed", "interrupted"}

    def __post_init__(self) -> None:
        """Validate Evaluation state after construction."""
        if self.status not in self.VALID_STATUSES:
            raise ValueError(
                f"Invalid status '{self.status}'. "
                f"Must be one of: {', '.join(sorted(self.VALID_STATUSES))}"
            )

        # Business rule: completed evaluation must have results
        if self.status == "completed" and self.results is None:
            raise ValueError("Completed evaluation must have results")

        # Business rule: failed evaluation must have failure reason
        if self.status == "failed" and self.failure_reason is None:
            raise ValueError("Failed evaluation must have failure reason")

        # Business rule: pending evaluation cannot have results or failure reason
        if self.status == "pending":
            if self.results is not None:
                raise ValueError("Pending evaluation cannot have results")
            if self.failure_reason is not None:
                raise ValueError("Pending evaluation cannot have failure reason")
            if self.started_at is not None:
                raise ValueError("Pending evaluation cannot have started_at")
            if self.completed_at is not None:
                raise ValueError("Pending evaluation cannot have completed_at")

        # Business rule: running evaluation cannot have results, failure reason, or completed_at
        if self.status == "running":
            if self.results is not None:
                raise ValueError("Running evaluation cannot have results")
            if self.failure_reason is not None:
                raise ValueError("Running evaluation cannot have failure reason")
            if self.completed_at is not None:
                raise ValueError("Running evaluation cannot have completed_at")
            if self.started_at is None:
                raise ValueError("Running evaluation must have started_at")

    def start_execution(self) -> Evaluation:
        """Transition evaluation from pending to running state.

        Returns a new Evaluation instance with updated state.
        """
        if self.status != "pending":
            raise ValueError(
                f"Cannot start execution from status '{self.status}'. "
                "Evaluation must be in 'pending' state."
            )

        return Evaluation(
            evaluation_id=self.evaluation_id,
            agent_config=self.agent_config,
            preprocessed_benchmark_id=self.preprocessed_benchmark_id,
            status="running",
            created_at=self.created_at,
            started_at=datetime.now(),
            completed_at=None,
            results=None,
            failure_reason=None,
        )

    def complete_with_results(self, results: EvaluationResults) -> Evaluation:
        """Complete evaluation with successful results.

        Returns a new Evaluation instance with completed state and results.
        """
        if self.status != "running":
            raise ValueError(
                f"Cannot complete evaluation from status '{self.status}'. "
                "Evaluation must be in 'running' state."
            )

        return Evaluation(
            evaluation_id=self.evaluation_id,
            agent_config=self.agent_config,
            preprocessed_benchmark_id=self.preprocessed_benchmark_id,
            status="completed",
            created_at=self.created_at,
            started_at=self.started_at,
            completed_at=datetime.now(),
            results=results,
            failure_reason=None,
        )

    def fail_with_reason(self, failure_reason: FailureReason) -> Evaluation:
        """Mark evaluation as failed with specific failure reason.

        Returns a new Evaluation instance with failed state and failure reason.
        """
        if self.status not in ["pending", "running"]:
            raise ValueError(
                f"Cannot fail evaluation from status '{self.status}'. "
                "Evaluation must be in 'pending' or 'running' state."
            )

        return Evaluation(
            evaluation_id=self.evaluation_id,
            agent_config=self.agent_config,
            preprocessed_benchmark_id=self.preprocessed_benchmark_id,
            status="failed",
            created_at=self.created_at,
            started_at=self.started_at,
            completed_at=datetime.now(),
            results=None,
            failure_reason=failure_reason,
        )

    def can_be_modified(self) -> bool:
        """Check if evaluation can be modified.

        Business rule: Cannot be modified once status is 'completed' or 'failed'.
        """
        return self.status not in ["completed", "failed"]
