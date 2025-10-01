"""Tests for Question value object."""

import pytest

from ml_agents_v2.core.domain.value_objects.question import Question


class TestQuestion:
    """Test Question value object behavior."""

    def test_question_creation(self) -> None:
        """Test basic Question creation with required parameters."""
        question = Question(
            id="q1",
            text="What is 2+2?",
            expected_answer="4",
            metadata={"difficulty": "easy", "category": "math"},
        )

        assert question.id == "q1"
        assert question.text == "What is 2+2?"
        assert question.expected_answer == "4"
        assert question.metadata == {"difficulty": "easy", "category": "math"}

    def test_question_creation_with_empty_metadata(self) -> None:
        """Test Question creation with empty metadata."""
        question = Question(
            id="q2", text="Capital of France?", expected_answer="Paris", metadata={}
        )

        assert question.id == "q2"
        assert question.text == "Capital of France?"
        assert question.expected_answer == "Paris"
        assert question.metadata == {}

    def test_question_creation_with_none_metadata(self) -> None:
        """Test Question creation with None metadata defaults to empty dict."""
        question = Question(
            id="q3",
            text="What is Python?",
            expected_answer="A programming language",
            metadata=None,
        )

        assert question.id == "q3"
        assert question.text == "What is Python?"
        assert question.expected_answer == "A programming language"
        assert question.metadata == {}

    def test_question_value_equality(self) -> None:
        """Test that Questions with same values are equal."""
        question1 = Question(
            id="q1",
            text="Test question",
            expected_answer="Test answer",
            metadata={"type": "test"},
        )

        question2 = Question(
            id="q1",
            text="Test question",
            expected_answer="Test answer",
            metadata={"type": "test"},
        )

        assert question1.equals(question2)
        assert question1 is not question2  # Different instances

    def test_question_value_inequality(self) -> None:
        """Test that Questions with different values are not equal."""
        question1 = Question(
            id="q1", text="Question A", expected_answer="Answer A", metadata={}
        )

        question2 = Question(
            id="q2",  # Different ID
            text="Question A",
            expected_answer="Answer A",
            metadata={},
        )

        assert not question1.equals(question2)

    def test_question_different_text_inequality(self) -> None:
        """Test Questions with different text are not equal."""
        question1 = Question(
            id="q1", text="What is 2+2?", expected_answer="4", metadata={}
        )

        question2 = Question(
            id="q1",
            text="What is 3+3?",  # Different text
            expected_answer="4",
            metadata={},
        )

        assert not question1.equals(question2)

    def test_question_immutability(self) -> None:
        """Test that Question is immutable after creation."""
        question = Question(
            id="q1",
            text="Immutable test",
            expected_answer="Cannot change",
            metadata={"test": "value"},
        )

        # Should not be able to modify attributes
        with pytest.raises(AttributeError):
            question.id = "q2"  # type: ignore

        with pytest.raises(AttributeError):
            question.text = "Modified text"  # type: ignore

        # Should not be able to modify metadata dictionary
        with pytest.raises(TypeError):
            question.metadata["test"] = "modified"  # type: ignore

    def test_question_to_dict(self) -> None:
        """Test serialization to dictionary."""
        question = Question(
            id="q1",
            text="Serialize me",
            expected_answer="Dictionary",
            metadata={"category": "serialization", "points": 10},
        )

        result = question.to_dict()
        expected = {
            "id": "q1",
            "text": "Serialize me",
            "expected_answer": "Dictionary",
            "metadata": {"category": "serialization", "points": 10},
        }

        assert result == expected

    def test_question_from_dict(self) -> None:
        """Test creation from dictionary."""
        data = {
            "id": "q1",
            "text": "From dict",
            "expected_answer": "Success",
            "metadata": {"source": "dictionary"},
        }

        question = Question.from_dict(data)

        assert question.id == "q1"
        assert question.text == "From dict"
        assert question.expected_answer == "Success"
        assert question.metadata == {"source": "dictionary"}

    def test_question_from_dict_missing_metadata(self) -> None:
        """Test creation from dictionary without metadata key."""
        data = {"id": "q2", "text": "No metadata", "expected_answer": "Still works"}

        question = Question.from_dict(data)

        assert question.id == "q2"
        assert question.text == "No metadata"
        assert question.expected_answer == "Still works"
        assert question.metadata == {}

    def test_question_validation_empty_id(self) -> None:
        """Test that empty ID raises ValueError."""
        with pytest.raises(ValueError, match="id cannot be empty"):
            Question(
                id="", text="Valid text", expected_answer="Valid answer", metadata={}
            )

    def test_question_validation_empty_text(self) -> None:
        """Test that empty text raises ValueError."""
        with pytest.raises(ValueError, match="text cannot be empty"):
            Question(id="q1", text="", expected_answer="Valid answer", metadata={})

    def test_question_validation_empty_expected_answer(self) -> None:
        """Test that empty expected_answer raises ValueError."""
        with pytest.raises(ValueError, match="expected_answer cannot be empty"):
            Question(id="q1", text="Valid text", expected_answer="", metadata={})
