"""Tests for repository implementations."""

import uuid
from datetime import datetime
from unittest.mock import patch

import pytest

from ml_agents_v2.core.domain.entities.evaluation import Evaluation
from ml_agents_v2.core.domain.entities.preprocessed_benchmark import (
    PreprocessedBenchmark,
)
from ml_agents_v2.core.domain.repositories.evaluation_repository import (
    EvaluationRepository,
)
from ml_agents_v2.core.domain.repositories.exceptions import (
    EntityNotFoundError,
)
from ml_agents_v2.core.domain.repositories.preprocessed_benchmark_repository import (
    PreprocessedBenchmarkRepository,
)
from ml_agents_v2.core.domain.value_objects.agent_config import AgentConfig
from ml_agents_v2.core.domain.value_objects.question import Question
from ml_agents_v2.infrastructure.database.repositories.benchmark_repository_impl import (
    BenchmarkRepositoryImpl,
)
from ml_agents_v2.infrastructure.database.repositories.evaluation_repository_impl import (
    EvaluationRepositoryImpl,
)
from ml_agents_v2.infrastructure.database.session_manager import DatabaseSessionManager


class TestEvaluationRepositoryImpl:
    """Test EvaluationRepositoryImpl concrete implementation."""

    @pytest.fixture
    def session_manager(self, tmp_path):
        """Create session manager with temporary database."""
        db_path = tmp_path / "test_eval_repo.db"
        session_manager = DatabaseSessionManager(f"sqlite:///{db_path}")
        session_manager.create_tables()
        return session_manager

    @pytest.fixture
    def repository(self, session_manager):
        """Create EvaluationRepositoryImpl instance."""
        return EvaluationRepositoryImpl(session_manager)

    @pytest.fixture
    def sample_evaluation(self):
        """Create sample evaluation for testing."""
        agent_config = AgentConfig(
            agent_type="none",
            model_provider="openrouter",
            model_name="meta-llama/llama-3.1-8b-instruct",
            model_parameters={"temperature": 0.1, "max_tokens": 800},
            agent_parameters={},
        )

        return Evaluation(
            evaluation_id=uuid.uuid4(),
            agent_config=agent_config,
            preprocessed_benchmark_id=uuid.uuid4(),
            status="pending",
            created_at=datetime.now(),
            started_at=None,
            completed_at=None,
            results=None,
            failure_reason=None,
        )

    def test_repository_implements_interface(self, repository):
        """Test that EvaluationRepositoryImpl implements EvaluationRepository."""
        assert isinstance(repository, EvaluationRepository)

    def test_save_evaluation(self, repository, sample_evaluation):
        """Test saving evaluation to database."""
        # Save evaluation
        repository.save(sample_evaluation)

        # Verify it was saved
        assert repository.exists(sample_evaluation.evaluation_id)

    def test_get_evaluation_by_id(self, repository, sample_evaluation):
        """Test retrieving evaluation by ID."""
        # Save evaluation first
        repository.save(sample_evaluation)

        # Retrieve by ID
        retrieved = repository.get_by_id(sample_evaluation.evaluation_id)

        assert retrieved.evaluation_id == sample_evaluation.evaluation_id
        assert retrieved.status == sample_evaluation.status
        assert (
            retrieved.agent_config.agent_type
            == sample_evaluation.agent_config.agent_type
        )

    def test_get_nonexistent_evaluation(self, repository):
        """Test retrieving non-existent evaluation raises EntityNotFoundError."""
        nonexistent_id = uuid.uuid4()

        with pytest.raises(EntityNotFoundError):
            repository.get_by_id(nonexistent_id)

    def test_list_evaluations_by_status(self, repository, sample_evaluation):
        """Test listing evaluations by status."""
        # Save evaluation
        repository.save(sample_evaluation)

        # List by status
        pending_evaluations = repository.list_by_status("pending")
        assert len(pending_evaluations) == 1
        assert pending_evaluations[0].evaluation_id == sample_evaluation.evaluation_id

        # List by different status
        running_evaluations = repository.list_by_status("running")
        assert len(running_evaluations) == 0

    def test_update_evaluation(self, repository, sample_evaluation):
        """Test updating evaluation in database."""
        # Save evaluation first
        repository.save(sample_evaluation)

        # Update evaluation status
        updated_evaluation = sample_evaluation.start_execution()
        repository.update(updated_evaluation)

        # Verify update
        retrieved = repository.get_by_id(sample_evaluation.evaluation_id)
        assert retrieved.status == "running"
        assert retrieved.started_at is not None

    def test_delete_evaluation(self, repository, sample_evaluation):
        """Test deleting evaluation from database."""
        # Save evaluation first
        repository.save(sample_evaluation)

        # Delete evaluation
        repository.delete(sample_evaluation.evaluation_id)

        # Verify deletion
        assert not repository.exists(sample_evaluation.evaluation_id)


