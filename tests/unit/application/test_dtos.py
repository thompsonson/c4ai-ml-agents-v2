"""Tests for Application Layer DTOs."""

import uuid
from datetime import datetime, timedelta

import pytest

from ml_agents_v2.core.application.dto.evaluation_info import EvaluationInfo
from ml_agents_v2.core.application.dto.progress_info import ProgressInfo
from ml_agents_v2.core.application.dto.validation_result import ValidationResult


class TestEvaluationInfo:
    """Test suite for EvaluationInfo DTO."""

    @pytest.fixture
    def sample_evaluation_info(self):
        """Create sample evaluation info."""
        created_at = datetime.now() - timedelta(minutes=10)
        completed_at = datetime.now()

        return EvaluationInfo(
            evaluation_id=uuid.uuid4(),
            agent_type="chain_of_thought",
            model_name="claude-3-sonnet",
            benchmark_name="GPQA",
            status="completed",
            accuracy=85.5,
            created_at=created_at,
            completed_at=completed_at,
            total_questions=10,
            correct_answers=8,
        )

    def test_evaluation_info_properties(self, sample_evaluation_info):
        """Test calculated properties of EvaluationInfo."""
        # Test status checks
        assert sample_evaluation_info.is_completed is True
        assert sample_evaluation_info.is_failed is False
        assert sample_evaluation_info.is_running is False

        # Test accuracy formatting
        assert sample_evaluation_info.accuracy_percentage == "85.5%"

        # Test duration calculation
        duration = sample_evaluation_info.duration_minutes
        assert duration is not None
        assert 9.5 <= duration <= 10.5  # Should be around 10 minutes

    def test_evaluation_info_no_accuracy(self):
        """Test evaluation info with no accuracy data."""
        info = EvaluationInfo(
            evaluation_id=uuid.uuid4(),
            agent_type="none",
            model_name="gpt-4",
            benchmark_name="TEST",
            status="pending",
            accuracy=None,
            created_at=datetime.now(),
            completed_at=None,
            total_questions=None,
            correct_answers=None,
        )

        assert info.accuracy_percentage == "-"
        assert info.duration_minutes is None

    def test_evaluation_info_different_statuses(self):
        """Test evaluation info with different status values."""
        base_data = {
            "evaluation_id": uuid.uuid4(),
            "agent_type": "none",
            "model_name": "gpt-4",
            "benchmark_name": "TEST",
            "accuracy": None,
            "created_at": datetime.now(),
            "completed_at": None,
            "total_questions": None,
            "correct_answers": None,
        }

        # Test running status
        running_info = EvaluationInfo(status="running", **base_data)
        assert running_info.is_running is True
        assert running_info.is_completed is False
        assert running_info.is_failed is False

        # Test failed status
        failed_info = EvaluationInfo(status="failed", **base_data)
        assert failed_info.is_failed is True
        assert failed_info.is_completed is False
        assert failed_info.is_running is False


