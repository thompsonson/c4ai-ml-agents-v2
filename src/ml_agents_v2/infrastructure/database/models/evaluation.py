"""SQLAlchemy model for Evaluation entity."""

import json
import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from ml_agents_v2.core.domain.entities.evaluation import Evaluation
from ml_agents_v2.core.domain.value_objects.agent_config import AgentConfig
from ml_agents_v2.core.domain.value_objects.evaluation_results import EvaluationResults
from ml_agents_v2.core.domain.value_objects.failure_reason import FailureReason
from ml_agents_v2.infrastructure.database.base import Base


class EvaluationModel(Base):
    """SQLAlchemy model for Evaluation domain entity.

    Maps the Evaluation aggregate root to database table with JSON fields
    for complex value objects (AgentConfig, EvaluationResults, FailureReason).
    """

    __tablename__ = "evaluations"

    # Primary key
    evaluation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Foreign key to benchmarks
    preprocessed_benchmark_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )

    # Agent configuration as JSON
    agent_config_json: Mapped[str] = mapped_column(Text, nullable=False)

    # Evaluation status
    status: Mapped[str] = mapped_column(String(20), nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Results as JSON (nullable for pending/running evaluations)
    results_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Failure reason as JSON (nullable for successful evaluations)
    failure_reason_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    @classmethod
    def from_domain(cls, evaluation: Evaluation) -> "EvaluationModel":
        """Create EvaluationModel from domain Evaluation entity.

        Args:
            evaluation: Domain Evaluation entity

        Returns:
            EvaluationModel instance
        """
        # Serialize agent config to JSON
        agent_config_json = json.dumps(evaluation.agent_config.to_dict())

        # Serialize results to JSON if present
        results_json = None
        if evaluation.results:
            results_json = json.dumps(
                {
                    "total_questions": evaluation.results.total_questions,
                    "correct_answers": evaluation.results.correct_answers,
                    "accuracy": evaluation.results.accuracy,
                    "average_execution_time": evaluation.results.average_execution_time,
                    "error_count": evaluation.results.error_count,
                    "detailed_results": [
                        {
                            "question_id": result.question_id,
                            "question_text": result.question_text,
                            "expected_answer": result.expected_answer,
                            "actual_answer": result.actual_answer,
                            "is_correct": result.is_correct,
                        }
                        for result in evaluation.results.detailed_results
                    ],
                    "summary_statistics": evaluation.results.summary_statistics,
                }
            )

        # Serialize failure reason to JSON if present
        failure_reason_json = None
        if evaluation.failure_reason:
            failure_reason_json = json.dumps(
                {
                    "category": evaluation.failure_reason.category,
                    "description": evaluation.failure_reason.description,
                    "technical_details": evaluation.failure_reason.technical_details,
                    "occurred_at": evaluation.failure_reason.occurred_at.isoformat(),
                    "recoverable": evaluation.failure_reason.recoverable,
                }
            )

        return cls(
            evaluation_id=evaluation.evaluation_id,
            preprocessed_benchmark_id=evaluation.preprocessed_benchmark_id,
            agent_config_json=agent_config_json,
            status=evaluation.status,
            created_at=evaluation.created_at,
            started_at=evaluation.started_at,
            completed_at=evaluation.completed_at,
            results_json=results_json,
            failure_reason_json=failure_reason_json,
        )

    def to_domain(self) -> Evaluation:
        """Convert EvaluationModel to domain Evaluation entity.

        Returns:
            Domain Evaluation entity
        """
        # Deserialize agent config from JSON
        agent_config_data = json.loads(self.agent_config_json)
        agent_config = AgentConfig(
            agent_type=agent_config_data["agent_type"],
            model_provider=agent_config_data["model_provider"],
            model_name=agent_config_data["model_name"],
            model_parameters=agent_config_data["model_parameters"],
            agent_parameters=agent_config_data["agent_parameters"],
        )

        # Deserialize results from JSON if present
        results = None
        if self.results_json:
            results_data = json.loads(self.results_json)
            from ml_agents_v2.core.domain.value_objects.evaluation_results import (
                QuestionResult,
            )

            detailed_results = [
                QuestionResult(
                    question_id=result["question_id"],
                    question_text=result["question_text"],
                    expected_answer=result["expected_answer"],
                    actual_answer=result["actual_answer"],
                    is_correct=result["is_correct"],
                )
                for result in results_data["detailed_results"]
            ]

            results = EvaluationResults(
                total_questions=results_data["total_questions"],
                correct_answers=results_data["correct_answers"],
                accuracy=results_data["accuracy"],
                average_execution_time=results_data["average_execution_time"],
                error_count=results_data["error_count"],
                detailed_results=detailed_results,
                summary_statistics=results_data["summary_statistics"],
            )

        # Deserialize failure reason from JSON if present
        failure_reason = None
        if self.failure_reason_json:
            failure_data = json.loads(self.failure_reason_json)
            from datetime import datetime

            failure_reason = FailureReason(
                category=failure_data["category"],
                description=failure_data["description"],
                technical_details=failure_data["technical_details"],
                occurred_at=datetime.fromisoformat(failure_data["occurred_at"]),
                recoverable=failure_data["recoverable"],
            )

        return Evaluation(
            evaluation_id=self.evaluation_id,
            agent_config=agent_config,
            preprocessed_benchmark_id=self.preprocessed_benchmark_id,
            status=self.status,
            created_at=self.created_at,
            started_at=self.started_at,
            completed_at=self.completed_at,
            results=results,
            failure_reason=failure_reason,
        )
