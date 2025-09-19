"""Tests for EvaluationRepository interface."""

import uuid
from datetime import datetime

import pytest

from ml_agents_v2.core.domain.entities.evaluation import Evaluation
from ml_agents_v2.core.domain.repositories.evaluation_repository import (
    EvaluationRepository,
)
from ml_agents_v2.core.domain.value_objects.agent_config import AgentConfig


class MockEvaluationRepository(EvaluationRepository):
    """Mock implementation of EvaluationRepository for testing."""

    def __init__(self) -> None:
        """Initialize mock repository with empty storage."""
        self._evaluations: dict[uuid.UUID, Evaluation] = {}

    async def save(self, evaluation: Evaluation) -> None:
        """Mock save implementation."""
        self._evaluations[evaluation.evaluation_id] = evaluation

    async def get_by_id(self, evaluation_id: uuid.UUID) -> Evaluation | None:
        """Mock get_by_id implementation."""
        return self._evaluations.get(evaluation_id)

    async def list_by_status(self, status: str) -> list[Evaluation]:
        """Mock list_by_status implementation."""
        return [
            eval_obj
            for eval_obj in self._evaluations.values()
            if eval_obj.status == status
        ]

    async def list_by_benchmark_id(self, benchmark_id: uuid.UUID) -> list[Evaluation]:
        """Mock list_by_benchmark_id implementation."""
        return [
            eval_obj
            for eval_obj in self._evaluations.values()
            if eval_obj.preprocessed_benchmark_id == benchmark_id
        ]

    async def update(self, evaluation: Evaluation) -> None:
        """Mock update implementation."""
        if evaluation.evaluation_id not in self._evaluations:
            raise ValueError(f"Evaluation {evaluation.evaluation_id} not found")
        self._evaluations[evaluation.evaluation_id] = evaluation

    async def delete(self, evaluation_id: uuid.UUID) -> None:
        """Mock delete implementation."""
        if evaluation_id not in self._evaluations:
            raise ValueError(f"Evaluation {evaluation_id} not found")
        del self._evaluations[evaluation_id]

    async def exists(self, evaluation_id: uuid.UUID) -> bool:
        """Mock exists implementation."""
        return evaluation_id in self._evaluations

    async def list_all(self, limit: int | None = None) -> list[Evaluation]:
        """Mock list_all implementation."""
        evaluations = list(self._evaluations.values())
        if limit is not None:
            evaluations = evaluations[:limit]
        return evaluations


