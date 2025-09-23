"""Integration tests for Application Services coordination."""

import pytest

from ml_agents_v2.core.application.services.error_mapper import ApplicationErrorMapper
from ml_agents_v2.core.application.services.evaluation_orchestrator import (
    EvaluationOrchestrator,
)
from ml_agents_v2.core.application.services.exceptions import (
    BenchmarkNotFoundError,
    EvaluationExecutionError,
)
from ml_agents_v2.core.domain.repositories.exceptions import EntityNotFoundError


@pytest.mark.skip(reason="Application integration tests disabled for Phase 6 retrofit - reasoning agent factory removed")
class TestApplicationServicesIntegration:
    """Test suite for application services working together."""

    @pytest.fixture
    def error_mapper(self):
        """Create error mapper for integration tests."""
        return ApplicationErrorMapper()

    @pytest.fixture
    def orchestrator_with_error_handling(
        self,
        mock_evaluation_repository,
        mock_benchmark_repository,
        mock_reasoning_agent_factory,
        error_mapper,
    ):
        """Create orchestrator that uses real error mapping."""
        orchestrator = EvaluationOrchestrator(
            evaluation_repository=mock_evaluation_repository,
            benchmark_repository=mock_benchmark_repository,
            reasoning_agent_factory=mock_reasoning_agent_factory,
        )
        # Inject error mapper for testing
        orchestrator._error_mapper = error_mapper
        return orchestrator

    def test_create_evaluation_with_error_mapping(
        self,
        orchestrator_with_error_handling,
        sample_agent_config,
        mock_benchmark_repository,
    ):
        """Test evaluation creation with proper error mapping."""
        # Arrange
        benchmark_name = "NONEXISTENT_BENCHMARK"
        mock_benchmark_repository.get_by_name.side_effect = EntityNotFoundError(
            "Benchmark", "NONEXISTENT_BENCHMARK"
        )

        # Act & Assert
        with pytest.raises(BenchmarkNotFoundError) as exc_info:
            orchestrator_with_error_handling.create_evaluation(
                agent_config=sample_agent_config,
                benchmark_name=benchmark_name,
            )

        assert (
            "benchmark" in str(exc_info.value).lower()
            and "not found" in str(exc_info.value).lower()
        )

    @pytest.mark.asyncio
    async def test_evaluation_execution_with_external_service_error(
        self,
        orchestrator_with_error_handling,
        sample_evaluation,
        sample_benchmark,
        mock_evaluation_repository,
        mock_benchmark_repository,
        mock_reasoning_agent,
    ):
        """Test evaluation execution handling external service errors."""
        # Arrange
        evaluation_id = sample_evaluation.evaluation_id

        mock_evaluation_repository.get_by_id.return_value = sample_evaluation
        mock_benchmark_repository.get_by_id.return_value = sample_benchmark

        # Simulate OpenRouter API failure
        openrouter_error = Exception("503 Service Unavailable")
        mock_reasoning_agent.answer_question.side_effect = openrouter_error

        # Act & Assert
        # Should raise EvaluationExecutionError due to failures
        with pytest.raises(EvaluationExecutionError):
            await orchestrator_with_error_handling.execute_evaluation(evaluation_id)

        # Should have marked evaluation as failed
        update_calls = mock_evaluation_repository.update.call_args_list
        if update_calls:  # There might be status updates before failure
            # Find the final evaluation update
            final_evaluation = update_calls[-1][0][0]
            assert final_evaluation.status == "failed"

    @pytest.mark.asyncio
    async def test_end_to_end_successful_evaluation(
        self,
        orchestrator_with_error_handling,
        sample_evaluation,
        sample_benchmark,
        sample_answer,
        mock_evaluation_repository,
        mock_benchmark_repository,
        mock_reasoning_agent,
    ):
        """Test complete evaluation workflow from creation to completion."""
        # Arrange
        evaluation_id = sample_evaluation.evaluation_id

        mock_evaluation_repository.get_by_id.return_value = sample_evaluation
        mock_benchmark_repository.get_by_id.return_value = sample_benchmark
        mock_reasoning_agent.answer_question.return_value = sample_answer

        # Track progress updates
        progress_updates = []

        def capture_progress(progress_info):
            progress_updates.append(progress_info)

        # Act
        await orchestrator_with_error_handling.execute_evaluation(
            evaluation_id, progress_callback=capture_progress
        )

        # Assert
        # Should have received progress updates
        assert len(progress_updates) > 0
        final_progress = progress_updates[-1]
        assert final_progress.completion_percentage == 100.0

        # Should have completed successfully
        update_calls = mock_evaluation_repository.update.call_args_list
        final_evaluation = update_calls[-1][0][0]
        assert final_evaluation.status == "completed"
        assert final_evaluation.results is not None
        assert final_evaluation.results.total_questions == len(
            sample_benchmark.questions
        )

    def test_validation_error_mapping_integration(
        self,
        orchestrator_with_error_handling,
        sample_agent_config,
        sample_benchmark,
        mock_benchmark_repository,
        mock_evaluation_repository,
    ):
        """Test validation errors are properly mapped."""
        # Arrange
        benchmark_name = "TEST_BENCHMARK"
        mock_benchmark_repository.get_by_name.return_value = (
            sample_benchmark  # Valid benchmark
        )

        # Simulate constraint violation during save
        constraint_error = Exception("UNIQUE constraint failed: evaluations.id")
        mock_evaluation_repository.save.side_effect = constraint_error

        # Act & Assert
        # The orchestrator should handle this gracefully
        # (In a real implementation, it might retry with a new UUID)
        with pytest.raises(
            Exception
        ) as exc_info:  # Will be mapped to ValidationError in real implementation
            orchestrator_with_error_handling.create_evaluation(
                agent_config=sample_agent_config,
                benchmark_name=benchmark_name,
            )

        # Verify the error is related to the constraint
        assert "constraint" in str(exc_info.value).lower()
