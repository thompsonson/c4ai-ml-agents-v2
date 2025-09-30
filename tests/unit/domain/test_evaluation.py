"""Tests for Evaluation entity."""

import uuid
from datetime import datetime

from ml_agents_v2.core.domain.entities.evaluation import Evaluation
from ml_agents_v2.core.domain.value_objects.agent_config import AgentConfig
from ml_agents_v2.core.domain.value_objects.evaluation_results import (
    EvaluationResults,
    QuestionResult,
)
from ml_agents_v2.core.domain.value_objects.failure_reason import FailureReason


class TestEvaluation:
    """Test suite for Evaluation entity."""

    def test_evaluation_creation(self) -> None:
        """Test Evaluation can be created with required attributes."""
        evaluation_id = uuid.uuid4()
        benchmark_id = uuid.uuid4()
        agent_config = AgentConfig(
            agent_type="none",
            model_provider="openai",
            model_name="gpt-4",
            model_parameters={"temperature": 0.7, "max_tokens": 1000},
            agent_parameters={"timeout_seconds": 30},
        )
        created_at = datetime.now()

        evaluation = Evaluation(
            evaluation_id=evaluation_id,
            agent_config=agent_config,
            preprocessed_benchmark_id=benchmark_id,
            status="pending",
            created_at=created_at,
            started_at=None,
            completed_at=None,
            results=None,
            failure_reason=None,
        )

        assert evaluation.evaluation_id == evaluation_id
        assert evaluation.agent_config == agent_config
        assert evaluation.preprocessed_benchmark_id == benchmark_id
        assert evaluation.status == "pending"
        assert evaluation.created_at == created_at
        assert evaluation.started_at is None
        assert evaluation.completed_at is None
        assert evaluation.results is None
        assert evaluation.failure_reason is None

    def test_evaluation_start_execution(self) -> None:
        """Test evaluation can transition from pending to running."""
        evaluation_id = uuid.uuid4()
        benchmark_id = uuid.uuid4()
        agent_config = AgentConfig(
            agent_type="none",
            model_provider="openai",
            model_name="gpt-4",
            model_parameters={"temperature": 0.7, "max_tokens": 1000},
            agent_parameters={"timeout_seconds": 30},
        )
        created_at = datetime.now()

        evaluation = Evaluation(
            evaluation_id=evaluation_id,
            agent_config=agent_config,
            preprocessed_benchmark_id=benchmark_id,
            status="pending",
            created_at=created_at,
            started_at=None,
            completed_at=None,
            results=None,
            failure_reason=None,
        )

        # Start execution
        started_evaluation = evaluation.start_execution()

        assert started_evaluation.status == "running"
        assert started_evaluation.started_at is not None
        assert started_evaluation.started_at >= created_at
        assert started_evaluation.completed_at is None
        assert started_evaluation.evaluation_id == evaluation_id

    def test_evaluation_complete(self) -> None:
        """Test evaluation can transition from running to completed (Phase 8 pattern)."""
        evaluation_id = uuid.uuid4()
        benchmark_id = uuid.uuid4()
        agent_config = AgentConfig(
            agent_type="none",
            model_provider="openai",
            model_name="gpt-4",
            model_parameters={"temperature": 0.7, "max_tokens": 1000},
            agent_parameters={"timeout_seconds": 30},
        )
        created_at = datetime.now()
        started_at = datetime.now()

        evaluation = Evaluation(
            evaluation_id=evaluation_id,
            agent_config=agent_config,
            preprocessed_benchmark_id=benchmark_id,
            status="running",
            created_at=created_at,
            started_at=started_at,
            completed_at=None,
            results=None,
            failure_reason=None,
        )

        # Complete without results (Phase 8 pattern - results computed from question results)
        completed_evaluation = evaluation.complete()

        assert completed_evaluation.status == "completed"
        assert completed_evaluation.completed_at is not None
        assert completed_evaluation.completed_at >= started_at
        assert (
            completed_evaluation.results is None
        )  # Phase 8: Results computed from question results
        assert completed_evaluation.failure_reason is None

    def test_evaluation_fail_with_reason(self) -> None:
        """Test evaluation can transition to failed state with failure reason."""
        evaluation_id = uuid.uuid4()
        benchmark_id = uuid.uuid4()
        agent_config = AgentConfig(
            agent_type="none",
            model_provider="openai",
            model_name="gpt-4",
            model_parameters={"temperature": 0.7, "max_tokens": 1000},
            agent_parameters={"timeout_seconds": 30},
        )
        created_at = datetime.now()
        started_at = datetime.now()

        evaluation = Evaluation(
            evaluation_id=evaluation_id,
            agent_config=agent_config,
            preprocessed_benchmark_id=benchmark_id,
            status="running",
            created_at=created_at,
            started_at=started_at,
            completed_at=None,
            results=None,
            failure_reason=None,
        )

        # Create failure reason
        failure_reason = FailureReason(
            category="network_timeout",
            description="Request timed out after 30 seconds",
            technical_details="ConnectionTimeout: No response received",
            occurred_at=datetime.now(),
            recoverable=True,
        )

        # Fail with reason
        failed_evaluation = evaluation.fail_with_reason(failure_reason)

        assert failed_evaluation.status == "failed"
        assert failed_evaluation.completed_at is not None
        assert failed_evaluation.failure_reason == failure_reason
        assert failed_evaluation.results is None

    def test_evaluation_can_be_modified_pending(self) -> None:
        """Test pending evaluation can be modified."""
        evaluation = self._create_test_evaluation(status="pending")
        assert evaluation.can_be_modified() is True

    def test_evaluation_can_be_modified_running(self) -> None:
        """Test running evaluation can be modified."""
        evaluation = self._create_test_evaluation(status="running")
        assert evaluation.can_be_modified() is True

    def test_evaluation_cannot_be_modified_completed(self) -> None:
        """Test completed evaluation cannot be modified."""
        evaluation = self._create_test_evaluation(status="completed")
        assert evaluation.can_be_modified() is False

    def test_evaluation_cannot_be_modified_failed(self) -> None:
        """Test failed evaluation cannot be modified."""
        evaluation = self._create_test_evaluation(status="failed")
        assert evaluation.can_be_modified() is False

    def test_evaluation_start_execution_invalid_state(self) -> None:
        """Test start_execution fails when not in pending state."""
        evaluation = self._create_test_evaluation(status="running")

        try:
            evaluation.start_execution()
            raise AssertionError("Expected ValueError for invalid state transition")
        except ValueError as e:
            assert "Cannot start execution" in str(e)
            assert "pending" in str(e)

    def test_evaluation_complete_invalid_state(self) -> None:
        """Test complete fails when not in running state (Phase 8 pattern)."""
        evaluation = self._create_test_evaluation(status="pending")

        try:
            evaluation.complete()
            raise AssertionError("Expected ValueError for invalid state transition")
        except ValueError as e:
            assert "Cannot complete evaluation" in str(e)
            assert "running" in str(e)

    def test_evaluation_fail_with_reason_invalid_state(self) -> None:
        """Test fail_with_reason fails when not in valid state."""
        evaluation = self._create_test_evaluation(status="completed")

        failure_reason = FailureReason(
            category="network_timeout",
            description="Request timed out",
            technical_details="Timeout error",
            occurred_at=datetime.now(),
            recoverable=True,
        )

        try:
            evaluation.fail_with_reason(failure_reason)
            raise AssertionError("Expected ValueError for invalid state transition")
        except ValueError as e:
            assert "Cannot fail evaluation" in str(e)

    def test_evaluation_validation_invalid_status(self) -> None:
        """Test Evaluation validation fails for invalid status."""
        evaluation_id = uuid.uuid4()
        benchmark_id = uuid.uuid4()
        agent_config = AgentConfig(
            agent_type="none",
            model_provider="openai",
            model_name="gpt-4",
            model_parameters={"temperature": 0.7, "max_tokens": 1000},
            agent_parameters={"timeout_seconds": 30},
        )

        try:
            Evaluation(
                evaluation_id=evaluation_id,
                agent_config=agent_config,
                preprocessed_benchmark_id=benchmark_id,
                status="invalid_status",
                created_at=datetime.now(),
                started_at=None,
                completed_at=None,
                results=None,
                failure_reason=None,
            )
            raise AssertionError("Expected ValueError for invalid status")
        except ValueError as e:
            assert "Invalid status" in str(e)

    def test_evaluation_validation_completed_phase8_pattern(self) -> None:
        """Test completed evaluation can have None results (Phase 8 pattern)."""
        evaluation_id = uuid.uuid4()
        benchmark_id = uuid.uuid4()
        agent_config = AgentConfig(
            agent_type="none",
            model_provider="openai",
            model_name="gpt-4",
            model_parameters={"temperature": 0.7, "max_tokens": 1000},
            agent_parameters={"timeout_seconds": 30},
        )

        # This should NOT raise an error in Phase 8 - results computed from question results
        evaluation = Evaluation(
            evaluation_id=evaluation_id,
            agent_config=agent_config,
            preprocessed_benchmark_id=benchmark_id,
            status="completed",
            created_at=datetime.now(),
            started_at=datetime.now(),
            completed_at=datetime.now(),
            results=None,  # Phase 8: Results computed from question results
            failure_reason=None,
        )

        assert evaluation.status == "completed"
        assert evaluation.results is None

    def test_evaluation_validation_failed_requires_failure_reason(self) -> None:
        """Test failed evaluation must have failure reason."""
        evaluation_id = uuid.uuid4()
        benchmark_id = uuid.uuid4()
        agent_config = AgentConfig(
            agent_type="none",
            model_provider="openai",
            model_name="gpt-4",
            model_parameters={"temperature": 0.7, "max_tokens": 1000},
            agent_parameters={"timeout_seconds": 30},
        )

        try:
            Evaluation(
                evaluation_id=evaluation_id,
                agent_config=agent_config,
                preprocessed_benchmark_id=benchmark_id,
                status="failed",
                created_at=datetime.now(),
                started_at=datetime.now(),
                completed_at=datetime.now(),
                results=None,
                failure_reason=None,  # Missing failure reason
            )
            raise AssertionError("Expected ValueError for missing failure reason")
        except ValueError as e:
            assert "Failed evaluation must have failure reason" in str(e)

    def test_evaluation_immutability(self) -> None:
        """Test Evaluation is immutable."""
        evaluation = self._create_test_evaluation(status="pending")

        try:
            evaluation.status = "running"  # type: ignore
            raise AssertionError("Expected error when trying to modify status")
        except (AttributeError, ValueError):
            pass  # Expected - frozen dataclass should prevent modification

    def _create_test_evaluation(self, status: str = "pending") -> Evaluation:
        """Helper method to create test evaluation."""
        evaluation_id = uuid.uuid4()
        benchmark_id = uuid.uuid4()
        agent_config = AgentConfig(
            agent_type="none",
            model_provider="openai",
            model_name="gpt-4",
            model_parameters={"temperature": 0.7, "max_tokens": 1000},
            agent_parameters={"timeout_seconds": 30},
        )

        # Set appropriate timestamps based on status
        created_at = datetime.now()
        started_at = (
            datetime.now() if status in ["running", "completed", "failed"] else None
        )
        completed_at = datetime.now() if status in ["completed", "failed"] else None

        # Set appropriate results/failure reason based on status
        results = None
        failure_reason = None

        if status == "completed":
            detailed_results = [
                QuestionResult(
                    question_id="q1",
                    question_text="What is 2+2?",
                    expected_answer="4",
                    actual_answer="4",
                    is_correct=True,
                )
            ]
            results = EvaluationResults(
                total_questions=1,
                correct_answers=1,
                accuracy=100.0,
                average_execution_time=1.5,
                error_count=0,
                detailed_results=detailed_results,
                summary_statistics={},
            )
        elif status == "failed":
            failure_reason = FailureReason(
                category="network_timeout",
                description="Request timed out",
                technical_details="Timeout error",
                occurred_at=datetime.now(),
                recoverable=True,
            )

        return Evaluation(
            evaluation_id=evaluation_id,
            agent_config=agent_config,
            preprocessed_benchmark_id=benchmark_id,
            status=status,
            created_at=created_at,
            started_at=started_at,
            completed_at=completed_at,
            results=results,
            failure_reason=failure_reason,
        )
