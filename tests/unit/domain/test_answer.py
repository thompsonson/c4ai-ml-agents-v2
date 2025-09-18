"""Tests for Answer value object."""

from ml_agents_v2.core.domain.value_objects.answer import Answer, TokenUsage
from ml_agents_v2.core.domain.value_objects.reasoning_trace import ReasoningTrace


class TestTokenUsage:
    """Test suite for TokenUsage value object."""

    def test_token_usage_creation(self) -> None:
        """Test TokenUsage can be created with all attributes."""
        usage = TokenUsage(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
        )

        assert usage.prompt_tokens == 100
        assert usage.completion_tokens == 50
        assert usage.total_tokens == 150

    def test_token_usage_value_equality(self) -> None:
        """Test TokenUsage equality based on values."""
        usage1 = TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        usage2 = TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150)

        assert usage1 == usage2

    def test_token_usage_value_inequality(self) -> None:
        """Test TokenUsage inequality when values differ."""
        usage1 = TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        usage2 = TokenUsage(prompt_tokens=200, completion_tokens=50, total_tokens=250)

        assert usage1 != usage2

    def test_token_usage_validation_negative_tokens(self) -> None:
        """Test TokenUsage validation fails for negative token counts."""
        try:
            TokenUsage(prompt_tokens=-1, completion_tokens=50, total_tokens=150)
            raise AssertionError("Expected ValueError for negative prompt_tokens")
        except ValueError as e:
            assert "Token counts cannot be negative" in str(e)

    def test_token_usage_validation_total_mismatch(self) -> None:
        """Test TokenUsage validation fails when total doesn't match sum."""
        try:
            TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=200)
            raise AssertionError("Expected ValueError for incorrect total")
        except ValueError as e:
            assert "total_tokens" in str(e) and "must equal" in str(e)

    def test_token_usage_immutability(self) -> None:
        """Test TokenUsage is immutable."""
        usage = TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150)

        try:
            usage.prompt_tokens = 200  # type: ignore
            raise AssertionError("Expected error when trying to modify prompt_tokens")
        except (AttributeError, ValueError):
            pass  # Expected - frozen dataclass should prevent modification


class TestAnswer:
    """Test suite for Answer value object."""

    def test_answer_creation(self) -> None:
        """Test Answer can be created with all attributes."""
        reasoning_trace = ReasoningTrace(
            approach_type="chain_of_thought",
            reasoning_text="Step 1: Analyze the problem...",
            metadata={},
        )
        token_usage = TokenUsage(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
        )

        answer = Answer(
            extracted_answer="42",
            reasoning_trace=reasoning_trace,
            confidence=0.95,
            execution_time=2.5,
            token_usage=token_usage,
            raw_response="Let me think step by step... The answer is 42.",
        )

        assert answer.extracted_answer == "42"
        assert answer.reasoning_trace == reasoning_trace
        assert answer.confidence == 0.95
        assert answer.execution_time == 2.5
        assert answer.token_usage == token_usage
        assert answer.raw_response == "Let me think step by step... The answer is 42."

    def test_answer_creation_with_none_confidence(self) -> None:
        """Test Answer can be created with None confidence."""
        reasoning_trace = ReasoningTrace(
            approach_type="none", reasoning_text="", metadata={}
        )
        token_usage = TokenUsage(
            prompt_tokens=50, completion_tokens=25, total_tokens=75
        )

        answer = Answer(
            extracted_answer="Yes",
            reasoning_trace=reasoning_trace,
            confidence=None,
            execution_time=1.0,
            token_usage=token_usage,
            raw_response="Yes",
        )

        assert answer.confidence is None

    def test_answer_value_equality(self) -> None:
        """Test Answer equality based on values."""
        reasoning_trace = ReasoningTrace(
            approach_type="none", reasoning_text="", metadata={}
        )
        token_usage = TokenUsage(
            prompt_tokens=50, completion_tokens=25, total_tokens=75
        )

        answer1 = Answer(
            extracted_answer="42",
            reasoning_trace=reasoning_trace,
            confidence=0.9,
            execution_time=1.5,
            token_usage=token_usage,
            raw_response="The answer is 42",
        )
        answer2 = Answer(
            extracted_answer="42",
            reasoning_trace=reasoning_trace,
            confidence=0.9,
            execution_time=1.5,
            token_usage=token_usage,
            raw_response="The answer is 42",
        )

        assert answer1 == answer2

    def test_answer_value_inequality(self) -> None:
        """Test Answer inequality when values differ."""
        reasoning_trace = ReasoningTrace(
            approach_type="none", reasoning_text="", metadata={}
        )
        token_usage = TokenUsage(
            prompt_tokens=50, completion_tokens=25, total_tokens=75
        )

        answer1 = Answer(
            extracted_answer="42",
            reasoning_trace=reasoning_trace,
            confidence=0.9,
            execution_time=1.5,
            token_usage=token_usage,
            raw_response="The answer is 42",
        )
        answer2 = Answer(
            extracted_answer="24",
            reasoning_trace=reasoning_trace,
            confidence=0.9,
            execution_time=1.5,
            token_usage=token_usage,
            raw_response="The answer is 24",
        )

        assert answer1 != answer2

    def test_answer_validation_empty_extracted_answer(self) -> None:
        """Test Answer validation fails for empty extracted_answer."""
        reasoning_trace = ReasoningTrace(
            approach_type="none", reasoning_text="", metadata={}
        )
        token_usage = TokenUsage(
            prompt_tokens=50, completion_tokens=25, total_tokens=75
        )

        try:
            Answer(
                extracted_answer="",
                reasoning_trace=reasoning_trace,
                confidence=None,
                execution_time=1.0,
                token_usage=token_usage,
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
        token_usage = TokenUsage(
            prompt_tokens=50, completion_tokens=25, total_tokens=75
        )

        try:
            Answer(
                extracted_answer="42",
                reasoning_trace=reasoning_trace,
                confidence=None,
                execution_time=-1.0,
                token_usage=token_usage,
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
        token_usage = TokenUsage(
            prompt_tokens=50, completion_tokens=25, total_tokens=75
        )

        try:
            Answer(
                extracted_answer="42",
                reasoning_trace=reasoning_trace,
                confidence=1.5,
                execution_time=1.0,
                token_usage=token_usage,
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
        token_usage = TokenUsage(
            prompt_tokens=50, completion_tokens=25, total_tokens=75
        )

        try:
            Answer(
                extracted_answer="42",
                reasoning_trace=reasoning_trace,
                confidence=None,
                execution_time=1.0,
                token_usage=token_usage,
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
        token_usage = TokenUsage(
            prompt_tokens=50, completion_tokens=25, total_tokens=75
        )

        answer = Answer(
            extracted_answer="42",
            reasoning_trace=reasoning_trace,
            confidence=0.9,
            execution_time=1.5,
            token_usage=token_usage,
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
        token_usage = TokenUsage(
            prompt_tokens=50, completion_tokens=25, total_tokens=75
        )

        answer_with_confidence = Answer(
            extracted_answer="42",
            reasoning_trace=reasoning_trace,
            confidence=0.9,
            execution_time=1.5,
            token_usage=token_usage,
            raw_response="Response",
        )

        answer_without_confidence = Answer(
            extracted_answer="42",
            reasoning_trace=reasoning_trace,
            confidence=None,
            execution_time=1.5,
            token_usage=token_usage,
            raw_response="Response",
        )

        assert answer_with_confidence.has_confidence() is True
        assert answer_without_confidence.has_confidence() is False
