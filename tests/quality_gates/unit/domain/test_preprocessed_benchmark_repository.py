"""Tests for PreprocessedBenchmarkRepository interface."""

import uuid
from datetime import datetime
from typing import Any

import pytest

from ml_agents_v2.core.domain.entities.preprocessed_benchmark import (
    PreprocessedBenchmark,
)
from ml_agents_v2.core.domain.repositories.preprocessed_benchmark_repository import (
    PreprocessedBenchmarkRepository,
)
from ml_agents_v2.core.domain.value_objects.question import Question


class MockPreprocessedBenchmarkRepository(PreprocessedBenchmarkRepository):
    """Mock implementation of PreprocessedBenchmarkRepository for testing."""

    def __init__(self) -> None:
        """Initialize mock repository with empty storage."""
        self._benchmarks: dict[uuid.UUID, PreprocessedBenchmark] = {}

    async def save(self, benchmark: PreprocessedBenchmark) -> None:
        """Mock save implementation."""
        self._benchmarks[benchmark.benchmark_id] = benchmark

    async def get_by_id(self, benchmark_id: uuid.UUID) -> PreprocessedBenchmark | None:
        """Mock get_by_id implementation."""
        return self._benchmarks.get(benchmark_id)

    async def get_by_name(self, name: str) -> PreprocessedBenchmark | None:
        """Mock get_by_name implementation."""
        for benchmark in self._benchmarks.values():
            if benchmark.name == name:
                return benchmark
        return None

    async def list_by_format_version(
        self, format_version: str
    ) -> list[PreprocessedBenchmark]:
        """Mock list_by_format_version implementation."""
        return [
            benchmark
            for benchmark in self._benchmarks.values()
            if benchmark.format_version == format_version
        ]

    async def search_by_metadata(
        self, metadata_filters: dict[str, Any]
    ) -> list[PreprocessedBenchmark]:
        """Mock search_by_metadata implementation."""
        results = []
        for benchmark in self._benchmarks.values():
            matches = True
            for key, value in metadata_filters.items():
                if key not in benchmark.metadata or benchmark.metadata[key] != value:
                    matches = False
                    break
            if matches:
                results.append(benchmark)
        return results

    async def update(self, benchmark: PreprocessedBenchmark) -> None:
        """Mock update implementation."""
        if benchmark.benchmark_id not in self._benchmarks:
            raise ValueError(f"Benchmark {benchmark.benchmark_id} not found")
        self._benchmarks[benchmark.benchmark_id] = benchmark

    async def delete(self, benchmark_id: uuid.UUID) -> None:
        """Mock delete implementation."""
        if benchmark_id not in self._benchmarks:
            raise ValueError(f"Benchmark {benchmark_id} not found")
        del self._benchmarks[benchmark_id]

    async def exists(self, benchmark_id: uuid.UUID) -> bool:
        """Mock exists implementation."""
        return benchmark_id in self._benchmarks

    async def list_all(self, limit: int | None = None) -> list[PreprocessedBenchmark]:
        """Mock list_all implementation."""
        benchmarks = list(self._benchmarks.values())
        if limit is not None:
            benchmarks = benchmarks[:limit]
        return benchmarks

    async def get_summary_stats(self) -> dict[str, Any]:
        """Mock get_summary_stats implementation."""
        if not self._benchmarks:
            return {"total_count": 0, "format_versions": [], "avg_question_count": 0}

        format_versions = list(
            {benchmark.format_version for benchmark in self._benchmarks.values()}
        )
        total_questions = sum(
            benchmark.question_count for benchmark in self._benchmarks.values()
        )
        avg_questions = total_questions / len(self._benchmarks)

        return {
            "total_count": len(self._benchmarks),
            "format_versions": format_versions,
            "avg_question_count": avg_questions,
            "total_questions": total_questions,
        }


