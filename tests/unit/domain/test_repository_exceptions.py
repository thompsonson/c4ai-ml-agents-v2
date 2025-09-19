"""Tests for repository exceptions."""

import pytest

from ml_agents_v2.core.domain.repositories.exceptions import (
    DuplicateEntityError,
    EntityNotFoundError,
    RepositoryConnectionError,
    RepositoryError,
    RepositoryTransactionError,
)


class TestRepositoryError:
    """Test suite for RepositoryError base exception."""

    def test_repository_error_creation(self) -> None:
        """Test RepositoryError can be created with message."""
        error = RepositoryError("Test error message")

        assert str(error) == "Test error message"
        assert error.cause is None

    def test_repository_error_with_cause(self) -> None:
        """Test RepositoryError can be created with underlying cause."""
        original_error = ValueError("Original error")
        error = RepositoryError("Wrapped error", cause=original_error)

        assert str(error) == "Wrapped error"
        assert error.cause is original_error

    def test_repository_error_inheritance(self) -> None:
        """Test RepositoryError inherits from Exception."""
        error = RepositoryError("Test")

        assert isinstance(error, Exception)
        assert isinstance(error, RepositoryError)


class TestEntityNotFoundError:
    """Test suite for EntityNotFoundError."""

    def test_entity_not_found_error_creation(self) -> None:
        """Test EntityNotFoundError formats message correctly."""
        error = EntityNotFoundError("Evaluation", "eval-123")

        assert str(error) == "Evaluation with ID 'eval-123' not found"
        assert error.entity_type == "Evaluation"
        assert error.entity_id == "eval-123"

    def test_entity_not_found_error_inheritance(self) -> None:
        """Test EntityNotFoundError inherits from RepositoryError."""
        error = EntityNotFoundError("Test", "123")

        assert isinstance(error, RepositoryError)
        assert isinstance(error, EntityNotFoundError)

    def test_entity_not_found_error_different_types(self) -> None:
        """Test EntityNotFoundError works with different entity types."""
        eval_error = EntityNotFoundError("Evaluation", "eval-456")
        benchmark_error = EntityNotFoundError("PreprocessedBenchmark", "bench-789")

        assert "Evaluation" in str(eval_error)
        assert "eval-456" in str(eval_error)
        assert "PreprocessedBenchmark" in str(benchmark_error)
        assert "bench-789" in str(benchmark_error)


class TestDuplicateEntityError:
    """Test suite for DuplicateEntityError."""

    def test_duplicate_entity_error_creation(self) -> None:
        """Test DuplicateEntityError formats message correctly."""
        error = DuplicateEntityError("Evaluation", "eval-123")

        assert str(error) == "Evaluation with ID 'eval-123' already exists"
        assert error.entity_type == "Evaluation"
        assert error.entity_id == "eval-123"

    def test_duplicate_entity_error_inheritance(self) -> None:
        """Test DuplicateEntityError inherits from RepositoryError."""
        error = DuplicateEntityError("Test", "123")

        assert isinstance(error, RepositoryError)
        assert isinstance(error, DuplicateEntityError)

    def test_duplicate_entity_error_different_types(self) -> None:
        """Test DuplicateEntityError works with different entity types."""
        eval_error = DuplicateEntityError("Evaluation", "eval-456")
        benchmark_error = DuplicateEntityError("PreprocessedBenchmark", "bench-789")

        assert "already exists" in str(eval_error)
        assert "eval-456" in str(eval_error)
        assert "already exists" in str(benchmark_error)
        assert "bench-789" in str(benchmark_error)


class TestRepositoryConnectionError:
    """Test suite for RepositoryConnectionError."""

    def test_repository_connection_error_default_message(self) -> None:
        """Test RepositoryConnectionError has default message."""
        error = RepositoryConnectionError()

        assert str(error) == "Failed to connect to repository"

    def test_repository_connection_error_custom_message(self) -> None:
        """Test RepositoryConnectionError accepts custom message."""
        error = RepositoryConnectionError("Database connection timeout")

        assert str(error) == "Database connection timeout"

    def test_repository_connection_error_inheritance(self) -> None:
        """Test RepositoryConnectionError inherits from RepositoryError."""
        error = RepositoryConnectionError()

        assert isinstance(error, RepositoryError)
        assert isinstance(error, RepositoryConnectionError)


class TestRepositoryTransactionError:
    """Test suite for RepositoryTransactionError."""

    def test_repository_transaction_error_default_message(self) -> None:
        """Test RepositoryTransactionError has default message."""
        error = RepositoryTransactionError()

        assert str(error) == "Repository transaction failed"

    def test_repository_transaction_error_custom_message(self) -> None:
        """Test RepositoryTransactionError accepts custom message."""
        error = RepositoryTransactionError("Transaction rollback failed")

        assert str(error) == "Transaction rollback failed"

    def test_repository_transaction_error_inheritance(self) -> None:
        """Test RepositoryTransactionError inherits from RepositoryError."""
        error = RepositoryTransactionError()

        assert isinstance(error, RepositoryError)
        assert isinstance(error, RepositoryTransactionError)


class TestExceptionHierarchy:
    """Test suite for exception hierarchy relationships."""

    def test_all_repository_exceptions_inherit_from_base(self) -> None:
        """Test all repository exceptions inherit from RepositoryError."""
        exceptions = [
            EntityNotFoundError("Test", "123"),
            DuplicateEntityError("Test", "123"),
            RepositoryConnectionError(),
            RepositoryTransactionError(),
        ]

        for exc in exceptions:
            assert isinstance(exc, RepositoryError)
            assert isinstance(exc, Exception)

    def test_exception_raising_and_catching(self) -> None:
        """Test exceptions can be raised and caught properly."""
        # Test EntityNotFoundError
        with pytest.raises(EntityNotFoundError) as exc_info:
            raise EntityNotFoundError("Evaluation", "test-id")
        assert exc_info.value.entity_type == "Evaluation"
        assert exc_info.value.entity_id == "test-id"

        # Test DuplicateEntityError
        with pytest.raises(DuplicateEntityError) as exc_info:
            raise DuplicateEntityError("Benchmark", "dup-id")
        assert exc_info.value.entity_type == "Benchmark"
        assert exc_info.value.entity_id == "dup-id"

        # Test catching by base class
        with pytest.raises(RepositoryError):
            raise RepositoryConnectionError("Connection failed")

    def test_exception_chaining_with_cause(self) -> None:
        """Test exception chaining works correctly."""
        original = ValueError("Database constraint violation")
        wrapped = RepositoryError("Failed to save entity", cause=original)

        assert wrapped.cause is original
        assert str(wrapped) == "Failed to save entity"
        assert str(wrapped.cause) == "Database constraint violation"
