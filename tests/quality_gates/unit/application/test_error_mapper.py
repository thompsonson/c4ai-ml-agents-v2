"""Tests for ApplicationErrorMapper."""

import pytest

from ml_agents_v2.core.application.services.error_mapper import ApplicationErrorMapper
from ml_agents_v2.core.application.services.exceptions import (
    BenchmarkNotFoundError,
    EvaluationNotFoundError,
    ExternalServiceError,
    ValidationError,
)
from ml_agents_v2.core.domain.repositories.exceptions import EntityNotFoundError


class TestApplicationErrorMapper:
    """Test suite for ApplicationErrorMapper."""

    @pytest.fixture
    def error_mapper(self):
        """Create error mapper instance."""
        return ApplicationErrorMapper()

    def test_map_openrouter_rate_limit_error(self, error_mapper):
        """Test mapping of OpenRouter rate limit errors."""

        # Arrange
        class MockRateLimitError(Exception):
            pass

        error = MockRateLimitError("Rate limit exceeded")
        error.__class__.__name__ = "RateLimitError"

        # Act
        failure_reason = error_mapper.map_openrouter_error(error)

        # Assert
        assert failure_reason.category == "rate_limit_exceeded"
        assert failure_reason.recoverable is True
        assert "rate limit exceeded" in failure_reason.description.lower()

    def test_map_openrouter_timeout_error(self, error_mapper):
        """Test mapping of OpenRouter timeout errors."""

        # Arrange
        class MockTimeoutError(Exception):
            pass

        error = MockTimeoutError("Request timed out")
        error.__class__.__name__ = "TimeoutError"

        # Act
        failure_reason = error_mapper.map_openrouter_error(error)

        # Assert
        assert failure_reason.category == "network_timeout"
        assert failure_reason.recoverable is True
        assert "timed out" in failure_reason.description.lower()

    def test_map_openrouter_authentication_error(self, error_mapper):
        """Test mapping of OpenRouter authentication errors."""

        # Arrange
        class MockAuthError(Exception):
            pass

        error = MockAuthError("401 Unauthorized")
        error.__class__.__name__ = "AuthenticationError"

        # Act
        failure_reason = error_mapper.map_openrouter_error(error)

        # Assert
        assert failure_reason.category == "authentication_error"
        assert failure_reason.recoverable is False
        assert "authentication failed" in failure_reason.description.lower()

    def test_map_openrouter_unknown_error(self, error_mapper):
        """Test mapping of unknown OpenRouter errors."""
        # Arrange
        error = Exception("Some unexpected error")

        # Act
        failure_reason = error_mapper.map_openrouter_error(error)

        # Assert
        assert failure_reason.category == "unknown"
        assert failure_reason.recoverable is False
        assert "unexpected" in failure_reason.description.lower()

    def test_map_repository_error_evaluation_not_found(self, error_mapper):
        """Test mapping of evaluation repository not found errors."""
        # Arrange
        repo_error = EntityNotFoundError("Evaluation", "eval-123")
        operation = "get evaluation by id"

        # Act
        app_error = error_mapper.map_repository_error(repo_error, operation)

        # Assert
        assert isinstance(app_error, EvaluationNotFoundError)
        assert "evaluation" in str(app_error).lower()

    def test_map_repository_error_benchmark_not_found(self, error_mapper):
        """Test mapping of benchmark repository not found errors."""
        # Arrange
        repo_error = EntityNotFoundError("Benchmark", "TEST_BENCHMARK")
        operation = "get benchmark by name"

        # Act
        app_error = error_mapper.map_repository_error(repo_error, operation)

        # Assert
        assert isinstance(app_error, BenchmarkNotFoundError)
        assert "benchmark" in str(app_error).lower()

    def test_map_repository_error_database_connection(self, error_mapper):
        """Test mapping of database connection errors."""
        # Arrange
        repo_error = Exception("Database connection failed")
        operation = "save evaluation"

        # Act
        app_error = error_mapper.map_repository_error(repo_error, operation)

        # Assert
        assert isinstance(app_error, ExternalServiceError)
        assert app_error.service_name == "database"
        assert app_error.recoverable is True

    def test_map_repository_error_constraint_violation(self, error_mapper):
        """Test mapping of database constraint violations."""
        # Arrange
        repo_error = Exception("UNIQUE constraint failed")
        operation = "save evaluation"

        # Act
        app_error = error_mapper.map_repository_error(repo_error, operation)

        # Assert
        assert isinstance(app_error, ValidationError)
        assert "constraint violation" in str(app_error).lower()

    def test_should_retry_error_recoverable(self, error_mapper):
        """Test retry logic for recoverable errors."""
        # Test recoverable error patterns
        recoverable_errors = [
            Exception("Connection timeout"),
            Exception("503 Service Unavailable"),
            Exception("Rate limit exceeded"),
            Exception("Temporary failure"),
        ]

        for error in recoverable_errors:
            assert error_mapper.should_retry_error(error) is True

    def test_should_retry_error_non_recoverable(self, error_mapper):
        """Test retry logic for non-recoverable errors."""
        # Test non-recoverable error patterns
        non_recoverable_errors = [
            Exception("401 Unauthorized"),
            Exception("Authentication failed"),
            Exception("Not found"),
            Exception("400 Bad Request"),
        ]

        for error in non_recoverable_errors:
            assert error_mapper.should_retry_error(error) is False

    def test_should_retry_error_external_service_error(self, error_mapper):
        """Test retry logic for ExternalServiceError."""
        # Recoverable external service error
        recoverable_error = ExternalServiceError(
            "Service temporarily unavailable",
            service_name="openrouter",
            recoverable=True,
        )
        assert error_mapper.should_retry_error(recoverable_error) is True

        # Non-recoverable external service error
        non_recoverable_error = ExternalServiceError(
            "Invalid API key",
            service_name="openrouter",
            recoverable=False,
        )
        assert error_mapper.should_retry_error(non_recoverable_error) is False
