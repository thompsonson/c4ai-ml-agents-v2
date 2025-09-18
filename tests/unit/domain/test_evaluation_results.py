"""Tests for EvaluationResults value object."""

from typing import Any

from ml_agents_v2.core.domain.value_objects.evaluation_results import (
    EvaluationResults,
    QuestionResult,
)


class TestQuestionResult:
    """Test suite for QuestionResult value object."""

    def test_question_result_creation(self) -> None:
        """Test QuestionResult can be created with all attributes."""
        result = QuestionResult(
            question_id="q1",
            question_text="What is 2+2?",
            expected_answer="4",
            actual_answer="4",
            is_correct=True,
        )

        assert result.question_id == "q1"
        assert result.question_text == "What is 2+2?"
        assert result.expected_answer == "4"
        assert result.actual_answer == "4"
        assert result.is_correct is True

    def test_question_result_value_equality(self) -> None:
        """Test QuestionResult equality based on values."""
        result1 = QuestionResult(
            question_id="q1",
            question_text="What is 2+2?",
            expected_answer="4",
            actual_answer="4",
            is_correct=True,
        )
        result2 = QuestionResult(
            question_id="q1",
            question_text="What is 2+2?",
            expected_answer="4",
            actual_answer="4",
            is_correct=True,
        )

        assert result1 == result2

    def test_question_result_value_inequality(self) -> None:
        """Test QuestionResult inequality when values differ."""
        result1 = QuestionResult(
            question_id="q1",
            question_text="What is 2+2?",
            expected_answer="4",
            actual_answer="4",
            is_correct=True,
        )
        result2 = QuestionResult(
            question_id="q1",
            question_text="What is 2+2?",
            expected_answer="4",
            actual_answer="5",
            is_correct=False,
        )

        assert result1 != result2

    def test_question_result_validation_empty_question_id(self) -> None:
        """Test QuestionResult validation fails for empty question_id."""
        try:
            QuestionResult(
                question_id="",
                question_text="What is 2+2?",
                expected_answer="4",
                actual_answer="4",
                is_correct=True,
            )
            raise AssertionError("Expected ValueError for empty question_id")
        except ValueError as e:
            assert "Question ID cannot be empty" in str(e)

    def test_question_result_validation_empty_question_text(self) -> None:
        """Test QuestionResult validation fails for empty question_text."""
        try:
            QuestionResult(
                question_id="q1",
                question_text="",
                expected_answer="4",
                actual_answer="4",
                is_correct=True,
            )
            raise AssertionError("Expected ValueError for empty question_text")
        except ValueError as e:
            assert "Question text cannot be empty" in str(e)

    def test_question_result_immutability(self) -> None:
        """Test QuestionResult is immutable."""
        result = QuestionResult(
            question_id="q1",
            question_text="What is 2+2?",
            expected_answer="4",
            actual_answer="4",
            is_correct=True,
        )

        try:
            result.question_id = "q2"  # type: ignore
            raise AssertionError("Expected error when trying to modify question_id")
        except (AttributeError, ValueError):
            pass  # Expected - frozen dataclass should prevent modification


