"""Evaluation entity."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from ..value_objects.agent_config import AgentConfig
from ..value_objects.evaluation_results import EvaluationResults
from ..value_objects.failure_reason import FailureReason

if TYPE_CHECKING:
    from ...application.dto.progress_info import ProgressInfo
    from ..repositories.evaluation_question_result_repository import (
        EvaluationQuestionResultRepository,
    )


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

        # Business rule: Results are now computed from question results
        # Completed evaluations don't store results directly

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

    def complete(self) -> Evaluation:
        """Complete evaluation successfully.

        Results are now computed from individual question results rather
        than being stored directly in the evaluation entity.

        Returns a new Evaluation instance with completed state.
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
            results=None,  # Results computed from question results
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

    def interrupt(self) -> Evaluation:
        """Mark evaluation as interrupted, preserving partial progress.

        Returns a new Evaluation instance with interrupted state.
        Individual question results are preserved for potential resume.
        """
        if self.status != "running":
            raise ValueError(
                f"Cannot interrupt evaluation from status '{self.status}'. "
                "Evaluation must be in 'running' state."
            )

        return Evaluation(
            evaluation_id=self.evaluation_id,
            agent_config=self.agent_config,
            preprocessed_benchmark_id=self.preprocessed_benchmark_id,
            status="interrupted",
            created_at=self.created_at,
            started_at=self.started_at,
            completed_at=datetime.now(),
            results=None,
            failure_reason=None,
        )

    def get_progress(
        self, question_result_repository: EvaluationQuestionResultRepository
    ) -> ProgressInfo:
        """Get current progress information from saved question results.

        Args:
            question_result_repository: Repository to query question results

        Returns:
            Progress information computed from saved results
        """
        from datetime import datetime

        from ...application.dto.progress_info import ProgressInfo

        # Get domain progress and convert to application DTO
        domain_progress = question_result_repository.get_progress(
            self.evaluation_id, total_questions=0  # This would need to be provided
        )

        # Parse latest_processed_at if it's a string, fallback to created_at
        last_updated = self.created_at
        if domain_progress.latest_processed_at:
            try:
                last_updated = datetime.fromisoformat(
                    domain_progress.latest_processed_at
                )
            except ValueError:
                last_updated = self.created_at

        return ProgressInfo(
            evaluation_id=domain_progress.evaluation_id,
            current_question=domain_progress.completed_questions,
            total_questions=domain_progress.total_questions,
            successful_answers=domain_progress.successful_questions,
            failed_questions=domain_progress.failed_questions,
            started_at=self.started_at or self.created_at,
            last_updated=last_updated,
        )
