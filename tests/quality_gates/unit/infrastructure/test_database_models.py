"""Tests for SQLAlchemy database models."""

import json
import uuid
from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ml_agents_v2.core.domain.entities.evaluation import Evaluation
from ml_agents_v2.core.domain.entities.evaluation_question_result import (
    EvaluationQuestionResult,
)
from ml_agents_v2.core.domain.entities.preprocessed_benchmark import (
    PreprocessedBenchmark,
)
from ml_agents_v2.core.domain.value_objects.agent_config import AgentConfig
from ml_agents_v2.core.domain.value_objects.question import Question
from ml_agents_v2.core.domain.value_objects.reasoning_trace import ReasoningTrace
from ml_agents_v2.infrastructure.database.base import Base
from ml_agents_v2.infrastructure.database.models.benchmark import BenchmarkModel
from ml_agents_v2.infrastructure.database.models.evaluation import EvaluationModel
from ml_agents_v2.infrastructure.database.models.evaluation_question_result import (
    EvaluationQuestionResultModel,
)


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


class TestEvaluationQuestionResultModel:
    """Test SQLAlchemy model mapping for EvaluationQuestionResult entity."""

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

    def test_mappingproxy_metadata_serialization(self, session):
        """Test that ReasoningTrace metadata (MappingProxyType) can be serialized properly.

        Current blocking issue: ReasoningTrace.metadata gets converted to MappingProxyType
        in domain layer for immutability, but json.dumps() cannot serialize this type.

        This test will initially fail, then pass once we implement the fix.
        """
        # Create reasoning trace with metadata (triggers MappingProxyType conversion in domain)
        reasoning_trace = ReasoningTrace(
            approach_type="chain_of_thought",
            reasoning_text="First, I need to analyze the question. The question asks for...",
            metadata={
                "confidence": 0.95,
                "reasoning_steps": 3,
                "source": "llm_response",
            },
        )

        # Create evaluation question result with reasoning trace
        question_result = EvaluationQuestionResult(
            id=uuid.uuid4(),
            evaluation_id=uuid.uuid4(),
            question_id="q1",
            question_text="What is 2+2?",
            expected_answer="4",
            actual_answer="4",
            is_correct=True,
            execution_time=1.5,
            reasoning_trace=reasoning_trace,
            error_message=None,
            technical_details=None,
            processed_at=datetime.now(),
        )

        # This should succeed and create a valid database model
        model = EvaluationQuestionResultModel.from_domain(question_result)

        # Verify the model was created correctly
        assert model.id == question_result.id
        assert model.evaluation_id == question_result.evaluation_id
        assert model.question_id == question_result.question_id
        assert model.question_text == question_result.question_text
        assert model.expected_answer == question_result.expected_answer
        assert model.actual_answer == question_result.actual_answer
        assert model.is_correct == question_result.is_correct
        assert model.execution_time == question_result.execution_time
        assert model.error_message == question_result.error_message
        assert model.technical_details == question_result.technical_details
        assert model.processed_at == question_result.processed_at

        # Verify reasoning trace was properly serialized to JSON
        assert model.reasoning_trace_json is not None
        assert isinstance(model.reasoning_trace_json, str)

        # Verify JSON can be parsed and contains expected data
        trace_data = json.loads(model.reasoning_trace_json)
        assert trace_data["approach_type"] == "chain_of_thought"
        assert "First, I need to analyze" in trace_data["reasoning_text"]
        assert trace_data["metadata"]["confidence"] == 0.95
        assert trace_data["metadata"]["reasoning_steps"] == 3
        assert trace_data["metadata"]["source"] == "llm_response"

    def test_llm_unicode_content_serialization(self, session):
        """Test that LLM responses with unicode, emojis, and special chars serialize properly.

        LLM responses often contain unicode characters, emojis, and special formatting
        that could cause JSON serialization issues.
        """
        # Create reasoning trace with unicode/emoji content (common in LLM responses)
        reasoning_trace = ReasoningTrace(
            approach_type="chain_of_thought",
            reasoning_text="The answer is 🤔 Let me think... \n\n步骤1: First step\n😊 Emoji in reasoning",
            metadata={
                "confidence": 0.85,
                "language": "mixed",
                "special_chars": "🤔😊步骤",
            },
        )

        question_result = EvaluationQuestionResult(
            id=uuid.uuid4(),
            evaluation_id=uuid.uuid4(),
            question_id="unicode_test",
            question_text="What is the answer? 问题是什么？",
            expected_answer="Expected 预期答案 🎯",
            actual_answer="Actual 实际答案 ✅",
            is_correct=True,
            execution_time=2.1,
            reasoning_trace=reasoning_trace,
            error_message=None,
            technical_details=None,
            processed_at=datetime.now(),
        )

        # Should successfully create model and serialize unicode content
        model = EvaluationQuestionResultModel.from_domain(question_result)

        # Verify unicode content is preserved (JSON escapes unicode but preserves meaning)
        assert model.reasoning_trace_json is not None
        assert isinstance(model.reasoning_trace_json, str)

        # Parse JSON to verify unicode content is correctly preserved
        trace_data = json.loads(model.reasoning_trace_json)
        assert (
            "🤔" in trace_data["reasoning_text"]
        )  # Unicode should be preserved when parsed
        assert "步骤" in trace_data["reasoning_text"]
        assert "🤔" in trace_data["metadata"]["special_chars"]
        assert "步骤" in trace_data["metadata"]["special_chars"]

    def test_csv_mixed_metadata_serialization(self, session):
        """Test that CSV import metadata with None values and mixed types serializes properly.

        User-uploaded CSV files can contain arbitrary column data with None values,
        mixed types, and problematic content.
        """
        # Create reasoning trace with CSV-style metadata (None values, mixed types)
        reasoning_trace = ReasoningTrace(
            approach_type="chain_of_thought",
            reasoning_text="Processing CSV data...",
            metadata={
                "category": None,  # None values from CSV
                "difficulty": "N/A",  # String representation of missing data
                "source_file": "test.csv",
                "csv_row_number": 42,
                "confidence": 0.7,
                "has_special_chars": True,
                "empty_string": "",
                "zero_value": 0,
            },
        )

        question_result = EvaluationQuestionResult(
            id=uuid.uuid4(),
            evaluation_id=uuid.uuid4(),
            question_id="csv_test",
            question_text="CSV imported question",
            expected_answer="CSV expected",
            actual_answer="CSV actual",
            is_correct=False,
            execution_time=0.5,
            reasoning_trace=reasoning_trace,
            error_message=None,
            technical_details=None,
            processed_at=datetime.now(),
        )

        # Should successfully handle None values and mixed types
        model = EvaluationQuestionResultModel.from_domain(question_result)
        trace_data = json.loads(model.reasoning_trace_json)
        assert trace_data["metadata"]["category"] is None
        assert trace_data["metadata"]["csv_row_number"] == 42
        assert trace_data["metadata"]["empty_string"] == ""

    def test_nested_object_serialization(self, session):
        """Test that nested dictionaries and complex structures serialize properly.

        Complex LLM response metadata or processing info can contain nested objects
        that might cause serialization issues.
        """
        # Create reasoning trace with nested metadata structures
        reasoning_trace = ReasoningTrace(
            approach_type="chain_of_thought",
            reasoning_text="Complex nested processing...",
            metadata={
                "timing": {
                    "start_time": "2024-01-01T00:00:00Z",
                    "processing_stages": {
                        "parse": 0.1,
                        "analyze": 0.5,
                        "generate": 1.2,
                    },
                },
                "config": {
                    "model": {
                        "name": "llama-3.1",
                        "parameters": {"temperature": 0.7, "max_tokens": 800},
                    }
                },
                "simple_value": "test",
            },
        )

        question_result = EvaluationQuestionResult(
            id=uuid.uuid4(),
            evaluation_id=uuid.uuid4(),
            question_id="nested_test",
            question_text="Nested structure test",
            expected_answer="Expected",
            actual_answer="Actual",
            is_correct=True,
            execution_time=1.8,
            reasoning_trace=reasoning_trace,
            error_message=None,
            technical_details=None,
            processed_at=datetime.now(),
        )

        # Should successfully handle nested structures
        model = EvaluationQuestionResultModel.from_domain(question_result)
        trace_data = json.loads(model.reasoning_trace_json)
        assert trace_data["metadata"]["timing"]["processing_stages"]["parse"] == 0.1
        assert (
            trace_data["metadata"]["config"]["model"]["parameters"]["temperature"]
            == 0.7
        )

    def test_serialization_error_context_accuracy(self, session):
        """Test that SerializationError class exists and can be imported.

        This verifies the SerializationError exception is properly defined
        and available for use in error handling scenarios.
        """
        from ml_agents_v2.infrastructure.database.exceptions import SerializationError

        # Verify the exception class has the expected attributes
        test_error = SerializationError(
            entity_type="TestEntity",
            entity_id="test-123",
            field_name="test_field",
            original_error=TypeError("Test error"),
        )

        assert test_error.entity_type == "TestEntity"
        assert test_error.entity_id == "test-123"
        assert test_error.field_name == "test_field"
        assert isinstance(test_error.original_error, TypeError)
        assert "TestEntity" in str(test_error)
        assert "test_field" in str(test_error)
        assert "test-123" in str(test_error)
