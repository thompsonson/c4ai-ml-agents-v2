"""Application layer test fixtures."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from ml_agents_v2.core.domain.entities.evaluation import Evaluation
from ml_agents_v2.core.domain.entities.preprocessed_benchmark import (
    PreprocessedBenchmark,
)
from ml_agents_v2.core.domain.value_objects.agent_config import AgentConfig
from ml_agents_v2.core.domain.value_objects.answer import Answer
from ml_agents_v2.core.domain.value_objects.evaluation_results import EvaluationResults
from ml_agents_v2.core.domain.value_objects.question import Question
from ml_agents_v2.core.domain.value_objects.reasoning_trace import ReasoningTrace


@pytest.fixture
def sample_agent_config():
    """Create a sample agent configuration."""
    return AgentConfig(
        agent_type="chain_of_thought",
        model_provider="anthropic",
        model_name="claude-3-sonnet",
        model_parameters={"temperature": 1.0, "max_tokens": 1000},
        agent_parameters={"timeout_seconds": 30},
    )


@pytest.fixture
def sample_questions():
    """Create sample questions for testing."""
    return [
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
            metadata={"difficulty": "easy"},
        ),
    ]


@pytest.fixture
def sample_benchmark(sample_questions):
    """Create a sample preprocessed benchmark."""
    return PreprocessedBenchmark(
        benchmark_id=uuid.uuid4(),
        name="TEST_BENCHMARK",
        description="A test benchmark",
        format_version="1.0",
        questions=sample_questions,
        question_count=len(sample_questions),
        metadata={"category": "test"},
        created_at=datetime.now(),
    )


@pytest.fixture
def sample_evaluation(sample_agent_config, sample_benchmark):
    """Create a sample evaluation in pending state."""
    return Evaluation(
        evaluation_id=uuid.uuid4(),
        agent_config=sample_agent_config,
        preprocessed_benchmark_id=sample_benchmark.benchmark_id,
        status="pending",
        created_at=datetime.now(),
        started_at=None,
        completed_at=None,
        results=None,
        failure_reason=None,
    )


@pytest.fixture
def sample_evaluation_results():
    """Create sample evaluation results."""
    from ml_agents_v2.core.domain.value_objects.evaluation_results import QuestionResult

    detailed_results = [
        QuestionResult(
            question_id="q1",
            question_text="What is 2+2?",
            expected_answer="4",
            actual_answer="4",
            is_correct=True,
        ),
        QuestionResult(
            question_id="q2",
            question_text="What is the capital of France?",
            expected_answer="Paris",
            actual_answer="Paris",
            is_correct=True,
        ),
    ]

    return EvaluationResults(
        total_questions=2,
        correct_answers=2,
        accuracy=100.0,
        average_execution_time=1.5,
        error_count=0,
        detailed_results=detailed_results,
        summary_statistics={},
    )


@pytest.fixture
def sample_answer():
    """Create a sample answer."""
    return Answer(
        extracted_answer="4",
        raw_response="Let me think step by step. 2+2 equals 4.",
        reasoning_trace=ReasoningTrace(
            approach_type="chain_of_thought",
            reasoning_text="Let me think step by step. 2+2 equals 4.",
            metadata={},
        ),
        execution_time=1.2,
        confidence=0.95,
    )


@pytest.fixture
def mock_evaluation_repository():
    """Create a mock evaluation repository."""
    repo = Mock()
    repo.save = Mock()
    repo.get_by_id = Mock()
    repo.update = Mock()
    repo.list_all = Mock(return_value=[])
    repo.list_by_status = Mock(return_value=[])
    return repo


@pytest.fixture
def mock_benchmark_repository(sample_benchmark):
    """Create a mock benchmark repository."""
    repo = Mock()
    repo.get_by_name = Mock(return_value=sample_benchmark)
    repo.get_by_id = Mock(return_value=sample_benchmark)
    repo.list_all = Mock(return_value=[sample_benchmark])
    return repo


@pytest.fixture
def mock_reasoning_agent():
    """Create a mock reasoning agent."""
    agent = AsyncMock()
    agent.answer_question = AsyncMock()
    agent.validate_config = Mock(return_value=True)
    return agent


@pytest.fixture
def mock_reasoning_agent_factory(mock_reasoning_agent):
    """Create a mock reasoning agent factory."""
    factory = Mock()
    factory.create_service = Mock(return_value=mock_reasoning_agent)
    factory.is_agent_type_supported = Mock(return_value=True)
    factory.get_supported_agent_types = Mock(return_value=["chain_of_thought", "none"])
    return factory
