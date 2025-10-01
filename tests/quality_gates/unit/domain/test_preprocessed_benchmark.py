"""Tests for PreprocessedBenchmark entity."""

import uuid
from datetime import datetime

from ml_agents_v2.core.domain.entities.preprocessed_benchmark import (
    PreprocessedBenchmark,
)
from ml_agents_v2.core.domain.value_objects.question import Question


class TestPreprocessedBenchmark:
    """Test suite for PreprocessedBenchmark entity."""

    def test_preprocessed_benchmark_creation(self) -> None:
        """Test PreprocessedBenchmark can be created with all attributes."""
        benchmark_id = uuid.uuid4()
        created_at = datetime.now()
        questions = [
            Question(
                id="q1",
                text="What is 2+2?",
                expected_answer="4",
                metadata={"difficulty": "easy"},
            ),
            Question(
                id="q2",
                text="What is the capital of France?",
                expected_answer="Paris",
                metadata={"difficulty": "medium"},
            ),
        ]

        benchmark = PreprocessedBenchmark(
            benchmark_id=benchmark_id,
            name="Basic Math Questions",
            description="Simple arithmetic and geography questions",
            questions=questions,
            metadata={"source": "test_suite", "version": "1.0"},
            created_at=created_at,
            question_count=2,
            format_version="2.0",
        )

        assert benchmark.benchmark_id == benchmark_id
        assert benchmark.name == "Basic Math Questions"
        assert benchmark.description == "Simple arithmetic and geography questions"
        assert benchmark.questions == questions
        assert benchmark.metadata == {"source": "test_suite", "version": "1.0"}
        assert benchmark.created_at == created_at
        assert benchmark.question_count == 2
        assert benchmark.format_version == "2.0"

    def test_preprocessed_benchmark_get_questions(self) -> None:
        """Test get_questions returns all questions."""
        questions = [
            Question(
                id="q1",
                text="What is 2+2?",
                expected_answer="4",
                metadata={},
            ),
            Question(
                id="q2",
                text="What is 3+3?",
                expected_answer="6",
                metadata={},
            ),
        ]

        benchmark = self._create_test_benchmark(questions=questions)
        retrieved_questions = benchmark.get_questions()

        assert retrieved_questions == questions
        assert len(retrieved_questions) == 2

    def test_preprocessed_benchmark_get_sample(self) -> None:
        """Test get_sample returns requested number of random questions."""
        questions = [
            Question(id="q1", text="Question 1", expected_answer="A1", metadata={}),
            Question(id="q2", text="Question 2", expected_answer="A2", metadata={}),
            Question(id="q3", text="Question 3", expected_answer="A3", metadata={}),
            Question(id="q4", text="Question 4", expected_answer="A4", metadata={}),
            Question(id="q5", text="Question 5", expected_answer="A5", metadata={}),
        ]

        benchmark = self._create_test_benchmark(questions=questions)

        # Test getting sample smaller than total
        sample = benchmark.get_sample(3)
        assert len(sample) == 3
        assert all(q in questions for q in sample)

        # Test getting sample equal to total
        sample_all = benchmark.get_sample(5)
        assert len(sample_all) == 5
        assert sorted(sample_all, key=lambda q: q.id) == sorted(
            questions, key=lambda q: q.id
        )

    def test_preprocessed_benchmark_get_sample_larger_than_available(self) -> None:
        """Test get_sample when requested size exceeds available questions."""
        questions = [
            Question(id="q1", text="Question 1", expected_answer="A1", metadata={}),
            Question(id="q2", text="Question 2", expected_answer="A2", metadata={}),
        ]

        benchmark = self._create_test_benchmark(questions=questions)

        # Should return all available questions when sample size exceeds total
        sample = benchmark.get_sample(10)
        assert len(sample) == 2
        assert sorted(sample, key=lambda q: q.id) == sorted(
            questions, key=lambda q: q.id
        )

    def test_preprocessed_benchmark_get_metadata(self) -> None:
        """Test get_metadata returns benchmark metadata."""
        metadata = {
            "source": "BHEH Logical Reasoning",
            "version": "2.1",
            "difficulty_levels": ["easy", "medium", "hard"],
            "total_time_limit": 3600,
        }

        benchmark = self._create_test_benchmark(metadata=metadata)
        retrieved_metadata = benchmark.get_metadata()

        assert retrieved_metadata == metadata

    def test_preprocessed_benchmark_validation_empty_name(self) -> None:
        """Test PreprocessedBenchmark validation fails for empty name."""
        questions = [
            Question(id="q1", text="Question", expected_answer="Answer", metadata={})
        ]

        try:
            PreprocessedBenchmark(
                benchmark_id=uuid.uuid4(),
                name="",
                description="Test description",
                questions=questions,
                metadata={},
                created_at=datetime.now(),
                question_count=1,
                format_version="2.0",
            )
            raise AssertionError("Expected ValueError for empty name")
        except ValueError as e:
            assert "Name cannot be empty" in str(e)

    def test_preprocessed_benchmark_validation_empty_questions(self) -> None:
        """Test PreprocessedBenchmark validation fails for empty questions list."""
        try:
            PreprocessedBenchmark(
                benchmark_id=uuid.uuid4(),
                name="Test Benchmark",
                description="Test description",
                questions=[],
                metadata={},
                created_at=datetime.now(),
                question_count=0,
                format_version="2.0",
            )
            raise AssertionError("Expected ValueError for empty questions")
        except ValueError as e:
            assert "Must have at least one question" in str(e)

    def test_preprocessed_benchmark_validation_question_count_mismatch(self) -> None:
        """Test validation fails when question_count doesn't match questions length."""
        questions = [
            Question(id="q1", text="Question", expected_answer="Answer", metadata={})
        ]

        try:
            PreprocessedBenchmark(
                benchmark_id=uuid.uuid4(),
                name="Test Benchmark",
                description="Test description",
                questions=questions,
                metadata={},
                created_at=datetime.now(),
                question_count=5,  # Mismatch
                format_version="2.0",
            )
            raise AssertionError("Expected ValueError for question count mismatch")
        except ValueError as e:
            assert "Question count" in str(
                e
            ) and "must match actual number of questions" in str(e)

    def test_preprocessed_benchmark_validation_duplicate_question_ids(self) -> None:
        """Test validation fails for duplicate question IDs."""
        questions = [
            Question(id="q1", text="Question 1", expected_answer="A1", metadata={}),
            Question(
                id="q1", text="Question 2", expected_answer="A2", metadata={}
            ),  # Duplicate ID
        ]

        try:
            PreprocessedBenchmark(
                benchmark_id=uuid.uuid4(),
                name="Test Benchmark",
                description="Test description",
                questions=questions,
                metadata={},
                created_at=datetime.now(),
                question_count=2,
                format_version="2.0",
            )
            raise AssertionError("Expected ValueError for duplicate question IDs")
        except ValueError as e:
            assert "Question IDs must be unique" in str(e)

    def test_preprocessed_benchmark_immutability(self) -> None:
        """Test PreprocessedBenchmark is immutable."""
        benchmark = self._create_test_benchmark()

        try:
            benchmark.name = "Modified Name"  # type: ignore
            raise AssertionError("Expected error when trying to modify name")
        except (AttributeError, ValueError):
            pass  # Expected - frozen dataclass should prevent modification

    def test_preprocessed_benchmark_value_equality(self) -> None:
        """Test PreprocessedBenchmark equality based on values."""
        benchmark_id = uuid.uuid4()
        questions = [
            Question(id="q1", text="Question", expected_answer="Answer", metadata={})
        ]
        created_at = datetime.now()

        benchmark1 = PreprocessedBenchmark(
            benchmark_id=benchmark_id,
            name="Test Benchmark",
            description="Test description",
            questions=questions,
            metadata={"version": "1.0"},
            created_at=created_at,
            question_count=1,
            format_version="2.0",
        )

        benchmark2 = PreprocessedBenchmark(
            benchmark_id=benchmark_id,
            name="Test Benchmark",
            description="Test description",
            questions=questions,
            metadata={"version": "1.0"},
            created_at=created_at,
            question_count=1,
            format_version="2.0",
        )

        assert benchmark1 == benchmark2

    def test_preprocessed_benchmark_value_inequality(self) -> None:
        """Test PreprocessedBenchmark inequality when values differ."""
        questions = [
            Question(id="q1", text="Question", expected_answer="Answer", metadata={})
        ]

        benchmark1 = self._create_test_benchmark(
            name="Benchmark A", questions=questions
        )
        benchmark2 = self._create_test_benchmark(
            name="Benchmark B", questions=questions
        )

        assert benchmark1 != benchmark2

    def _create_test_benchmark(
        self,
        name: str = "Test Benchmark",
        description: str = "Test description",
        questions: list[Question] | None = None,
        metadata: dict[str, any] | None = None,
    ) -> PreprocessedBenchmark:
        """Helper method to create test benchmark."""
        if questions is None:
            questions = [
                Question(
                    id="q1",
                    text="Default question",
                    expected_answer="Default answer",
                    metadata={},
                )
            ]

        if metadata is None:
            metadata = {"source": "test"}

        return PreprocessedBenchmark(
            benchmark_id=uuid.uuid4(),
            name=name,
            description=description,
            questions=questions,
            metadata=metadata,
            created_at=datetime.now(),
            question_count=len(questions),
            format_version="2.0",
        )