class TestEvaluationResults:
    """Test suite for EvaluationResults value object."""

    def test_evaluation_results_creation(self) -> None:
        """Test EvaluationResults can be created with all attributes."""
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
                question_text="What is 3+3?",
                expected_answer="6",
                actual_answer="5",
                is_correct=False,
            ),
        ]
        summary_statistics: dict[str, Any] = {
            "difficulty_breakdown": {"easy": 1, "medium": 1},
            "category_performance": {"math": 0.5},
        }

        results = EvaluationResults(
            total_questions=2,
            correct_answers=1,
            accuracy=50.0,
            average_execution_time=2.5,
            total_tokens=300,
            error_count=0,
            detailed_results=detailed_results,
            summary_statistics=summary_statistics,
        )

        assert results.total_questions == 2
        assert results.correct_answers == 1
        assert results.accuracy == 50.0
        assert results.average_execution_time == 2.5
        assert results.total_tokens == 300
        assert results.error_count == 0
        assert len(results.detailed_results) == 2
        assert results.summary_statistics == summary_statistics

    def test_evaluation_results_value_equality(self) -> None:
        """Test EvaluationResults equality based on values."""
        detailed_results = [
            QuestionResult(
                question_id="q1",
                question_text="What is 2+2?",
                expected_answer="4",
                actual_answer="4",
                is_correct=True,
            )
        ]

        results1 = EvaluationResults(
            total_questions=1,
            correct_answers=1,
            accuracy=100.0,
            average_execution_time=1.0,
            total_tokens=100,
            error_count=0,
            detailed_results=detailed_results,
            summary_statistics={},
        )
        results2 = EvaluationResults(
            total_questions=1,
            correct_answers=1,
            accuracy=100.0,
            average_execution_time=1.0,
            total_tokens=100,
            error_count=0,
            detailed_results=detailed_results,
            summary_statistics={},
        )

        assert results1 == results2

    def test_evaluation_results_validation_negative_values(self) -> None:
        """Test EvaluationResults validation fails for negative values."""
        detailed_results = [
            QuestionResult(
                question_id="q1",
                question_text="What is 2+2?",
                expected_answer="4",
                actual_answer="4",
                is_correct=True,
            )
        ]

        try:
            EvaluationResults(
                total_questions=-1,
                correct_answers=1,
                accuracy=100.0,
                average_execution_time=1.0,
                total_tokens=100,
                error_count=0,
                detailed_results=detailed_results,
                summary_statistics={},
            )
            raise AssertionError("Expected ValueError for negative total_questions")
        except ValueError as e:
            assert "cannot be negative" in str(e)

    def test_evaluation_results_validation_accuracy_range(self) -> None:
        """Test EvaluationResults validation fails for accuracy outside [0,100]."""
        detailed_results = [
            QuestionResult(
                question_id="q1",
                question_text="What is 2+2?",
                expected_answer="4",
                actual_answer="4",
                is_correct=True,
            )
        ]

        try:
            EvaluationResults(
                total_questions=1,
                correct_answers=1,
                accuracy=150.0,
                average_execution_time=1.0,
                total_tokens=100,
                error_count=0,
                detailed_results=detailed_results,
                summary_statistics={},
            )
            raise AssertionError("Expected ValueError for accuracy > 100")
        except ValueError as e:
            assert "Accuracy must be between 0 and 100" in str(e)

    def test_evaluation_results_validation_correct_answers_exceeds_total(self) -> None:
        """Test EvaluationResults validation fails when correct_answers > total_questions."""
        detailed_results = [
            QuestionResult(
                question_id="q1",
                question_text="What is 2+2?",
                expected_answer="4",
                actual_answer="4",
                is_correct=True,
            )
        ]

        try:
            EvaluationResults(
                total_questions=1,
                correct_answers=2,
                accuracy=200.0,
                average_execution_time=1.0,
                total_tokens=100,
                error_count=0,
                detailed_results=detailed_results,
                summary_statistics={},
            )
            raise AssertionError(
                "Expected ValueError for correct_answers > total_questions"
            )
        except ValueError as e:
            assert "Accuracy must be between 0 and 100" in str(e)

    def test_evaluation_results_validation_detailed_results_count_mismatch(
        self,
    ) -> None:
        """Test EvaluationResults validation fails when detailed_results count doesn't match total_questions."""
        detailed_results = [
            QuestionResult(
                question_id="q1",
                question_text="What is 2+2?",
                expected_answer="4",
                actual_answer="4",
                is_correct=True,
            )
        ]

        try:
            EvaluationResults(
                total_questions=2,
                correct_answers=1,
                accuracy=50.0,
                average_execution_time=1.0,
                total_tokens=100,
                error_count=0,
                detailed_results=detailed_results,
                summary_statistics={},
            )
            raise AssertionError(
                "Expected ValueError for mismatched detailed_results count"
            )
        except ValueError as e:
            assert "Detailed results count" in str(
                e
            ) and "must match total questions" in str(e)

    def test_evaluation_results_calculate_accuracy(self) -> None:
        """Test calculate_accuracy method computes correct percentage."""
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
                question_text="What is 3+3?",
                expected_answer="6",
                actual_answer="5",
                is_correct=False,
            ),
        ]

        results = EvaluationResults(
            total_questions=2,
            correct_answers=1,
            accuracy=50.0,
            average_execution_time=1.0,
            total_tokens=100,
            error_count=0,
            detailed_results=detailed_results,
            summary_statistics={},
        )

        calculated_accuracy = results.calculate_accuracy()
        assert calculated_accuracy == 50.0

    def test_evaluation_results_calculate_accuracy_zero_questions(self) -> None:
        """Test calculate_accuracy handles zero questions gracefully."""
        results = EvaluationResults(
            total_questions=0,
            correct_answers=0,
            accuracy=0.0,
            average_execution_time=0.0,
            total_tokens=0,
            error_count=0,
            detailed_results=[],
            summary_statistics={},
        )

        calculated_accuracy = results.calculate_accuracy()
        assert calculated_accuracy == 0.0

    def test_evaluation_results_get_performance_summary(self) -> None:
        """Test get_performance_summary returns meaningful summary."""
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
                question_text="What is 3+3?",
                expected_answer="6",
                actual_answer="5",
                is_correct=False,
            ),
        ]

        results = EvaluationResults(
            total_questions=2,
            correct_answers=1,
            accuracy=50.0,
            average_execution_time=2.5,
            total_tokens=300,
            error_count=0,
            detailed_results=detailed_results,
            summary_statistics={},
        )

        summary = results.get_performance_summary()
        assert isinstance(summary, dict)
        assert "accuracy" in summary
        assert "total_questions" in summary
        assert "average_execution_time" in summary
        assert "total_tokens" in summary

    def test_evaluation_results_export_detailed_csv(self) -> None:
        """Test export_detailed_csv returns CSV format string."""
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
                question_text="What is 3+3?",
                expected_answer="6",
                actual_answer="5",
                is_correct=False,
            ),
        ]

        results = EvaluationResults(
            total_questions=2,
            correct_answers=1,
            accuracy=50.0,
            average_execution_time=2.5,
            total_tokens=300,
            error_count=0,
            detailed_results=detailed_results,
            summary_statistics={},
        )

        csv_data = results.export_detailed_csv()
        assert isinstance(csv_data, str)
        assert "question_id" in csv_data  # Header
        assert "q1" in csv_data
        assert "q2" in csv_data
        assert "What is 2+2?" in csv_data

    def test_evaluation_results_immutability(self) -> None:
        """Test EvaluationResults is immutable."""
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
            average_execution_time=1.0,
            total_tokens=100,
            error_count=0,
            detailed_results=detailed_results,
            summary_statistics={},
        )

        try:
            results.total_questions = 2  # type: ignore
            raise AssertionError("Expected error when trying to modify total_questions")
        except (AttributeError, ValueError):
            pass  # Expected - frozen dataclass should prevent modification
