"""Progress tracking for evaluation execution."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from datetime import datetime

from ..dto.progress_info import ProgressInfo


class ProgressTracker:
    """Manages progress tracking for long-running evaluation operations.

    Provides real-time progress updates during evaluation execution
    with callback mechanisms for UI integration and logging.
    """

    def __init__(self) -> None:
        """Initialize the progress tracker."""
        self._logger = logging.getLogger(__name__)
        self._active_evaluations: dict[uuid.UUID, ProgressInfo] = {}

    def start_evaluation_tracking(
        self,
        evaluation_id: uuid.UUID,
        total_questions: int,
        started_at: datetime | None = None,
    ) -> None:
        """Start tracking progress for an evaluation.

        Args:
            evaluation_id: ID of the evaluation to track
            total_questions: Total number of questions to process
            started_at: When the evaluation started (defaults to now)
        """
        if started_at is None:
            started_at = datetime.now()

        initial_progress = ProgressInfo(
            evaluation_id=evaluation_id,
            current_question=0,
            total_questions=total_questions,
            successful_answers=0,
            failed_questions=0,
            started_at=started_at,
            last_updated=started_at,
        )

        self._active_evaluations[evaluation_id] = initial_progress

        self._logger.info(
            "Started progress tracking",
            extra={
                "evaluation_id": str(evaluation_id),
                "total_questions": total_questions,
            },
        )

    def update_progress(
        self,
        evaluation_id: uuid.UUID,
        current_question: int,
        successful_answers: int,
        failed_questions: int,
        current_question_text: str | None = None,
    ) -> ProgressInfo:
        """Update progress for an evaluation.

        Args:
            evaluation_id: ID of the evaluation
            current_question: Current question number (1-based)
            successful_answers: Number of successful answers so far
            failed_questions: Number of failed questions so far
            current_question_text: Optional text of current question

        Returns:
            Updated progress information

        Raises:
            ValueError: If evaluation is not being tracked
        """
        if evaluation_id not in self._active_evaluations:
            raise ValueError(f"Evaluation {evaluation_id} is not being tracked")

        previous_progress = self._active_evaluations[evaluation_id]
        now = datetime.now()

        # Calculate estimated completion time
        if current_question > 0:
            elapsed_time = (now - previous_progress.started_at).total_seconds()
            time_per_question = elapsed_time / current_question
            remaining_questions = previous_progress.total_questions - current_question
            estimated_remaining = remaining_questions * time_per_question
            estimated_completion = now.timestamp() + estimated_remaining
            estimated_completion_dt = datetime.fromtimestamp(estimated_completion)
        else:
            estimated_completion_dt = None

        updated_progress = ProgressInfo(
            evaluation_id=evaluation_id,
            current_question=current_question,
            total_questions=previous_progress.total_questions,
            successful_answers=successful_answers,
            failed_questions=failed_questions,
            started_at=previous_progress.started_at,
            last_updated=now,
            estimated_completion=estimated_completion_dt,
            current_question_text=current_question_text,
        )

        self._active_evaluations[evaluation_id] = updated_progress

        self._logger.debug(
            "Updated evaluation progress",
            extra={
                "evaluation_id": str(evaluation_id),
                "progress": f"{current_question}/{previous_progress.total_questions}",
                "completion_percentage": updated_progress.completion_percentage,
            },
        )

        return updated_progress

    def finish_evaluation_tracking(
        self, evaluation_id: uuid.UUID
    ) -> ProgressInfo | None:
        """Finish tracking progress for an evaluation.

        Args:
            evaluation_id: ID of the evaluation to stop tracking

        Returns:
            Final progress information, or None if not tracked
        """
        if evaluation_id not in self._active_evaluations:
            self._logger.warning(
                "Attempted to finish tracking non-tracked evaluation",
                extra={"evaluation_id": str(evaluation_id)},
            )
            return None

        final_progress = self._active_evaluations.pop(evaluation_id)

        self._logger.info(
            "Finished progress tracking",
            extra={
                "evaluation_id": str(evaluation_id),
                "final_completion": final_progress.completion_percentage,
                "duration_minutes": final_progress.elapsed_minutes,
            },
        )

        return final_progress

    def get_current_progress(self, evaluation_id: uuid.UUID) -> ProgressInfo | None:
        """Get current progress for an evaluation.

        Args:
            evaluation_id: ID of the evaluation

        Returns:
            Current progress information, or None if not tracked
        """
        return self._active_evaluations.get(evaluation_id)

    def is_tracking(self, evaluation_id: uuid.UUID) -> bool:
        """Check if an evaluation is currently being tracked.

        Args:
            evaluation_id: ID of the evaluation

        Returns:
            True if tracking is active
        """
        return evaluation_id in self._active_evaluations

    def get_all_active_evaluations(self) -> list[ProgressInfo]:
        """Get progress information for all active evaluations.

        Returns:
            List of progress information for active evaluations
        """
        return list(self._active_evaluations.values())

    def cleanup_stale_tracking(self, max_age_hours: int = 24) -> list[uuid.UUID]:
        """Clean up stale tracking entries.

        Args:
            max_age_hours: Maximum age in hours before considering tracking stale

        Returns:
            List of evaluation IDs that were cleaned up
        """
        now = datetime.now()
        max_age_seconds = max_age_hours * 3600
        stale_evaluations = []

        for evaluation_id, progress in list(self._active_evaluations.items()):
            age_seconds = (now - progress.last_updated).total_seconds()
            if age_seconds > max_age_seconds:
                stale_evaluations.append(evaluation_id)
                del self._active_evaluations[evaluation_id]

        if stale_evaluations:
            self._logger.info(
                "Cleaned up stale progress tracking",
                extra={
                    "stale_count": len(stale_evaluations),
                    "max_age_hours": max_age_hours,
                },
            )

        return stale_evaluations


class ProgressCallback:
    """Wrapper for progress callback functions with error handling."""

    def __init__(
        self,
        callback: Callable[[ProgressInfo], None],
        error_handler: Callable[[Exception], None] | None = None,
    ) -> None:
        """Initialize progress callback.

        Args:
            callback: Function to call with progress updates
            error_handler: Optional function to handle callback errors
        """
        self._callback = callback
        self._error_handler = error_handler
        self._logger = logging.getLogger(__name__)

    def __call__(self, progress: ProgressInfo) -> None:
        """Call the progress callback with error handling.

        Args:
            progress: Progress information to report
        """
        try:
            self._callback(progress)
        except Exception as e:
            self._logger.error(
                "Progress callback failed",
                extra={
                    "evaluation_id": str(progress.evaluation_id),
                    "error": str(e),
                },
            )

            if self._error_handler:
                try:
                    self._error_handler(e)
                except Exception as handler_error:
                    self._logger.error(
                        "Progress callback error handler failed",
                        extra={"error": str(handler_error)},
                    )


def create_console_progress_callback() -> ProgressCallback:
    """Create a simple console progress callback.

    Returns:
        Progress callback that prints to console
    """

    def console_callback(progress: ProgressInfo) -> None:
        """Print progress to console."""
        print(f"\rProgress: {progress.progress_summary}", end="", flush=True)

    return ProgressCallback(console_callback)


def create_logging_progress_callback() -> ProgressCallback:
    """Create a progress callback that logs to the application logger.

    Returns:
        Progress callback that logs progress updates
    """
    logger = logging.getLogger("ml_agents_v2.progress")

    def logging_callback(progress: ProgressInfo) -> None:
        """Log progress information."""
        logger.info(
            "Evaluation progress update",
            extra={
                "evaluation_id": str(progress.evaluation_id),
                "current_question": progress.current_question,
                "total_questions": progress.total_questions,
                "completion_percentage": progress.completion_percentage,
                "success_rate": progress.success_rate,
                "questions_per_minute": progress.questions_per_minute,
            },
        )

    return ProgressCallback(logging_callback)
