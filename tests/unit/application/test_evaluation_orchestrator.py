"""Tests for EvaluationOrchestrator application service."""

import uuid
from dataclasses import replace
from datetime import datetime

import pytest

from ml_agents_v2.core.application.services.evaluation_orchestrator import (
    EvaluationOrchestrator,
)
from ml_agents_v2.core.application.services.exceptions import (
    BenchmarkNotFoundError,
    EvaluationNotFoundError,
)
from ml_agents_v2.core.domain.repositories.exceptions import EntityNotFoundError


@pytest.mark.skip(reason="EvaluationOrchestrator tests disabled for Phase 6 retrofit - reasoning agent factory removed")
class TestEvaluationOrchestrator:
    """Test suite for EvaluationOrchestrator."""

    @pytest.fixture
    def orchestrator(
        self,
        mock_evaluation_repository,
        mock_benchmark_repository,
        mock_reasoning_agent_factory,
    ):
        """Create orchestrator with mocked dependencies."""
        return EvaluationOrchestrator(
            evaluation_repository=mock_evaluation_repository,
            benchmark_repository=mock_benchmark_repository,
            reasoning_agent_factory=mock_reasoning_agent_factory,
        )

    def test_create_evaluation_success(
        self,
        orchestrator,
        sample_agent_config,
        sample_benchmark,
        mock_benchmark_repository,
        mock_evaluation_repository,
    ):
        """Test successful evaluation creation."""
        # Arrange
        benchmark_name = "TEST_BENCHMARK"
        mock_benchmark_repository.get_by_name.return_value = sample_benchmark

        # Act
        evaluation_id = orchestrator.create_evaluation(
            agent_config=sample_agent_config,
            benchmark_name=benchmark_name,
        )

        # Assert
        assert isinstance(evaluation_id, uuid.UUID)
        mock_benchmark_repository.get_by_name.assert_called_once_with(benchmark_name)
        mock_evaluation_repository.save.assert_called_once()

        # Verify the evaluation was created with correct attributes
        saved_evaluation = mock_evaluation_repository.save.call_args[0][0]
        assert saved_evaluation.agent_config == sample_agent_config
        assert (
            saved_evaluation.preprocessed_benchmark_id == sample_benchmark.benchmark_id
        )
        assert saved_evaluation.status == "pending"

    def test_create_evaluation_benchmark_not_found(
        self,
        orchestrator,
        sample_agent_config,
        mock_benchmark_repository,
    ):
        """Test evaluation creation with non-existent benchmark."""
        # Arrange
        benchmark_name = "NONEXISTENT_BENCHMARK"
        mock_benchmark_repository.get_by_name.side_effect = EntityNotFoundError(
            "Benchmark", "NONEXISTENT_BENCHMARK"
        )

        # Act & Assert
        with pytest.raises(BenchmarkNotFoundError) as exc_info:
            orchestrator.create_evaluation(
                agent_config=sample_agent_config,
                benchmark_name=benchmark_name,
            )

        assert "not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_evaluation_basic_workflow(
        self,
        orchestrator,
        sample_evaluation,
        sample_benchmark,
        sample_answer,
        mock_evaluation_repository,
        mock_benchmark_repository,
        mock_reasoning_agent,
    ):
        """Test basic evaluation execution workflow."""
        # Arrange
        evaluation_id = sample_evaluation.evaluation_id

        # Mock repository responses
        mock_evaluation_repository.get_by_id.return_value = sample_evaluation
        mock_benchmark_repository.get_by_id.return_value = sample_benchmark

        # Mock reasoning agent response
        mock_reasoning_agent.answer_question.return_value = sample_answer

        # Act
        await orchestrator.execute_evaluation(evaluation_id)

        # Assert
        # Should have retrieved evaluation and benchmark
        mock_evaluation_repository.get_by_id.assert_called_with(evaluation_id)
        mock_benchmark_repository.get_by_id.assert_called_with(
            sample_evaluation.preprocessed_benchmark_id
        )

        # Should have processed questions
        assert mock_reasoning_agent.answer_question.call_count == len(
            sample_benchmark.questions
        )

        # Should have updated evaluation status multiple times (running -> completed)
        assert mock_evaluation_repository.update.call_count >= 2

        # Verify final evaluation state
        final_update_call = mock_evaluation_repository.update.call_args_list[-1]
        final_evaluation = final_update_call[0][0]
        assert final_evaluation.status == "completed"
        assert final_evaluation.results is not None

    def test_get_evaluation_status_success(
        self,
        orchestrator,
        sample_evaluation,
        mock_evaluation_repository,
    ):
        """Test successful evaluation status retrieval."""
        # Arrange
        evaluation_id = sample_evaluation.evaluation_id
        mock_evaluation_repository.get_by_id.return_value = sample_evaluation

        # Act
        status = orchestrator.get_evaluation_status(evaluation_id)

        # Assert
        assert status == "pending"
        mock_evaluation_repository.get_by_id.assert_called_once_with(evaluation_id)

    def test_get_evaluation_status_not_found(
        self,
        orchestrator,
        mock_evaluation_repository,
    ):
        """Test evaluation status retrieval for non-existent evaluation."""
        # Arrange
        evaluation_id = uuid.uuid4()
        mock_evaluation_repository.get_by_id.side_effect = EntityNotFoundError(
            "Evaluation", str(evaluation_id)
        )

        # Act & Assert
        with pytest.raises(EvaluationNotFoundError):
            orchestrator.get_evaluation_status(evaluation_id)

    def test_get_evaluation_results_success(
        self,
        orchestrator,
        sample_evaluation,
        sample_benchmark,
        sample_evaluation_results,
        mock_evaluation_repository,
        mock_benchmark_repository,
    ):
        """Test successful evaluation results retrieval."""
        # Arrange
        completed_evaluation = replace(
            sample_evaluation,
            status="completed",
            results=sample_evaluation_results,
            started_at=datetime.now(),
            completed_at=datetime.now(),
        )

        mock_evaluation_repository.get_by_id.return_value = completed_evaluation
        mock_benchmark_repository.get_by_id.return_value = sample_benchmark

        # Act
        summary = orchestrator.get_evaluation_results(
            completed_evaluation.evaluation_id
        )

        # Assert
        assert summary.evaluation_id == completed_evaluation.evaluation_id
        assert summary.agent_type == completed_evaluation.agent_config.agent_type
        assert summary.benchmark_name == sample_benchmark.name
        assert summary.accuracy == sample_evaluation_results.accuracy
        assert summary.total_questions == sample_evaluation_results.total_questions

    def test_list_evaluations_basic(
        self,
        orchestrator,
        sample_evaluation,
        sample_benchmark,
        mock_evaluation_repository,
        mock_benchmark_repository,
    ):
        """Test basic evaluation listing."""
        # Arrange
        mock_evaluation_repository.list_all.return_value = [sample_evaluation]
        mock_benchmark_repository.get_by_id.return_value = sample_benchmark

        # Act
        evaluation_infos = orchestrator.list_evaluations()

        # Assert
        assert len(evaluation_infos) == 1
        info = evaluation_infos[0]
        assert info.evaluation_id == sample_evaluation.evaluation_id
        assert info.agent_type == sample_evaluation.agent_config.agent_type
        assert info.benchmark_name == sample_benchmark.name
        assert info.status == sample_evaluation.status
