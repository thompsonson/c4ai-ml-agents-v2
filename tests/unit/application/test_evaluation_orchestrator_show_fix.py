"""Unit tests for evaluation orchestrator show command fix."""

import uuid
from datetime import datetime
from unittest.mock import Mock

import pytest

from ml_agents_v2.core.application.services.evaluation_orchestrator import (
    EvaluationOrchestrator,
)
from ml_agents_v2.core.domain.entities.evaluation import Evaluation
from ml_agents_v2.core.domain.entities.evaluation_question_result import (
    EvaluationQuestionResult,
)
from ml_agents_v2.core.domain.entities.preprocessed_benchmark import (
    PreprocessedBenchmark,
)
from ml_agents_v2.core.domain.value_objects.agent_config import AgentConfig
from ml_agents_v2.core.domain.value_objects.evaluation_results import (
    EvaluationResults,
)


class TestEvaluationOrchestratorShowFix:
    """Test that get_evaluation_results computes from question results when needed."""

    def test_get_evaluation_results_computes_from_question_results_when_results_none(
        self,
    ):
        """Test that get_evaluation_results computes results from question results when evaluation.results is None."""
        # Arrange
        evaluation_id = uuid.uuid4()
        benchmark_id = uuid.uuid4()

        # Mock repositories
        evaluation_repo = Mock()
        question_result_repo = Mock()
        benchmark_repo = Mock()
        reasoning_service = Mock()
        domain_services = {}

        # Create evaluation with results=None (the bug scenario)
        evaluation = Evaluation(
            evaluation_id=evaluation_id,
            agent_config=AgentConfig(
                agent_type="chain_of_thought",
                model_provider="anthropic",
                model_name="claude-3-sonnet",
                model_parameters={"temperature": 1.0},
                agent_parameters={},
            ),
            preprocessed_benchmark_id=benchmark_id,
            status="completed",
            created_at=datetime.now(),
            started_at=datetime.now(),
            completed_at=datetime.now(),
            results=None,  # This is the key - results is None
            failure_reason=None,
        )

        # Mock benchmark - Create with actual questions to satisfy validation
        from ml_agents_v2.core.domain.value_objects.question import Question

        questions = [
            Question(id="q1", text="Question 1", expected_answer="A", metadata={}),
            Question(id="q2", text="Question 2", expected_answer="B", metadata={}),
        ]

        benchmark = PreprocessedBenchmark(
            benchmark_id=benchmark_id,
            name="GPQA",
            description="Test benchmark",
            questions=questions,
            metadata={},
            created_at=datetime.now(),
            question_count=2,
            format_version="1.0",
        )

        # Create mock question results
        question_results = [
            EvaluationQuestionResult.create_successful(
                evaluation_id=evaluation_id,
                question_id="q1",
                question_text="Question 1",
                expected_answer="A",
                actual_answer="A",
                is_correct=True,
                execution_time=1.0,
                reasoning_trace=None,
            ),
            EvaluationQuestionResult.create_failed(
                evaluation_id=evaluation_id,
                question_id="q2",
                question_text="Question 2",
                expected_answer="B",
                execution_time=2.0,
                error_message="Wrong answer",
            ),
        ]

        # Setup repository mocks
        evaluation_repo.get_by_id.return_value = evaluation
        benchmark_repo.get_by_id.return_value = benchmark
        question_result_repo.get_by_evaluation_id.return_value = question_results

        # Create orchestrator
        orchestrator = EvaluationOrchestrator(
            evaluation_repository=evaluation_repo,
            evaluation_question_result_repository=question_result_repo,
            benchmark_repository=benchmark_repo,
            reasoning_infrastructure_service=reasoning_service,
            domain_service_registry=domain_services,
        )

        # Act
        result = orchestrator.get_evaluation_results(evaluation_id)

        # Assert
        assert result.evaluation_id == evaluation_id
        assert result.status == "completed"
        assert result.benchmark_name == "GPQA"
        assert result.agent_type == "chain_of_thought"
        assert result.model_name == "claude-3-sonnet"

        # Verify computed results from question results
        assert result.total_questions == 2
        assert result.correct_answers == 1
        assert result.accuracy == 50.0  # 1 out of 2 correct
        assert result.error_count == 1  # One failed question
        assert result.average_time_per_question == 1.5  # (1.0 + 2.0) / 2

        # Verify repository calls
        evaluation_repo.get_by_id.assert_called_once_with(evaluation_id)
        benchmark_repo.get_by_id.assert_called_once_with(benchmark_id)
        question_result_repo.get_by_evaluation_id.assert_called_once_with(evaluation_id)

    def test_get_evaluation_results_uses_stored_results_when_available(self):
        """Test that get_evaluation_results uses stored results when available."""
        # Arrange
        evaluation_id = uuid.uuid4()
        benchmark_id = uuid.uuid4()

        # Mock repositories
        evaluation_repo = Mock()
        question_result_repo = Mock()
        benchmark_repo = Mock()
        reasoning_service = Mock()
        domain_services = {}

        # Create stored results with all required fields
        from ml_agents_v2.core.domain.value_objects.evaluation_results import (
            QuestionResult,
        )

        question_results_detailed = [
            QuestionResult(
                question_id="q1",
                question_text="Question 1",
                expected_answer="A",
                actual_answer="A",
                is_correct=True,
            )
            for _ in range(75)
        ] + [
            QuestionResult(
                question_id="q2",
                question_text="Question 2",
                expected_answer="B",
                actual_answer="C",
                is_correct=False,
            )
            for _ in range(25)
        ]

        stored_results = EvaluationResults(
            total_questions=100,
            correct_answers=75,
            accuracy=75.0,
            average_execution_time=1.5,
            error_count=5,
            detailed_results=question_results_detailed,
            summary_statistics={},
        )

        # Create evaluation with stored results
        evaluation = Evaluation(
            evaluation_id=evaluation_id,
            agent_config=AgentConfig(
                agent_type="chain_of_thought",
                model_provider="anthropic",
                model_name="claude-3-sonnet",
                model_parameters={"temperature": 1.0},
                agent_parameters={},
            ),
            preprocessed_benchmark_id=benchmark_id,
            status="completed",
            created_at=datetime.now(),
            started_at=datetime.now(),
            completed_at=datetime.now(),
            results=stored_results,  # Stored results available
            failure_reason=None,
        )

        # Mock benchmark with proper questions
        from ml_agents_v2.core.domain.value_objects.question import Question

        questions = [
            Question(id=f"q{i}", text=f"Question {i}", expected_answer="A", metadata={})
            for i in range(100)
        ]

        benchmark = PreprocessedBenchmark(
            benchmark_id=benchmark_id,
            name="GPQA",
            description="Test benchmark",
            questions=questions,
            metadata={},
            created_at=datetime.now(),
            question_count=100,
            format_version="1.0",
        )

        # Setup repository mocks
        evaluation_repo.get_by_id.return_value = evaluation
        benchmark_repo.get_by_id.return_value = benchmark

        # Create orchestrator
        orchestrator = EvaluationOrchestrator(
            evaluation_repository=evaluation_repo,
            evaluation_question_result_repository=question_result_repo,
            benchmark_repository=benchmark_repo,
            reasoning_infrastructure_service=reasoning_service,
            domain_service_registry=domain_services,
        )

        # Act
        result = orchestrator.get_evaluation_results(evaluation_id)

        # Assert - should use stored results
        assert result.total_questions == 100
        assert result.correct_answers == 75
        assert result.accuracy == 75.0
        assert result.error_count == 5
        assert result.average_time_per_question == 1.5

        # Should NOT call question_result_repo since stored results are available
        question_result_repo.get_by_evaluation_id.assert_not_called()

    def test_get_evaluation_results_fails_when_no_question_results_and_no_stored_results(
        self,
    ):
        """Test that get_evaluation_results fails when there are no question results and no stored results."""
        # Arrange
        evaluation_id = uuid.uuid4()
        benchmark_id = uuid.uuid4()

        # Mock repositories
        evaluation_repo = Mock()
        question_result_repo = Mock()
        benchmark_repo = Mock()
        reasoning_service = Mock()
        domain_services = {}

        # Create evaluation with no results
        evaluation = Evaluation(
            evaluation_id=evaluation_id,
            agent_config=AgentConfig(
                agent_type="chain_of_thought",
                model_provider="anthropic",
                model_name="claude-3-sonnet",
                model_parameters={"temperature": 1.0},
                agent_parameters={},
            ),
            preprocessed_benchmark_id=benchmark_id,
            status="completed",
            created_at=datetime.now(),
            started_at=datetime.now(),
            completed_at=datetime.now(),
            results=None,
            failure_reason=None,
        )

        # Mock benchmark with one question to satisfy validation
        from ml_agents_v2.core.domain.value_objects.question import Question

        questions = [
            Question(id="q1", text="Question 1", expected_answer="A", metadata={}),
        ]

        benchmark = PreprocessedBenchmark(
            benchmark_id=benchmark_id,
            name="GPQA",
            description="Test benchmark",
            questions=questions,
            metadata={},
            created_at=datetime.now(),
            question_count=1,
            format_version="1.0",
        )

        # Setup repository mocks
        evaluation_repo.get_by_id.return_value = evaluation
        benchmark_repo.get_by_id.return_value = benchmark
        question_result_repo.get_by_evaluation_id.return_value = (
            []
        )  # No question results

        # Create orchestrator
        orchestrator = EvaluationOrchestrator(
            evaluation_repository=evaluation_repo,
            evaluation_question_result_repository=question_result_repo,
            benchmark_repository=benchmark_repo,
            reasoning_infrastructure_service=reasoning_service,
            domain_service_registry=domain_services,
        )

        # Act & Assert
        from ml_agents_v2.core.application.services.exceptions import (
            InvalidEvaluationStateError,
        )

        with pytest.raises(InvalidEvaluationStateError, match="no question results"):
            orchestrator.get_evaluation_results(evaluation_id)
