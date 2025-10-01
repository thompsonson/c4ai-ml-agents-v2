"""Tests for Answer value object."""

from ml_agents_v2.core.domain.value_objects.answer import Answer
from ml_agents_v2.core.domain.value_objects.reasoning_trace import ReasoningTrace


class TestAnswer:
    """Test suite for Answer value object."""

    def test_answer_creation(self) -> None:
        """Test Answer can be created with all attributes."""
        reasoning_trace = ReasoningTrace(
            approach_type="chain_of_thought",
            reasoning_text="Step 1: Analyze the problem...",
            metadata={},
        )

        answer = Answer(
            extracted_answer="42",
            reasoning_trace=reasoning_trace,
            confidence=0.95,
            execution_time=2.5,
            raw_response="Let me think step by step... The answer is 42.",
        )

        assert answer.extracted_answer == "42"
        assert answer.reasoning_trace == reasoning_trace
        assert answer.confidence == 0.95
        assert answer.execution_time == 2.5
        assert answer.raw_response == "Let me think step by step... The answer is 42."

    def test_answer_creation_with_none_confidence(self) -> None:
        """Test Answer can be created with None confidence."""
        reasoning_trace = ReasoningTrace(
            approach_type="none", reasoning_text="", metadata={}
        )

        answer = Answer(
            extracted_answer="Yes",
            reasoning_trace=reasoning_trace,
            confidence=None,
            execution_time=1.0,
            raw_response="Yes",
        )

        assert answer.confidence is None

    def test_answer_value_equality(self) -> None:
        """Test Answer equality based on values."""
        reasoning_trace = ReasoningTrace(
            approach_type="none", reasoning_text="", metadata={}
        )

        answer1 = Answer(
            extracted_answer="42",
            reasoning_trace=reasoning_trace,
            confidence=0.9,
            execution_time=1.5,
            raw_response="The answer is 42",
        )
        answer2 = Answer(
            extracted_answer="42",
            reasoning_trace=reasoning_trace,
            confidence=0.9,
            execution_time=1.5,
            raw_response="The answer is 42",
        )

        assert answer1 == answer2

    def test_answer_value_inequality(self) -> None:
        """Test Answer inequality when values differ."""
        reasoning_trace = ReasoningTrace(
            approach_type="none", reasoning_text="", metadata={}
        )

        answer1 = Answer(
            extracted_answer="42",
            reasoning_trace=reasoning_trace,
            confidence=0.9,
            execution_time=1.5,
            raw_response="The answer is 42",
        )
        answer2 = Answer(
            extracted_answer="24",
            reasoning_trace=reasoning_trace,
            confidence=0.9,
            execution_time=1.5,
            raw_response="The answer is 24",
        )

        assert answer1 != answer2

    def test_answer_validation_empty_extracted_answer(self) -> None:
        """Test Answer validation fails for empty extracted_answer."""
        reasoning_trace = ReasoningTrace(
            approach_type="none", reasoning_text="", metadata={}
        )

        try:
            Answer(
                extracted_answer="",
                reasoning_trace=reasoning_trace,
                confidence=None,
                execution_time=1.0,
                raw_response="Response",
            )
            raise AssertionError("Expected ValueError for empty extracted_answer")
        except ValueError as e:
            assert "Extracted answer cannot be empty" in str(e)

    def test_answer_validation_negative_execution_time(self) -> None:
        """Test Answer validation fails for negative execution_time."""
        reasoning_trace = ReasoningTrace(
            approach_type="none", reasoning_text="", metadata={}
        )

        try:
            Answer(
                extracted_answer="42",
                reasoning_trace=reasoning_trace,
                confidence=None,
                execution_time=-1.0,
                raw_response="Response",
            )
            raise AssertionError("Expected ValueError for negative execution_time")
        except ValueError as e:
            assert "Execution time cannot be negative" in str(e)

    def test_answer_validation_invalid_confidence_range(self) -> None:
        """Test Answer validation fails for confidence outside [0,1] range."""
        reasoning_trace = ReasoningTrace(
            approach_type="none", reasoning_text="", metadata={}
        )

        try:
            Answer(
                extracted_answer="42",
                reasoning_trace=reasoning_trace,
                confidence=1.5,
                execution_time=1.0,
                raw_response="Response",
            )
            raise AssertionError("Expected ValueError for confidence > 1")
        except ValueError as e:
            assert "Confidence must be between 0 and 1" in str(e)

    def test_answer_validation_empty_raw_response(self) -> None:
        """Test Answer validation fails for empty raw_response."""
        reasoning_trace = ReasoningTrace(
            approach_type="none", reasoning_text="", metadata={}
        )

        try:
            Answer(
                extracted_answer="42",
                reasoning_trace=reasoning_trace,
                confidence=None,
                execution_time=1.0,
                raw_response="",
            )
            raise AssertionError("Expected ValueError for empty raw_response")
        except ValueError as e:
            assert "Raw response cannot be empty" in str(e)

    def test_answer_immutability(self) -> None:
        """Test Answer is immutable."""
        reasoning_trace = ReasoningTrace(
            approach_type="none", reasoning_text="", metadata={}
        )

        answer = Answer(
            extracted_answer="42",
            reasoning_trace=reasoning_trace,
            confidence=0.9,
            execution_time=1.5,
            raw_response="The answer is 42",
        )

        try:
            answer.extracted_answer = "24"  # type: ignore
            raise AssertionError(
                "Expected error when trying to modify extracted_answer"
            )
        except (AttributeError, ValueError):
            pass  # Expected - frozen dataclass should prevent modification

    def test_answer_has_confidence(self) -> None:
        """Test has_confidence method returns correct value."""
        reasoning_trace = ReasoningTrace(
            approach_type="none", reasoning_text="", metadata={}
        )

        answer_with_confidence = Answer(
            extracted_answer="42",
            reasoning_trace=reasoning_trace,
            confidence=0.9,
            execution_time=1.5,
            raw_response="Response",
        )

        answer_without_confidence = Answer(
            extracted_answer="42",
            reasoning_trace=reasoning_trace,
            confidence=None,
            execution_time=1.5,
            raw_response="Response",
        )

        assert answer_with_confidence.has_confidence() is True
        assert answer_without_confidence.has_confidence() is False