class TestProgressInfo:
    """Test suite for ProgressInfo DTO."""

    @pytest.fixture
    def sample_progress_info(self):
        """Create sample progress info."""
        started_at = datetime.now() - timedelta(minutes=5)
        last_updated = datetime.now()

        return ProgressInfo(
            evaluation_id=uuid.uuid4(),
            current_question=6,
            total_questions=10,
            successful_answers=5,
            failed_questions=1,
            started_at=started_at,
            last_updated=last_updated,
        )

    def test_progress_info_calculations(self, sample_progress_info):
        """Test progress calculation properties."""
        # Test completion percentage
        assert sample_progress_info.completion_percentage == 60.0

        # Test success rate
        assert sample_progress_info.success_rate == pytest.approx(83.33, rel=1e-2)

        # Test elapsed time (should be around 5 minutes)
        elapsed = sample_progress_info.elapsed_minutes
        assert 4.5 <= elapsed <= 5.5

        # Test questions per minute (6 questions in ~5 minutes)
        qpm = sample_progress_info.questions_per_minute
        assert 1.0 <= qpm <= 1.5

    def test_progress_info_edge_cases(self):
        """Test progress info with edge case values."""
        now = datetime.now()

        # Test with zero progress
        zero_progress = ProgressInfo(
            evaluation_id=uuid.uuid4(),
            current_question=0,
            total_questions=10,
            successful_answers=0,
            failed_questions=0,
            started_at=now,
            last_updated=now,
        )

        assert zero_progress.completion_percentage == 0.0
        assert zero_progress.success_rate == 0.0
        assert zero_progress.questions_per_minute == 0.0

        # Test with no total questions
        no_total = ProgressInfo(
            evaluation_id=uuid.uuid4(),
            current_question=0,
            total_questions=0,
            successful_answers=0,
            failed_questions=0,
            started_at=now,
            last_updated=now,
        )

        assert no_total.completion_percentage == 0.0

    def test_progress_info_summary(self, sample_progress_info):
        """Test progress summary formatting."""
        summary = sample_progress_info.progress_summary
        assert "6/10" in summary
        assert "60.0%" in summary
        assert "5 correct" in summary

    def test_progress_info_estimated_remaining(self, sample_progress_info):
        """Test estimated remaining time calculation."""
        remaining = sample_progress_info.estimated_remaining_minutes

        # Should estimate time for 4 remaining questions based on current rate
        if remaining is not None:
            assert 2.0 <= remaining <= 5.0  # Reasonable estimate range


class TestValidationResult:
    """Test suite for ValidationResult DTO."""

    def test_validation_result_success(self):
        """Test successful validation result."""
        result = ValidationResult.success()

        assert result.is_valid is True
        assert result.has_errors is False
        assert result.has_warnings is False
        assert len(result.errors) == 0
        assert len(result.warnings) == 0

    def test_validation_result_success_with_warnings(self):
        """Test successful validation with warnings."""
        warnings = ["This is a warning", "Another warning"]
        result = ValidationResult.success(warnings)

        assert result.is_valid is True
        assert result.has_errors is False
        assert result.has_warnings is True
        assert result.warnings == warnings

    def test_validation_result_failure(self):
        """Test failed validation result."""
        errors = ["Error 1", "Error 2"]
        warnings = ["Warning 1"]
        result = ValidationResult.failure(errors, warnings)

        assert result.is_valid is False
        assert result.has_errors is True
        assert result.has_warnings is True
        assert result.errors == errors
        assert result.warnings == warnings

    def test_validation_result_single_error(self):
        """Test single error validation result."""
        error_message = "Single error"
        result = ValidationResult.single_error(error_message)

        assert result.is_valid is False
        assert result.errors == [error_message]
        assert result.warnings == []

    def test_validation_result_add_error(self):
        """Test adding error to validation result."""
        original = ValidationResult.success()
        updated = original.add_error("New error")

        # Original should be unchanged (immutable)
        assert original.is_valid is True
        assert len(original.errors) == 0

        # Updated should have the error
        assert updated.is_valid is False
        assert updated.errors == ["New error"]

    def test_validation_result_add_warning(self):
        """Test adding warning to validation result."""
        original = ValidationResult.success()
        updated = original.add_warning("New warning")

        # Original should be unchanged
        assert len(original.warnings) == 0

        # Updated should have the warning
        assert updated.is_valid is True  # Still valid
        assert updated.warnings == ["New warning"]

    def test_validation_result_combine(self):
        """Test combining validation results."""
        result1 = ValidationResult.failure(["Error 1"], ["Warning 1"])
        result2 = ValidationResult.failure(["Error 2"], ["Warning 2"])

        combined = result1.combine(result2)

        assert combined.is_valid is False
        assert combined.errors == ["Error 1", "Error 2"]
        assert combined.warnings == ["Warning 1", "Warning 2"]

    def test_validation_result_combine_valid_with_invalid(self):
        """Test combining valid result with invalid result."""
        valid = ValidationResult.success(["Warning 1"])
        invalid = ValidationResult.failure(["Error 1"], ["Warning 2"])

        combined = valid.combine(invalid)

        assert combined.is_valid is False  # Should be invalid if either is invalid
        assert combined.errors == ["Error 1"]
        assert combined.warnings == ["Warning 1", "Warning 2"]