class TestEvaluationRepository:
    """Test suite for EvaluationRepository interface."""

    @pytest.fixture
    def repository(self) -> MockEvaluationRepository:
        """Create a mock repository for testing."""
        return MockEvaluationRepository()

    @pytest.fixture
    def sample_evaluation(self) -> Evaluation:
        """Create a sample evaluation for testing."""
        agent_config = AgentConfig(
            agent_type="none",
            model_provider="openai",
            model_name="gpt-4",
            model_parameters={"temperature": 0.7},
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

    @pytest.mark.asyncio
    async def test_save_evaluation(
        self, repository: MockEvaluationRepository, sample_evaluation: Evaluation
    ) -> None:
        """Test saving an evaluation."""
        await repository.save(sample_evaluation)

        # Verify evaluation was saved
        retrieved = await repository.get_by_id(sample_evaluation.evaluation_id)
        assert retrieved == sample_evaluation

    @pytest.mark.asyncio
    async def test_get_by_id_existing(
        self, repository: MockEvaluationRepository, sample_evaluation: Evaluation
    ) -> None:
        """Test retrieving an existing evaluation by ID."""
        await repository.save(sample_evaluation)

        result = await repository.get_by_id(sample_evaluation.evaluation_id)

        assert result == sample_evaluation
        assert result.evaluation_id == sample_evaluation.evaluation_id

    @pytest.mark.asyncio
    async def test_get_by_id_nonexistent(
        self, repository: MockEvaluationRepository
    ) -> None:
        """Test retrieving a nonexistent evaluation returns None."""
        nonexistent_id = uuid.uuid4()

        result = await repository.get_by_id(nonexistent_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_list_by_status(self, repository: MockEvaluationRepository) -> None:
        """Test listing evaluations by status."""
        # Create evaluations with different statuses
        agent_config = AgentConfig(
            agent_type="none",
            model_provider="openai",
            model_name="gpt-4",
            model_parameters={},
            agent_parameters={},
        )

        pending_eval = Evaluation(
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

        running_eval = Evaluation(
            evaluation_id=uuid.uuid4(),
            agent_config=agent_config,
            preprocessed_benchmark_id=uuid.uuid4(),
            status="running",
            created_at=datetime.now(),
            started_at=datetime.now(),
            completed_at=None,
            results=None,
            failure_reason=None,
        )

        await repository.save(pending_eval)
        await repository.save(running_eval)

        # Test filtering by status
        pending_evals = await repository.list_by_status("pending")
        running_evals = await repository.list_by_status("running")
        completed_evals = await repository.list_by_status("completed")

        assert len(pending_evals) == 1
        assert pending_evals[0] == pending_eval
        assert len(running_evals) == 1
        assert running_evals[0] == running_eval
        assert len(completed_evals) == 0

    @pytest.mark.asyncio
    async def test_list_by_benchmark_id(
        self, repository: MockEvaluationRepository
    ) -> None:
        """Test listing evaluations by benchmark ID."""
        benchmark_id_1 = uuid.uuid4()
        benchmark_id_2 = uuid.uuid4()

        agent_config = AgentConfig(
            agent_type="none",
            model_provider="openai",
            model_name="gpt-4",
            model_parameters={},
            agent_parameters={},
        )

        eval_1 = Evaluation(
            evaluation_id=uuid.uuid4(),
            agent_config=agent_config,
            preprocessed_benchmark_id=benchmark_id_1,
            status="pending",
            created_at=datetime.now(),
            started_at=None,
            completed_at=None,
            results=None,
            failure_reason=None,
        )

        eval_2 = Evaluation(
            evaluation_id=uuid.uuid4(),
            agent_config=agent_config,
            preprocessed_benchmark_id=benchmark_id_1,
            status="running",
            created_at=datetime.now(),
            started_at=datetime.now(),
            completed_at=None,
            results=None,
            failure_reason=None,
        )

        eval_3 = Evaluation(
            evaluation_id=uuid.uuid4(),
            agent_config=agent_config,
            preprocessed_benchmark_id=benchmark_id_2,
            status="pending",
            created_at=datetime.now(),
            started_at=None,
            completed_at=None,
            results=None,
            failure_reason=None,
        )

        await repository.save(eval_1)
        await repository.save(eval_2)
        await repository.save(eval_3)

        # Test filtering by benchmark ID
        benchmark_1_evals = await repository.list_by_benchmark_id(benchmark_id_1)
        benchmark_2_evals = await repository.list_by_benchmark_id(benchmark_id_2)

        assert len(benchmark_1_evals) == 2
        assert eval_1 in benchmark_1_evals
        assert eval_2 in benchmark_1_evals
        assert len(benchmark_2_evals) == 1
        assert eval_3 in benchmark_2_evals

    @pytest.mark.asyncio
    async def test_update_evaluation(
        self, repository: MockEvaluationRepository, sample_evaluation: Evaluation
    ) -> None:
        """Test updating an existing evaluation."""
        await repository.save(sample_evaluation)

        # Start the evaluation
        updated_evaluation = sample_evaluation.start_execution()
        await repository.update(updated_evaluation)

        # Verify update
        retrieved = await repository.get_by_id(sample_evaluation.evaluation_id)
        assert retrieved.status == "running"
        assert retrieved.started_at is not None

    @pytest.mark.asyncio
    async def test_update_nonexistent_evaluation(
        self, repository: MockEvaluationRepository, sample_evaluation: Evaluation
    ) -> None:
        """Test updating a nonexistent evaluation raises error."""
        with pytest.raises(ValueError, match="not found"):
            await repository.update(sample_evaluation)

    @pytest.mark.asyncio
    async def test_delete_evaluation(
        self, repository: MockEvaluationRepository, sample_evaluation: Evaluation
    ) -> None:
        """Test deleting an existing evaluation."""
        await repository.save(sample_evaluation)

        # Verify exists before delete
        assert await repository.exists(sample_evaluation.evaluation_id) is True

        # Delete
        await repository.delete(sample_evaluation.evaluation_id)

        # Verify deleted
        assert await repository.exists(sample_evaluation.evaluation_id) is False
        assert await repository.get_by_id(sample_evaluation.evaluation_id) is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_evaluation(
        self, repository: MockEvaluationRepository
    ) -> None:
        """Test deleting a nonexistent evaluation raises error."""
        nonexistent_id = uuid.uuid4()

        with pytest.raises(ValueError, match="not found"):
            await repository.delete(nonexistent_id)

    @pytest.mark.asyncio
    async def test_exists_evaluation(
        self, repository: MockEvaluationRepository, sample_evaluation: Evaluation
    ) -> None:
        """Test checking if evaluation exists."""
        # Initially doesn't exist
        assert await repository.exists(sample_evaluation.evaluation_id) is False

        # Save and check exists
        await repository.save(sample_evaluation)
        assert await repository.exists(sample_evaluation.evaluation_id) is True

        # Delete and check doesn't exist
        await repository.delete(sample_evaluation.evaluation_id)
        assert await repository.exists(sample_evaluation.evaluation_id) is False

    @pytest.mark.asyncio
    async def test_list_all_evaluations(
        self, repository: MockEvaluationRepository
    ) -> None:
        """Test listing all evaluations."""
        agent_config = AgentConfig(
            agent_type="none",
            model_provider="openai",
            model_name="gpt-4",
            model_parameters={},
            agent_parameters={},
        )

        # Create multiple evaluations
        evaluations = []
        for _ in range(5):
            evaluation = Evaluation(
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
            evaluations.append(evaluation)
            await repository.save(evaluation)

        # Test list all without limit
        all_evals = await repository.list_all()
        assert len(all_evals) == 5
        for evaluation in evaluations:
            assert evaluation in all_evals

        # Test list all with limit
        limited_evals = await repository.list_all(limit=3)
        assert len(limited_evals) == 3
        for evaluation in limited_evals:
            assert evaluation in evaluations

    @pytest.mark.asyncio
    async def test_abstract_interface_compliance(self) -> None:
        """Test that EvaluationRepository is properly abstract."""
        # Should not be able to instantiate abstract class directly
        with pytest.raises(TypeError):
            EvaluationRepository()  # type: ignore

    def test_interface_method_signatures(self) -> None:
        """Test that the interface has all required method signatures."""
        # Verify all required methods exist
        required_methods = [
            "save",
            "get_by_id",
            "list_by_status",
            "list_by_benchmark_id",
            "update",
            "delete",
            "exists",
            "list_all",
        ]

        for method_name in required_methods:
            assert hasattr(EvaluationRepository, method_name)
            method = getattr(EvaluationRepository, method_name)
            assert callable(method)