class TestBenchmarkRepositoryImpl:
    """Test BenchmarkRepositoryImpl concrete implementation."""

    @pytest.fixture
    def session_manager(self, tmp_path):
        """Create session manager with temporary database."""
        db_path = tmp_path / "test_bench_repo.db"
        session_manager = DatabaseSessionManager(f"sqlite:///{db_path}")
        session_manager.create_tables()
        return session_manager

    @pytest.fixture
    def repository(self, session_manager):
        """Create BenchmarkRepositoryImpl instance."""
        return BenchmarkRepositoryImpl(session_manager)

    @pytest.fixture
    def sample_benchmark(self):
        """Create sample benchmark for testing."""
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
                metadata={"category": "geography"},
            ),
        ]

        return PreprocessedBenchmark(
            benchmark_id=uuid.uuid4(),
            name="Test Benchmark",
            description="A test benchmark for unit testing",
            questions=questions,
            metadata={"version": "1.0", "created_by": "test"},
            created_at=datetime.now(),
            question_count=len(questions),
            format_version="1.0",
        )

    def test_repository_implements_interface(self, repository):
        """Test that BenchmarkRepositoryImpl implements PreprocessedBenchmarkRepository."""
        assert isinstance(repository, PreprocessedBenchmarkRepository)

    def test_save_benchmark(self, repository, sample_benchmark):
        """Test saving benchmark to database."""
        # Save benchmark
        repository.save(sample_benchmark)

        # Verify it was saved
        assert repository.exists(sample_benchmark.benchmark_id)

    def test_get_benchmark_by_id(self, repository, sample_benchmark):
        """Test retrieving benchmark by ID."""
        # Save benchmark first
        repository.save(sample_benchmark)

        # Retrieve by ID
        retrieved = repository.get_by_id(sample_benchmark.benchmark_id)

        assert retrieved.benchmark_id == sample_benchmark.benchmark_id
        assert retrieved.name == sample_benchmark.name
        assert len(retrieved.questions) == len(sample_benchmark.questions)

    def test_get_benchmark_by_name(self, repository, sample_benchmark):
        """Test retrieving benchmark by name."""
        # Save benchmark first
        repository.save(sample_benchmark)

        # Retrieve by name
        retrieved = repository.get_by_name(sample_benchmark.name)

        assert retrieved.benchmark_id == sample_benchmark.benchmark_id
        assert retrieved.name == sample_benchmark.name

    def test_get_nonexistent_benchmark(self, repository):
        """Test retrieving non-existent benchmark raises EntityNotFoundError."""
        nonexistent_id = uuid.uuid4()

        with pytest.raises(EntityNotFoundError):
            repository.get_by_id(nonexistent_id)

        with pytest.raises(EntityNotFoundError):
            repository.get_by_name("nonexistent")

    def test_list_all_benchmarks(self, repository, sample_benchmark):
        """Test listing all benchmarks."""
        # Save benchmark
        repository.save(sample_benchmark)

        # List all
        all_benchmarks = repository.list_all()
        assert len(all_benchmarks) == 1
        assert all_benchmarks[0].benchmark_id == sample_benchmark.benchmark_id

    def test_benchmark_registry_constants(self, repository):
        """Test that BENCHMARK_REGISTRY contains expected constants."""
        from ml_agents_v2.infrastructure.database.repositories.benchmark_repository_impl import (
            BENCHMARK_REGISTRY,
        )

        # Verify registry structure
        assert isinstance(BENCHMARK_REGISTRY, dict)
        assert len(BENCHMARK_REGISTRY) > 0

        # Verify expected benchmark mappings
        expected_mappings = {
            "GPQA": "BENCHMARK-01-GPQA.csv",
            "FOLIO": "BENCHMARK-05-FOLIO.csv",
            "BBEH": "BENCHMARK-06-BBEH.csv",
            "MATH3": "BENCHMARK-07-MATH3.csv",
            "LeetCode_Python_Easy": "BENCHMARK-08-LeetCode_Python_Easy.csv",
        }

        for short_name, filename in expected_mappings.items():
            assert short_name in BENCHMARK_REGISTRY
            assert BENCHMARK_REGISTRY[short_name] == filename

    def test_get_by_name_with_registry_mapping(self, repository):
        """Test retrieving benchmark by short name using registry mapping."""
        from ml_agents_v2.infrastructure.database.repositories.benchmark_repository_impl import (
            BENCHMARK_REGISTRY,
        )

        # Create and save a benchmark with filename matching registry
        filename = BENCHMARK_REGISTRY["GPQA"]  # "BENCHMARK-01-GPQA.csv"
        from ml_agents_v2.core.domain.value_objects.question import Question

        question = Question(
            id="test-q1", text="What is 2+2?", expected_answer="4", metadata={}
        )
        benchmark = PreprocessedBenchmark(
            benchmark_id=uuid.uuid4(),
            name=filename,  # Save with full filename
            description="GPQA benchmark for testing",
            questions=[question],
            metadata={"source": "registry_test"},
            created_at=datetime.now(),
            question_count=1,
            format_version="1.0",
        )
        repository.save(benchmark)

        # Retrieve using short name from registry
        retrieved = repository.get_by_name("GPQA")  # Use short name

        assert retrieved.benchmark_id == benchmark.benchmark_id
        assert retrieved.name == filename  # Should return the full filename

    def test_get_by_name_registry_fallback_to_exact_name(
        self, repository, sample_benchmark
    ):
        """Test that get_by_name falls back to exact name if not in registry."""
        # Save benchmark with name not in registry
        repository.save(sample_benchmark)

        # Retrieve by exact name (should work even if not in registry)
        retrieved = repository.get_by_name(sample_benchmark.name)

        assert retrieved.benchmark_id == sample_benchmark.benchmark_id
        assert retrieved.name == sample_benchmark.name

    def test_get_by_name_registry_nonexistent_short_name(self, repository):
        """Test retrieving by non-existent short name raises EntityNotFoundError."""
        # Try to retrieve with short name that doesn't exist in registry
        # and no benchmark with that exact name exists
        with pytest.raises(EntityNotFoundError):
            repository.get_by_name("NONEXISTENT_BENCHMARK")

    def test_list_available_names_method(self, repository):
        """Test list_available_names method returns registry keys."""
        from ml_agents_v2.infrastructure.database.repositories.benchmark_repository_impl import (
            BENCHMARK_REGISTRY,
        )

        available_names = repository.list_available_names()

        # Should return the keys from BENCHMARK_REGISTRY
        expected_names = list(BENCHMARK_REGISTRY.keys())
        assert sorted(available_names) == sorted(expected_names)

        # Verify specific expected names are present
        assert "GPQA" in available_names
        assert "FOLIO" in available_names
        assert "BBEH" in available_names
        assert "MATH3" in available_names
        assert "LeetCode_Python_Easy" in available_names

    def test_list_available_names_returns_list(self, repository):
        """Test that list_available_names returns a list."""
        available_names = repository.list_available_names()

        assert isinstance(available_names, list)
        assert len(available_names) > 0

    def test_list_available_names_immutability(self, repository):
        """Test that modifying returned list doesn't affect internal registry."""
        available_names = repository.list_available_names()
        original_length = len(available_names)

        # Modify the returned list
        available_names.append("TEST_MODIFICATION")

        # Get a fresh list - should not be affected
        fresh_names = repository.list_available_names()
        assert len(fresh_names) == original_length
        assert "TEST_MODIFICATION" not in fresh_names

    def test_get_by_name_with_user_friendly_name_stored_in_database(self, repository):
        """Test retrieving benchmark by user-friendly name when that's what's stored.

        This test covers the real-world scenario where benchmarks are stored in the database
        with user-friendly names (e.g., 'GPQA') rather than CSV filenames
        (e.g., 'BENCHMARK-01-GPQA.csv'). The get_by_name method should find these benchmarks
        when searched using the user-friendly name.

        This test currently fails because get_by_name() maps 'GPQA' to 'BENCHMARK-01-GPQA.csv'
        and searches for that mapped name, but the benchmark is stored as 'GPQA'.
        """
        from ml_agents_v2.core.domain.value_objects.question import Question

        # Create and save a benchmark with user-friendly name (as it exists in real database)
        question = Question(
            id="gpqa-test-q1",
            text="What is the speed of light in vacuum?",
            expected_answer="299,792,458 m/s",
            metadata={"difficulty": "medium"},
        )

        benchmark = PreprocessedBenchmark(
            benchmark_id=uuid.uuid4(),
            name="GPQA",  # Save with user-friendly name, not CSV filename
            description="Graduate-level physics, chemistry, and biology questions",
            questions=[question],
            metadata={"source": "GPQA dataset", "format": "user_friendly"},
            created_at=datetime.now(),
            question_count=1,
            format_version="1.0",
        )
        repository.save(benchmark)

        # Attempt to retrieve using the same user-friendly name
        # This should work but currently fails because get_by_name() maps
        # "GPQA" -> "BENCHMARK-01-GPQA.csv" and searches for the mapped name
        retrieved = repository.get_by_name("GPQA")

        assert retrieved.benchmark_id == benchmark.benchmark_id
        assert retrieved.name == "GPQA"
        assert retrieved.description == benchmark.description
        assert len(retrieved.questions) == 1
        assert retrieved.questions[0].text == question.text

    def test_registry_name_mapping_integration(self, repository):
        """Test end-to-end integration of registry name mapping."""

        # Test with multiple registry entries
        test_cases = [
            ("GPQA", "BENCHMARK-01-GPQA.csv"),
            ("FOLIO", "BENCHMARK-05-FOLIO.csv"),
            ("BBEH", "BENCHMARK-06-BBEH.csv"),
        ]

        from ml_agents_v2.core.domain.value_objects.question import Question

        for short_name, filename in test_cases:
            # Create benchmark with filename
            question = Question(
                id=f"test-{short_name.lower()}-q1",
                text=f"Test question for {short_name}",
                expected_answer="test answer",
                metadata={},
            )
            benchmark = PreprocessedBenchmark(
                benchmark_id=uuid.uuid4(),
                name=filename,
                description=f"{short_name} test benchmark",
                questions=[question],
                metadata={"short_name": short_name},
                created_at=datetime.now(),
                question_count=1,
                format_version="1.0",
            )
            repository.save(benchmark)

            # Retrieve by short name
            retrieved = repository.get_by_name(short_name)
            assert retrieved.name == filename
            assert retrieved.metadata["short_name"] == short_name

            # Also verify we can still retrieve by full filename
            retrieved_by_filename = repository.get_by_name(filename)
            assert retrieved_by_filename.benchmark_id == benchmark.benchmark_id

    def test_registry_error_handling(self, repository):
        """Test error handling in registry-related methods."""
        # list_available_names should handle any internal errors gracefully
        with patch(
            "ml_agents_v2.infrastructure.database.repositories.benchmark_repository_impl.BENCHMARK_REGISTRY",
            new_callable=lambda: {"test": "value"},
        ):
            # Should not raise an exception
            names = repository.list_available_names()
            assert names == ["test"]

        # Test with empty registry
        with patch(
            "ml_agents_v2.infrastructure.database.repositories.benchmark_repository_impl.BENCHMARK_REGISTRY",
            new_callable=lambda: {},
        ):
            names = repository.list_available_names()
            assert names == []
