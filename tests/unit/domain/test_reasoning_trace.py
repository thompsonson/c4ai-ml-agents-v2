"""Tests for ReasoningTrace value object."""

import pytest

from ml_agents_v2.core.domain.value_objects.reasoning_trace import ReasoningTrace


class TestReasoningTrace:
    """Test ReasoningTrace value object behavior."""

    def test_reasoning_trace_none_approach(self) -> None:
        """Test ReasoningTrace for 'none' reasoning approach."""
        trace = ReasoningTrace(approach_type="none", reasoning_text="", metadata={})

        assert trace.approach_type == "none"
        assert trace.reasoning_text == ""
        assert trace.metadata == {}

    def test_reasoning_trace_chain_of_thought_approach(self) -> None:
        """Test ReasoningTrace for 'chain_of_thought' reasoning approach."""
        reasoning_text = (
            "Step 1: Understand the problem. Step 2: Break it down. Step 3: Solve."
        )
        trace = ReasoningTrace(
            approach_type="chain_of_thought",
            reasoning_text=reasoning_text,
            metadata={"steps": 3, "confidence": 0.9},
        )

        assert trace.approach_type == "chain_of_thought"
        assert trace.reasoning_text == reasoning_text
        assert trace.metadata == {"steps": 3, "confidence": 0.9}

    def test_reasoning_trace_creation_with_none_metadata(self) -> None:
        """Test ReasoningTrace creation with None metadata defaults to empty dict."""
        trace = ReasoningTrace(
            approach_type="chain_of_thought",
            reasoning_text="Some reasoning",
            metadata=None,
        )

        assert trace.approach_type == "chain_of_thought"
        assert trace.reasoning_text == "Some reasoning"
        assert trace.metadata == {}

    def test_reasoning_trace_value_equality(self) -> None:
        """Test that ReasoningTraces with same values are equal."""
        trace1 = ReasoningTrace(
            approach_type="chain_of_thought",
            reasoning_text="Same reasoning",
            metadata={"key": "value"},
        )

        trace2 = ReasoningTrace(
            approach_type="chain_of_thought",
            reasoning_text="Same reasoning",
            metadata={"key": "value"},
        )

        assert trace1.equals(trace2)
        assert trace1 is not trace2  # Different instances

    def test_reasoning_trace_value_inequality_different_approach(self) -> None:
        """Test ReasoningTraces with different approach types are not equal."""
        trace1 = ReasoningTrace(approach_type="none", reasoning_text="", metadata={})

        trace2 = ReasoningTrace(
            approach_type="chain_of_thought",
            reasoning_text="Some reasoning steps here",
            metadata={},
        )

        assert not trace1.equals(trace2)

    def test_reasoning_trace_value_inequality_different_text(self) -> None:
        """Test ReasoningTraces with different reasoning text are not equal."""
        trace1 = ReasoningTrace(
            approach_type="chain_of_thought",
            reasoning_text="First reasoning",
            metadata={},
        )

        trace2 = ReasoningTrace(
            approach_type="chain_of_thought",
            reasoning_text="Second reasoning",
            metadata={},
        )

        assert not trace1.equals(trace2)

    def test_reasoning_trace_immutability(self) -> None:
        """Test that ReasoningTrace is immutable after creation."""
        trace = ReasoningTrace(
            approach_type="chain_of_thought",
            reasoning_text="Cannot change this",
            metadata={"immutable": True},
        )

        # Should not be able to modify attributes
        with pytest.raises(AttributeError):
            trace.approach_type = "none"  # type: ignore

        with pytest.raises(AttributeError):
            trace.reasoning_text = "Modified text"  # type: ignore

        # Should not be able to modify metadata dictionary
        with pytest.raises(TypeError):
            trace.metadata["immutable"] = False  # type: ignore

    def test_reasoning_trace_to_dict(self) -> None:
        """Test serialization to dictionary."""
        trace = ReasoningTrace(
            approach_type="chain_of_thought",
            reasoning_text="Detailed reasoning process",
            metadata={"duration_seconds": 2.5, "tokens_used": 150},
        )

        result = trace.to_dict()
        expected = {
            "approach_type": "chain_of_thought",
            "reasoning_text": "Detailed reasoning process",
            "metadata": {"duration_seconds": 2.5, "tokens_used": 150},
        }

        assert result == expected

    def test_reasoning_trace_from_dict(self) -> None:
        """Test creation from dictionary."""
        data = {
            "approach_type": "none",
            "reasoning_text": "",
            "metadata": {"approach_validated": True},
        }

        trace = ReasoningTrace.from_dict(data)

        assert trace.approach_type == "none"
        assert trace.reasoning_text == ""
        assert trace.metadata == {"approach_validated": True}

    def test_reasoning_trace_from_dict_missing_metadata(self) -> None:
        """Test creation from dictionary without metadata key."""
        data = {
            "approach_type": "chain_of_thought",
            "reasoning_text": "No metadata provided",
        }

        trace = ReasoningTrace.from_dict(data)

        assert trace.approach_type == "chain_of_thought"
        assert trace.reasoning_text == "No metadata provided"
        assert trace.metadata == {}

    def test_reasoning_trace_validation_invalid_approach_type(self) -> None:
        """Test that invalid approach_type raises ValueError."""
        with pytest.raises(ValueError, match="approach_type must be one of"):
            ReasoningTrace(
                approach_type="invalid_approach",
                reasoning_text="Some text",
                metadata={},
            )

    def test_reasoning_trace_validation_none_with_reasoning_text(self) -> None:
        """Test that 'none' approach with non-empty reasoning text raises ValueError."""
        with pytest.raises(
            ValueError, match="'none' approach must have empty reasoning_text"
        ):
            ReasoningTrace(
                approach_type="none",
                reasoning_text="This should be empty for none approach",
                metadata={},
            )

    def test_reasoning_trace_validation_chain_of_thought_empty_text(self) -> None:
        """Test that 'chain_of_thought' approach with empty reasoning text raises ValueError."""
        with pytest.raises(
            ValueError,
            match="'chain_of_thought' approach must have non-empty reasoning_text",
        ):
            ReasoningTrace(
                approach_type="chain_of_thought", reasoning_text="", metadata={}
            )

    def test_reasoning_trace_validation_chain_of_thought_whitespace_only(self) -> None:
        """Test that 'chain_of_thought' with whitespace-only reasoning text raises ValueError."""
        with pytest.raises(
            ValueError,
            match="'chain_of_thought' approach must have non-empty reasoning_text",
        ):
            ReasoningTrace(
                approach_type="chain_of_thought",
                reasoning_text="   \n\t   ",  # Only whitespace
                metadata={},
            )

    def test_reasoning_trace_is_empty(self) -> None:
        """Test is_empty property for different approach types."""
        none_trace = ReasoningTrace(
            approach_type="none", reasoning_text="", metadata={}
        )

        cot_trace = ReasoningTrace(
            approach_type="chain_of_thought",
            reasoning_text="Some reasoning",
            metadata={},
        )

        assert none_trace.is_empty is True
        assert cot_trace.is_empty is False

    def test_reasoning_trace_has_reasoning(self) -> None:
        """Test has_reasoning property for different approach types."""
        none_trace = ReasoningTrace(
            approach_type="none", reasoning_text="", metadata={}
        )

        cot_trace = ReasoningTrace(
            approach_type="chain_of_thought",
            reasoning_text="Step by step thinking",
            metadata={},
        )

        assert none_trace.has_reasoning is False
        assert cot_trace.has_reasoning is True