class TestPreprocessedBenchmarkRepository:
    """Test suite for PreprocessedBenchmarkRepository interface."""

    @pytest.fixture
    def repository(self) -> MockPreprocessedBenchmarkRepository:
        """Create a mock repository for testing."""
        return MockPreprocessedBenchmarkRepository()

    @pytest.fixture
    def sample_questions(self) -> list[Question]:
        """Create sample questions for testing."""
        return [
            Question(
                id="q1",
                text="What is 2+2?",
                expected_answer="4",
                metadata={"difficulty": "easy", "topic": "math"},
            ),
            Question(
                id="q2",
                text="What is the capital of France?",
                expected_answer="Paris",
                metadata={"difficulty": "medium", "topic": "geography"},
            ),
        ]

    @pytest.fixture
    def sample_benchmark(
        self, sample_questions: list[Question]
    ) -> PreprocessedBenchmark:
        """Create a sample benchmark for testing."""
        return PreprocessedBenchmark(
            benchmark_id=uuid.uuid4(),
            name="Test Benchmark",
            description="A test benchmark for unit testing",
            questions=sample_questions,
            metadata={"source": "test", "version": "1.0", "category": "general"},
            created_at=datetime.now(),
            question_count=len(sample_questions),
            format_version="2.0",
        )

    @pytest.mark.asyncio
    async def test_save_benchmark(
        self,
        repository: MockPreprocessedBenchmarkRepository,
        sample_benchmark: PreprocessedBenchmark,
    ) -> None:
        """Test saving a benchmark."""
        await repository.save(sample_benchmark)

        # Verify benchmark was saved
        retrieved = await repository.get_by_id(sample_benchmark.benchmark_id)
        assert retrieved == sample_benchmark

    @pytest.mark.asyncio
    async def test_get_by_id_existing(
        self,
        repository: MockPreprocessedBenchmarkRepository,
        sample_benchmark: PreprocessedBenchmark,
    ) -> None:
        """Test retrieving an existing benchmark by ID."""
        await repository.save(sample_benchmark)

        result = await repository.get_by_id(sample_benchmark.benchmark_id)

        assert result == sample_benchmark
        assert result.benchmark_id == sample_benchmark.benchmark_id

    @pytest.mark.asyncio
    async def test_get_by_id_nonexistent(
        self, repository: MockPreprocessedBenchmarkRepository
    ) -> None:
        """Test retrieving a nonexistent benchmark returns None."""
        nonexistent_id = uuid.uuid4()

        result = await repository.get_by_id(nonexistent_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_name_existing(
        self,
        repository: MockPreprocessedBenchmarkRepository,
        sample_benchmark: PreprocessedBenchmark,
    ) -> None:
        """Test retrieving an existing benchmark by name."""
        await repository.save(sample_benchmark)

        result = await repository.get_by_name(sample_benchmark.name)

        assert result == sample_benchmark
        assert result.name == sample_benchmark.name

    @pytest.mark.asyncio
    async def test_get_by_name_nonexistent(
        self, repository: MockPreprocessedBenchmarkRepository
    ) -> None:
        """Test retrieving a nonexistent benchmark by name returns None."""
        result = await repository.get_by_name("Nonexistent Benchmark")

        assert result is None

    @pytest.mark.asyncio
    async def test_list_by_format_version(
        self,
        repository: MockPreprocessedBenchmarkRepository,
        sample_questions: list[Question],
    ) -> None:
        """Test listing benchmarks by format version."""
        # Create benchmarks with different format versions
        benchmark_v1 = PreprocessedBenchmark(
            benchmark_id=uuid.uuid4(),
            name="Benchmark v1",
            description="Version 1 benchmark",
            questions=sample_questions,
            metadata={"version": "1.0"},
            created_at=datetime.now(),
            question_count=len(sample_questions),
            format_version="1.0",
        )

        benchmark_v2 = PreprocessedBenchmark(
            benchmark_id=uuid.uuid4(),
            name="Benchmark v2",
            description="Version 2 benchmark",
            questions=sample_questions,
            metadata={"version": "2.0"},
            created_at=datetime.now(),
            question_count=len(sample_questions),
            format_version="2.0",
        )

        benchmark_v2_2 = PreprocessedBenchmark(
            benchmark_id=uuid.uuid4(),
            name="Another Benchmark v2",
            description="Another version 2 benchmark",
            questions=sample_questions,
            metadata={"version": "2.0"},
            created_at=datetime.now(),
            question_count=len(sample_questions),
            format_version="2.0",
        )

        await repository.save(benchmark_v1)
        await repository.save(benchmark_v2)
        await repository.save(benchmark_v2_2)

        # Test filtering by format version
        v1_benchmarks = await repository.list_by_format_version("1.0")
        v2_benchmarks = await repository.list_by_format_version("2.0")
        v3_benchmarks = await repository.list_by_format_version("3.0")

        assert len(v1_benchmarks) == 1
        assert benchmark_v1 in v1_benchmarks
        assert len(v2_benchmarks) == 2
        assert benchmark_v2 in v2_benchmarks
        assert benchmark_v2_2 in v2_benchmarks
        assert len(v3_benchmarks) == 0

    @pytest.mark.asyncio
    async def test_search_by_metadata(
        self,
        repository: MockPreprocessedBenchmarkRepository,
        sample_questions: list[Question],
    ) -> None:
        """Test searching benchmarks by metadata."""
        # Create benchmarks with different metadata
        math_benchmark = PreprocessedBenchmark(
            benchmark_id=uuid.uuid4(),
            name="Math Benchmark",
            description="Mathematics questions",
            questions=sample_questions,
            metadata={"category": "math", "difficulty": "easy", "source": "test"},
            created_at=datetime.now(),
            question_count=len(sample_questions),
            format_version="2.0",
        )

        science_benchmark = PreprocessedBenchmark(
            benchmark_id=uuid.uuid4(),
            name="Science Benchmark",
            description="Science questions",
            questions=sample_questions,
            metadata={"category": "science", "difficulty": "hard", "source": "test"},
            created_at=datetime.now(),
            question_count=len(sample_questions),
            format_version="2.0",
        )

        history_benchmark = PreprocessedBenchmark(
            benchmark_id=uuid.uuid4(),
            name="History Benchmark",
            description="History questions",
            questions=sample_questions,
            metadata={
                "category": "history",
                "difficulty": "easy",
                "source": "external",
            },
            created_at=datetime.now(),
            question_count=len(sample_questions),
            format_version="2.0",
        )

        await repository.save(math_benchmark)
        await repository.save(science_benchmark)
        await repository.save(history_benchmark)

        # Test different metadata filters
        category_results = await repository.search_by_metadata({"category": "math"})
        assert len(category_results) == 1
        assert math_benchmark in category_results

        difficulty_results = await repository.search_by_metadata({"difficulty": "easy"})
        assert len(difficulty_results) == 2
        assert math_benchmark in difficulty_results
        assert history_benchmark in difficulty_results

        source_results = await repository.search_by_metadata({"source": "test"})
        assert len(source_results) == 2
        assert math_benchmark in source_results
        assert science_benchmark in source_results

        # Test multiple criteria
        multi_results = await repository.search_by_metadata(
            {"difficulty": "easy", "source": "test"}
        )
        assert len(multi_results) == 1
        assert math_benchmark in multi_results

        # Test no matches
        no_match_results = await repository.search_by_metadata(
            {"category": "nonexistent"}
        )
        assert len(no_match_results) == 0

    @pytest.mark.asyncio
    async def test_update_benchmark(
        self,
        repository: MockPreprocessedBenchmarkRepository,
        sample_benchmark: PreprocessedBenchmark,
    ) -> None:
        """Test updating an existing benchmark."""
        await repository.save(sample_benchmark)

        # Create updated benchmark (immutable, so create new instance)
        updated_questions = sample_benchmark.questions + [
            Question(
                id="q3",
                text="What is 3+3?",
                expected_answer="6",
                metadata={"difficulty": "easy"},
            )
        ]

        updated_benchmark = PreprocessedBenchmark(
            benchmark_id=sample_benchmark.benchmark_id,
            name=sample_benchmark.name,
            description="Updated description",
            questions=updated_questions,
            metadata=sample_benchmark.metadata,
            created_at=sample_benchmark.created_at,
            question_count=len(updated_questions),
            format_version=sample_benchmark.format_version,
        )

        await repository.update(updated_benchmark)

        # Verify update
        retrieved = await repository.get_by_id(sample_benchmark.benchmark_id)
        assert retrieved.description == "Updated description"
        assert retrieved.question_count == 3

    @pytest.mark.asyncio
    async def test_update_nonexistent_benchmark(
        self,
        repository: MockPreprocessedBenchmarkRepository,
        sample_benchmark: PreprocessedBenchmark,
    ) -> None:
        """Test updating a nonexistent benchmark raises error."""
        with pytest.raises(ValueError, match="not found"):
            await repository.update(sample_benchmark)

    @pytest.mark.asyncio
    async def test_delete_benchmark(
        self,
        repository: MockPreprocessedBenchmarkRepository,
        sample_benchmark: PreprocessedBenchmark,
    ) -> None:
        """Test deleting an existing benchmark."""
        await repository.save(sample_benchmark)

        # Verify exists before delete
        assert await repository.exists(sample_benchmark.benchmark_id) is True

        # Delete
        await repository.delete(sample_benchmark.benchmark_id)

        # Verify deleted
        assert await repository.exists(sample_benchmark.benchmark_id) is False
        assert await repository.get_by_id(sample_benchmark.benchmark_id) is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_benchmark(
        self, repository: MockPreprocessedBenchmarkRepository
    ) -> None:
        """Test deleting a nonexistent benchmark raises error."""
        nonexistent_id = uuid.uuid4()

        with pytest.raises(ValueError, match="not found"):
            await repository.delete(nonexistent_id)

    @pytest.mark.asyncio
    async def test_exists_benchmark(
        self,
        repository: MockPreprocessedBenchmarkRepository,
        sample_benchmark: PreprocessedBenchmark,
    ) -> None:
        """Test checking if benchmark exists."""
        # Initially doesn't exist
        assert await repository.exists(sample_benchmark.benchmark_id) is False

        # Save and check exists
        await repository.save(sample_benchmark)
        assert await repository.exists(sample_benchmark.benchmark_id) is True

        # Delete and check doesn't exist
        await repository.delete(sample_benchmark.benchmark_id)
        assert await repository.exists(sample_benchmark.benchmark_id) is False

    @pytest.mark.asyncio
    async def test_list_all_benchmarks(
        self,
        repository: MockPreprocessedBenchmarkRepository,
        sample_questions: list[Question],
    ) -> None:
        """Test listing all benchmarks."""
        # Create multiple benchmarks
        benchmarks = []
        for i in range(5):
            benchmark = PreprocessedBenchmark(
                benchmark_id=uuid.uuid4(),
                name=f"Benchmark {i}",
                description=f"Test benchmark {i}",
                questions=sample_questions,
                metadata={"index": i},
                created_at=datetime.now(),
                question_count=len(sample_questions),
                format_version="2.0",
            )
            benchmarks.append(benchmark)
            await repository.save(benchmark)

        # Test list all without limit
        all_benchmarks = await repository.list_all()
        assert len(all_benchmarks) == 5
        for benchmark in benchmarks:
            assert benchmark in all_benchmarks

        # Test list all with limit
        limited_benchmarks = await repository.list_all(limit=3)
        assert len(limited_benchmarks) == 3
        for benchmark in limited_benchmarks:
            assert benchmark in benchmarks

    @pytest.mark.asyncio
    async def test_get_summary_stats(
        self,
        repository: MockPreprocessedBenchmarkRepository,
        sample_questions: list[Question],
    ) -> None:
        """Test getting summary statistics."""
        # Test empty repository
        empty_stats = await repository.get_summary_stats()
        assert empty_stats["total_count"] == 0
        assert empty_stats["format_versions"] == []
        assert empty_stats["avg_question_count"] == 0

        # Add benchmarks with different characteristics
        benchmark1 = PreprocessedBenchmark(
            benchmark_id=uuid.uuid4(),
            name="Benchmark 1",
            description="First benchmark",
            questions=sample_questions,
            metadata={},
            created_at=datetime.now(),
            question_count=2,
            format_version="1.0",
        )

        benchmark2 = PreprocessedBenchmark(
            benchmark_id=uuid.uuid4(),
            name="Benchmark 2",
            description="Second benchmark",
            questions=sample_questions
            + [Question(id="q3", text="Test?", expected_answer="Test", metadata={})],
            metadata={},
            created_at=datetime.now(),
            question_count=3,
            format_version="2.0",
        )

        benchmark3 = PreprocessedBenchmark(
            benchmark_id=uuid.uuid4(),
            name="Benchmark 3",
            description="Third benchmark",
            questions=sample_questions,
            metadata={},
            created_at=datetime.now(),
            question_count=2,
            format_version="2.0",
        )

        await repository.save(benchmark1)
        await repository.save(benchmark2)
        await repository.save(benchmark3)

        # Test populated repository stats
        stats = await repository.get_summary_stats()
        assert stats["total_count"] == 3
        assert set(stats["format_versions"]) == {"1.0", "2.0"}
        assert stats["avg_question_count"] == (2 + 3 + 2) / 3
        assert stats["total_questions"] == 7

    @pytest.mark.asyncio
    async def test_abstract_interface_compliance(self) -> None:
        """Test that PreprocessedBenchmarkRepository is properly abstract."""
        # Should not be able to instantiate abstract class directly
        with pytest.raises(TypeError):
            PreprocessedBenchmarkRepository()  # type: ignore

    def test_interface_method_signatures(self) -> None:
        """Test that the interface has all required method signatures."""
        # Verify all required methods exist
        required_methods = [
            "save",
            "get_by_id",
            "get_by_name",
            "list_by_format_version",
            "search_by_metadata",
            "update",
            "delete",
            "exists",
            "list_all",
            "get_summary_stats",
        ]

        for method_name in required_methods:
            assert hasattr(PreprocessedBenchmarkRepository, method_name)
            method = getattr(PreprocessedBenchmarkRepository, method_name)
            assert callable(method)
