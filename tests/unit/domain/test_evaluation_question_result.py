"""Tests for EvaluationQuestionResult entity."""

import uuid
from datetime import datetime

import pytest

from ml_agents_v2.core.domain.entities.evaluation_question_result import (
    EvaluationQuestionResult,
)
from ml_agents_v2.core.domain.value_objects.reasoning_trace import ReasoningTrace


class TestEvaluationQuestionResult:
    """Test suite for EvaluationQuestionResult entity."""

    def test_create_successful(self) -> None:
        """Test creating successful EvaluationQuestionResult."""
        evaluation_id = uuid.uuid4()
        reasoning_trace = ReasoningTrace(
            approach_type="chain_of_thought",
            reasoning_text="Step-by-step reasoning",
            metadata={"confidence": 0.8},
        )

        result = EvaluationQuestionResult.create_successful(
            evaluation_id=evaluation_id,
            question_id="q1",
            question_text="What is 2+2?",
            expected_answer="4",
            actual_answer="4",
            is_correct=True,
            execution_time=1.5,
            reasoning_trace=reasoning_trace,
        )

        assert result.evaluation_id == evaluation_id
        assert result.question_id == "q1"
        assert result.question_text == "What is 2+2?"
        assert result.expected_answer == "4"
        assert result.actual_answer == "4"
        assert result.is_correct is True
        assert result.execution_time == 1.5
        assert result.reasoning_trace == reasoning_trace
        assert result.error_message is None
        assert result.technical_details is None
        assert result.processed_at is not None

    def test_create_failed_with_technical_details(self) -> None:
        """Test creating failed EvaluationQuestionResult with technical details."""
        evaluation_id = uuid.uuid4()

        result = EvaluationQuestionResult.create_failed(
            evaluation_id=evaluation_id,
            question_id="q2",
            question_text="What is the capital of France?",
            expected_answer="Paris",
            error_message="Model refused to answer",
            execution_time=0.8,
            technical_details="APIError: Content filter triggered",
        )

        assert result.evaluation_id == evaluation_id
        assert result.question_id == "q2"
        assert result.question_text == "What is the capital of France?"
        assert result.expected_answer == "Paris"
        assert result.actual_answer is None
        assert result.is_correct is None
        assert result.execution_time == 0.8
        assert result.reasoning_trace is None
        assert result.error_message == "Model refused to answer"
        assert result.technical_details == "APIError: Content filter triggered"
        assert result.processed_at is not None

    def test_create_failed_without_technical_details(self) -> None:
        """Test creating failed EvaluationQuestionResult without technical details."""
        evaluation_id = uuid.uuid4()

        result = EvaluationQuestionResult.create_failed(
            evaluation_id=evaluation_id,
            question_id="q3",
            question_text="Complex question",
            expected_answer="Complex answer",
            error_message="Timeout error",
            execution_time=30.0,
        )

        assert result.error_message == "Timeout error"
        assert result.technical_details is None
        assert result.actual_answer is None
        assert result.is_correct is None

    def test_validation_negative_execution_time(self) -> None:
        """Test validation fails for negative execution time."""
        with pytest.raises(ValueError, match="Processing time must be positive"):
            EvaluationQuestionResult.create_successful(
                evaluation_id=uuid.uuid4(),
                question_id="q1",
                question_text="Test",
                expected_answer="Test",
                actual_answer="Test",
                is_correct=True,
                execution_time=-1.0,
            )

    def test_validation_missing_error_message_on_failure(self) -> None:
        """Test validation fails when both actual_answer and error_message are None."""
        with pytest.raises(
            ValueError, match="Error message required if processing failed"
        ):
            EvaluationQuestionResult(
                id=uuid.uuid4(),
                evaluation_id=uuid.uuid4(),
                question_id="q1",
                question_text="Test",
                expected_answer="Test",
                actual_answer=None,
                is_correct=None,
                execution_time=1.0,
                reasoning_trace=None,
                error_message=None,
                technical_details=None,
                processed_at=datetime.now(),
            )

    def test_validation_missing_correctness_on_success(self) -> None:
        """Test validation fails when actual_answer exists but is_correct is None."""
        with pytest.raises(
            ValueError, match="Successful processing must have correctness evaluation"
        ):
            EvaluationQuestionResult(
                id=uuid.uuid4(),
                evaluation_id=uuid.uuid4(),
                question_id="q1",
                question_text="Test",
                expected_answer="Test",
                actual_answer="Test",
                is_correct=None,
                execution_time=1.0,
                reasoning_trace=None,
                error_message=None,
                technical_details=None,
                processed_at=datetime.now(),
            )

    def test_is_successful(self) -> None:
        """Test is_successful method."""
        successful_result = EvaluationQuestionResult.create_successful(
            evaluation_id=uuid.uuid4(),
            question_id="q1",
            question_text="Test",
            expected_answer="Test",
            actual_answer="Test",
            is_correct=True,
            execution_time=1.0,
        )

        failed_result = EvaluationQuestionResult.create_failed(
            evaluation_id=uuid.uuid4(),
            question_id="q2",
            question_text="Test",
            expected_answer="Test",
            error_message="Error",
            execution_time=1.0,
        )

        assert successful_result.is_successful() is True
        assert failed_result.is_successful() is False

    def test_matches_expected(self) -> None:
        """Test matches_expected method."""
        correct_result = EvaluationQuestionResult.create_successful(
            evaluation_id=uuid.uuid4(),
            question_id="q1",
            question_text="Test",
            expected_answer="Test",
            actual_answer="Test",
            is_correct=True,
            execution_time=1.0,
        )

        incorrect_result = EvaluationQuestionResult.create_successful(
            evaluation_id=uuid.uuid4(),
            question_id="q2",
            question_text="Test",
            expected_answer="Test",
            actual_answer="Wrong",
            is_correct=False,
            execution_time=1.0,
        )

        failed_result = EvaluationQuestionResult.create_failed(
            evaluation_id=uuid.uuid4(),
            question_id="q3",
            question_text="Test",
            expected_answer="Test",
            error_message="Error",
            execution_time=1.0,
        )

        assert correct_result.matches_expected() is True
        assert incorrect_result.matches_expected() is False
        assert failed_result.matches_expected() is False
