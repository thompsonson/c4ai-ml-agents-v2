"""SQLAlchemy model for EvaluationQuestionResult entity."""

import json
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from ml_agents_v2.core.domain.entities.evaluation_question_result import (
    EvaluationQuestionResult,
)
from ml_agents_v2.core.domain.value_objects.reasoning_trace import ReasoningTrace
from ml_agents_v2.infrastructure.database.base import Base
from ml_agents_v2.infrastructure.database.exceptions import SerializationError


class EvaluationQuestionResultModel(Base):
    """SQLAlchemy model for EvaluationQuestionResult domain entity.

    Maps individual question results to database table with JSON fields
    for complex data (reasoning_trace).
    """

    __tablename__ = "evaluation_question_results"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Foreign key to evaluations table
    evaluation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evaluations.evaluation_id", ondelete="CASCADE"),
        nullable=False,
    )

    # Question identification
    question_id: Mapped[str] = mapped_column(String(255), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    expected_answer: Mapped[str] = mapped_column(Text, nullable=False)

    # Results
    actual_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # Performance metrics
    execution_time: Mapped[float] = mapped_column(Float, nullable=False)

    # Reasoning information
    reasoning_trace_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Error handling
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    technical_details: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamp
    processed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    @classmethod
    def from_domain(
        cls, question_result: EvaluationQuestionResult
    ) -> "EvaluationQuestionResultModel":
        """Create EvaluationQuestionResultModel from domain entity.

        Args:
            question_result: Domain EvaluationQuestionResult entity

        Returns:
            EvaluationQuestionResultModel instance
        """

        # Serialize reasoning trace to JSON if present
        reasoning_trace_json = None
        if question_result.reasoning_trace:
            try:
                reasoning_trace_json = json.dumps(
                    {
                        "approach_type": question_result.reasoning_trace.approach_type,
                        "reasoning_text": question_result.reasoning_trace.reasoning_text,
                        "metadata": dict(
                            question_result.reasoning_trace.metadata
                        ),  # Fix mappingproxy
                    }
                )
            except (TypeError, ValueError, RecursionError) as e:
                raise SerializationError(
                    entity_type="EvaluationQuestionResult",
                    entity_id=str(question_result.id),
                    field_name="reasoning_trace",
                    original_error=e,
                ) from e

        return cls(
            id=question_result.id,
            evaluation_id=question_result.evaluation_id,
            question_id=question_result.question_id,
            question_text=question_result.question_text,
            expected_answer=question_result.expected_answer,
            actual_answer=question_result.actual_answer,
            is_correct=question_result.is_correct,
            execution_time=question_result.execution_time,
            reasoning_trace_json=reasoning_trace_json,
            error_message=question_result.error_message,
            technical_details=question_result.technical_details,
            processed_at=question_result.processed_at,
        )

    def to_domain(self) -> EvaluationQuestionResult:
        """Convert EvaluationQuestionResultModel to domain entity.

        Returns:
            Domain EvaluationQuestionResult entity
        """

        # Deserialize reasoning trace from JSON if present
        reasoning_trace = None
        if self.reasoning_trace_json:
            trace_data = json.loads(self.reasoning_trace_json)
            reasoning_trace = ReasoningTrace(
                approach_type=trace_data["approach_type"],
                reasoning_text=trace_data["reasoning_text"],
                metadata=trace_data["metadata"],
            )

        return EvaluationQuestionResult(
            id=self.id,
            evaluation_id=self.evaluation_id,
            question_id=self.question_id,
            question_text=self.question_text,
            expected_answer=self.expected_answer,
            actual_answer=self.actual_answer,
            is_correct=self.is_correct,
            execution_time=self.execution_time,
            reasoning_trace=reasoning_trace,
            error_message=self.error_message,
            technical_details=self.technical_details,
            processed_at=self.processed_at,
        )
