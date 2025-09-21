"""Tests for SQLAlchemy database models."""

import uuid
from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ml_agents_v2.core.domain.entities.evaluation import Evaluation
from ml_agents_v2.core.domain.entities.preprocessed_benchmark import (
    PreprocessedBenchmark,
)
from ml_agents_v2.core.domain.value_objects.agent_config import AgentConfig
from ml_agents_v2.core.domain.value_objects.question import Question
from ml_agents_v2.infrastructure.database.base import Base
from ml_agents_v2.infrastructure.database.models.benchmark import BenchmarkModel
from ml_agents_v2.infrastructure.database.models.evaluation import EvaluationModel


class TestDatabaseModels:
    """Test SQLAlchemy model mappings for domain entities."""

    @pytest.fixture
    def engine(self):
        """Create in-memory SQLite engine for testing."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        return engine

    @pytest.fixture
    def session(self, engine):
        """Create database session for testing."""
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()

    def test_evaluation_model_maps_from_domain_entity(self, session):
        """Test that EvaluationModel can be created from domain Evaluation entity."""
        # Create domain entity
        agent_config = AgentConfig(
            agent_type="none",
            model_provider="openrouter",
            model_name="meta-llama/llama-3.1-8b-instruct",
            model_parameters={"temperature": 0.1, "max_tokens": 800},
            agent_parameters={},
        )

        evaluation = Evaluation(
            evaluation_id=uuid.uuid4(),
            agent_config=agent_config,
            preprocessed_benchmark_id=uuid.uuid4(),
            status="pending",
            created_at=datetime.now(),
            started_at=None,
            completed_at=None,
            results=None,
            failure_reason=None,
        )

        # Convert to database model
        model = EvaluationModel.from_domain(evaluation)

        # Verify mapping
        assert model.evaluation_id == evaluation.evaluation_id
        assert model.status == evaluation.status
        assert model.created_at == evaluation.created_at
        assert model.started_at == evaluation.started_at
        assert model.completed_at == evaluation.completed_at
        assert model.preprocessed_benchmark_id == evaluation.preprocessed_benchmark_id

        # Agent config should be stored as JSON
        assert isinstance(model.agent_config_json, str)

        # Save to database
        session.add(model)
        session.commit()

        # Verify it can be retrieved
        retrieved = (
            session.query(EvaluationModel)
            .filter_by(evaluation_id=evaluation.evaluation_id)
            .first()
        )
        assert retrieved is not None

    def test_evaluation_model_maps_to_domain_entity(self, session):
        """Test that EvaluationModel can be converted back to domain entity."""
        # This test will verify the reverse mapping
        pass

    def test_benchmark_model_maps_from_domain_entity(self, session):
        """Test that BenchmarkModel can be created from domain PreprocessedBenchmark."""
        # Create domain entity
        questions = [
            Question(
                id="q1",
                text="What is 2+2?",
                expected_answer="4",
                metadata={"difficulty": "easy"},
            ),
            Question(
                id="q2",
                text="What is the capital of France?",
                expected_answer="Paris",
                metadata={"category": "geography"},
            ),
        ]

        benchmark = PreprocessedBenchmark(
            benchmark_id=uuid.uuid4(),
            name="Test Benchmark",
            description="A test benchmark for unit testing",
            questions=questions,
            metadata={"version": "1.0", "created_by": "test"},
            created_at=datetime.now(),
            question_count=len(questions),
            format_version="1.0",
        )

        # Convert to database model
        model = BenchmarkModel.from_domain(benchmark)

        # Verify mapping
        assert model.benchmark_id == benchmark.benchmark_id
        assert model.name == benchmark.name
        assert model.description == benchmark.description
        assert model.question_count == benchmark.question_count
        assert model.format_version == benchmark.format_version
        assert model.created_at == benchmark.created_at

        # Questions should be stored as JSON
        assert isinstance(model.questions_json, str)
        assert isinstance(model.metadata_json, str)

        # Save to database
        session.add(model)
        session.commit()

        # Verify it can be retrieved
        retrieved = (
            session.query(BenchmarkModel)
            .filter_by(benchmark_id=benchmark.benchmark_id)
            .first()
        )
        assert retrieved is not None

    def test_benchmark_model_maps_to_domain_entity(self, session):
        """Test that BenchmarkModel can be converted back to domain entity."""
        # This test will verify the reverse mapping
        pass
