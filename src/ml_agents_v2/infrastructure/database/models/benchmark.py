"""SQLAlchemy model for PreprocessedBenchmark entity."""

import json
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from ml_agents_v2.core.domain.entities.preprocessed_benchmark import (
    PreprocessedBenchmark,
)
from ml_agents_v2.core.domain.value_objects.question import Question
from ml_agents_v2.infrastructure.database.base import Base


class BenchmarkModel(Base):
    """SQLAlchemy model for PreprocessedBenchmark domain entity.

    Maps the PreprocessedBenchmark aggregate root to database table with JSON
    fields for questions array and metadata.
    """

    __tablename__ = "preprocessed_benchmarks"

    # Primary key
    benchmark_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Basic benchmark information
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    format_version: Mapped[str] = mapped_column(String(50), nullable=False)
    question_count: Mapped[int] = mapped_column(Integer, nullable=False)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Questions as JSON array
    questions_json: Mapped[str] = mapped_column(Text, nullable=False)

    # Metadata as JSON
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False)

    @classmethod
    def from_domain(cls, benchmark: PreprocessedBenchmark) -> "BenchmarkModel":
        """Create BenchmarkModel from domain PreprocessedBenchmark entity.

        Args:
            benchmark: Domain PreprocessedBenchmark entity

        Returns:
            BenchmarkModel instance
        """
        # Serialize questions to JSON
        questions_json = json.dumps(
            [question.to_dict() for question in benchmark.questions]
        )

        # Serialize metadata to JSON
        metadata_json = json.dumps(benchmark.metadata)

        return cls(
            benchmark_id=benchmark.benchmark_id,
            name=benchmark.name,
            description=benchmark.description,
            format_version=benchmark.format_version,
            question_count=benchmark.question_count,
            created_at=benchmark.created_at,
            questions_json=questions_json,
            metadata_json=metadata_json,
        )

    def to_domain(self) -> PreprocessedBenchmark:
        """Convert BenchmarkModel to domain PreprocessedBenchmark entity.

        Returns:
            Domain PreprocessedBenchmark entity
        """
        # Deserialize questions from JSON
        questions_data = json.loads(self.questions_json)
        questions = [
            Question.from_dict(question_data) for question_data in questions_data
        ]

        # Deserialize metadata from JSON
        metadata = json.loads(self.metadata_json)

        return PreprocessedBenchmark(
            benchmark_id=self.benchmark_id,
            name=self.name,
            description=self.description,
            questions=questions,
            metadata=metadata,
            created_at=self.created_at,
            question_count=self.question_count,
            format_version=self.format_version,
        )
