"""Tests for health check service implementation."""

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from ml_agents_v2.infrastructure.database.session_manager import DatabaseSessionManager
from ml_agents_v2.infrastructure.health_checker import HealthChecker, HealthStatus
from ml_agents_v2.infrastructure.providers import OpenRouterClient


class TestHealthStatus:
    """Test HealthStatus model."""

    def test_health_status_creation(self):
        """Test that HealthStatus can be created with valid data."""
        checks = {
            "database": {"status": "healthy", "message": "Connection successful"},
            "openrouter": {"status": "healthy", "message": "API accessible"},
        }
        status = HealthStatus(status="healthy", checks=checks)

        assert status.status == "healthy"
        assert status.checks == checks

    def test_health_status_with_error_details(self):
        """Test HealthStatus with error information."""
        checks = {
            "database": {
                "status": "unhealthy",
                "message": "Connection failed",
                "error": "Database connection timeout",
            }
        }
        status = HealthStatus(status="unhealthy", checks=checks)

        assert status.status == "unhealthy"
        assert "error" in status.checks["database"]

    def test_health_status_mixed_components(self):
        """Test HealthStatus with mixed component health."""
        checks = {
            "database": {"status": "healthy", "message": "OK"},
            "openrouter": {"status": "unhealthy", "error": "API down"},
            "cache": {"status": "healthy", "message": "Connected"},
        }
        status = HealthStatus(status="degraded", checks=checks)

        assert status.status == "degraded"
        assert len(status.checks) == 3


class TestHealthChecker:
    """Test HealthChecker implementation."""

    @pytest.fixture
    def mock_session_manager(self):
        """Create mock database session manager."""
        return MagicMock(spec=DatabaseSessionManager)

    @pytest.fixture
    def mock_openrouter_client(self):
        """Create mock OpenRouter client."""
        return MagicMock(spec=OpenRouterClient)

    @pytest.fixture
    def health_checker(self, mock_session_manager, mock_openrouter_client):
        """Create HealthChecker instance with mocks."""
        return HealthChecker(
            database_session_manager=mock_session_manager,
            openrouter_client=mock_openrouter_client,
        )

    def test_health_checker_initialization(
        self, mock_session_manager, mock_openrouter_client
    ):
        """Test that HealthChecker initializes correctly."""
        checker = HealthChecker(
            database_session_manager=mock_session_manager,
            openrouter_client=mock_openrouter_client,
        )

        assert checker.database_session_manager == mock_session_manager
        assert checker.openrouter_client == mock_openrouter_client
        assert hasattr(checker, "logger")

    def test_check_health_all_healthy(self, health_checker):
        """Test health check when all components are healthy."""
        # Mock healthy database
        mock_session = MagicMock()
        mock_session.execute.return_value.scalar.return_value = 1
        health_checker.database_session_manager.get_session.return_value.__enter__.return_value = (
            mock_session
        )
        health_checker.database_session_manager.get_session.return_value.__exit__.return_value = (
            None
        )

        # Mock healthy OpenRouter
        health_checker.openrouter_client.health_check.return_value = {
            "status": "ok",
            "credit_left": 100.0,
        }

        result = health_checker.check_health()

        assert isinstance(result, HealthStatus)
        assert result.status == "healthy"
        assert result.checks["database"]["status"] == "healthy"
        assert result.checks["openrouter"]["status"] == "healthy"
        assert "credit_left" in result.checks["openrouter"]

    def test_check_health_database_unhealthy(self, health_checker):
        """Test health check when database is unhealthy."""
        # Mock database failure
        health_checker.database_session_manager.get_session.side_effect = (
            SQLAlchemyError("Database connection failed")
        )

        # Mock healthy OpenRouter
        health_checker.openrouter_client.health_check.return_value = {"status": "ok"}

        result = health_checker.check_health()

        assert result.status == "degraded"
        assert result.checks["database"]["status"] == "unhealthy"
        assert result.checks["openrouter"]["status"] == "healthy"
        assert "Database connection failed" in result.checks["database"]["error"]

    def test_check_health_openrouter_unhealthy(self, health_checker):
        """Test health check when OpenRouter is unhealthy."""
        # Mock healthy database
        mock_session = MagicMock()
        mock_session.execute.return_value.scalar.return_value = 1
        health_checker.database_session_manager.get_session.return_value.__enter__.return_value = (
            mock_session
        )
        health_checker.database_session_manager.get_session.return_value.__exit__.return_value = (
            None
        )

        # Mock OpenRouter failure
        health_checker.openrouter_client.health_check.side_effect = Exception(
            "API connection failed"
        )

        result = health_checker.check_health()

        assert result.status == "degraded"
        assert result.checks["database"]["status"] == "healthy"
        assert result.checks["openrouter"]["status"] == "unhealthy"
        assert "API connection failed" in result.checks["openrouter"]["error"]

    def test_check_health_all_unhealthy(self, health_checker):
        """Test health check when all components are unhealthy."""
        # Mock database failure
        health_checker.database_session_manager.get_session.side_effect = (
            SQLAlchemyError("Database error")
        )

        # Mock OpenRouter failure
        health_checker.openrouter_client.health_check.side_effect = Exception(
            "API error"
        )

        result = health_checker.check_health()

        assert result.status == "unhealthy"
        assert result.checks["database"]["status"] == "unhealthy"
        assert result.checks["openrouter"]["status"] == "unhealthy"

    def test_check_database_success(self, health_checker):
        """Test successful database health check."""
        mock_session = MagicMock()
        mock_session.execute.return_value.scalar.return_value = 1
        health_checker.database_session_manager.get_session.return_value.__enter__.return_value = (
            mock_session
        )
        health_checker.database_session_manager.get_session.return_value.__exit__.return_value = (
            None
        )

        result = health_checker._check_database()

        assert result["status"] == "healthy"
        assert result["message"] == "Database connection successful"
        # Verify that execute was called once and the argument is a TextClause for "SELECT 1"
        assert mock_session.execute.call_count == 1
        call_args = mock_session.execute.call_args[0][0]
        assert str(call_args) == "SELECT 1"

    def test_check_database_failure(self, health_checker):
        """Test database health check failure."""
        health_checker.database_session_manager.get_session.side_effect = (
            SQLAlchemyError("Connection timeout")
        )

        result = health_checker._check_database()

        assert result["status"] == "unhealthy"
        assert result["message"] == "Database connection failed"
        assert result["error"] == "Connection timeout"

    def test_check_database_generic_exception(self, health_checker):
        """Test database health check with generic exception."""
        health_checker.database_session_manager.get_session.side_effect = Exception(
            "Unexpected error"
        )

        result = health_checker._check_database()

        assert result["status"] == "unhealthy"
        assert result["message"] == "Database connection failed"
        assert result["error"] == "Unexpected error"

    def test_check_openrouter_success(self, health_checker):
        """Test successful OpenRouter health check."""
        health_checker.openrouter_client.health_check.return_value = {
            "status": "ok",
            "credit_left": 50.75,
            "usage": {"requests": 100, "tokens": 10000},
        }

        result = health_checker._check_openrouter()

        assert result["status"] == "healthy"
        assert result["message"] == "OpenRouter API connection successful"
        assert result["credit_left"] == 50.75
        assert result["usage"]["requests"] == 100

    def test_check_openrouter_minimal_response(self, health_checker):
        """Test OpenRouter health check with minimal response."""
        health_checker.openrouter_client.health_check.return_value = {"status": "ok"}

        result = health_checker._check_openrouter()

        assert result["status"] == "healthy"
        assert result["message"] == "OpenRouter API connection successful"
        # Should not have credit_left or usage keys when not provided
        assert "credit_left" not in result
        assert "usage" not in result

    def test_check_openrouter_with_partial_data(self, health_checker):
        """Test OpenRouter health check with partial optional data."""
        health_checker.openrouter_client.health_check.return_value = {
            "status": "ok",
            "credit_left": 25.50,
        }

        result = health_checker._check_openrouter()

        assert result["status"] == "healthy"
        assert result["credit_left"] == 25.50
        assert "usage" not in result

    def test_check_openrouter_failure(self, health_checker):
        """Test OpenRouter health check failure."""
        health_checker.openrouter_client.health_check.side_effect = Exception(
            "Authentication failed"
        )

        result = health_checker._check_openrouter()

        assert result["status"] == "unhealthy"
        assert result["message"] == "OpenRouter API connection failed"
        assert result["error"] == "Authentication failed"

    def test_determine_overall_status_all_healthy(self, health_checker):
        """Test overall status determination when all components are healthy."""
        checks = {
            "database": {"status": "healthy"},
            "openrouter": {"status": "healthy"},
            "cache": {"status": "healthy"},
        }

        result = health_checker._determine_overall_status(checks)
        assert result == "healthy"

    def test_determine_overall_status_all_unhealthy(self, health_checker):
        """Test overall status determination when all components are unhealthy."""
        checks = {
            "database": {"status": "unhealthy"},
            "openrouter": {"status": "unhealthy"},
        }

        result = health_checker._determine_overall_status(checks)
        assert result == "unhealthy"

    def test_determine_overall_status_mixed(self, health_checker):
        """Test overall status determination with mixed component health."""
        checks = {
            "database": {"status": "healthy"},
            "openrouter": {"status": "unhealthy"},
            "cache": {"status": "healthy"},
        }

        result = health_checker._determine_overall_status(checks)
        assert result == "degraded"

    def test_determine_overall_status_single_component_healthy(self, health_checker):
        """Test overall status determination with single healthy component."""
        checks = {"database": {"status": "healthy"}}

        result = health_checker._determine_overall_status(checks)
        assert result == "healthy"

    def test_determine_overall_status_single_component_unhealthy(self, health_checker):
        """Test overall status determination with single unhealthy component."""
        checks = {"database": {"status": "unhealthy"}}

        result = health_checker._determine_overall_status(checks)
        assert result == "unhealthy"

    def test_determine_overall_status_empty_checks(self, health_checker):
        """Test overall status determination with no components."""
        checks = {}

        result = health_checker._determine_overall_status(checks)
        assert result == "healthy"  # No failures means healthy

    @patch("ml_agents_v2.infrastructure.health_checker.get_logger")
    def test_logging_on_database_errors(self, mock_get_logger, health_checker):
        """Test that database errors are properly logged."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Create new instance to trigger logger setup
        checker = HealthChecker(
            database_session_manager=health_checker.database_session_manager,
            openrouter_client=health_checker.openrouter_client,
        )
        checker.logger = mock_logger

        # Trigger database error
        checker.database_session_manager.get_session.side_effect = Exception(
            "Test database error"
        )
        checker._check_database()

        # Verify logging was called
        mock_logger.error.assert_called_with(
            "Database health check failed", error="Test database error"
        )

    @patch("ml_agents_v2.infrastructure.health_checker.get_logger")
    def test_logging_on_openrouter_errors(self, mock_get_logger, health_checker):
        """Test that OpenRouter errors are properly logged."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Create new instance to trigger logger setup
        checker = HealthChecker(
            database_session_manager=health_checker.database_session_manager,
            openrouter_client=health_checker.openrouter_client,
        )
        checker.logger = mock_logger

        # Trigger OpenRouter error
        checker.openrouter_client.health_check.side_effect = Exception("Test API error")
        checker._check_openrouter()

        # Verify logging was called
        mock_logger.error.assert_called_with(
            "OpenRouter health check failed", error="Test API error"
        )

    def test_health_checker_logger_initialization(
        self, mock_session_manager, mock_openrouter_client
    ):
        """Test that logger is properly initialized during object creation."""
        with patch(
            "ml_agents_v2.infrastructure.health_checker.get_logger"
        ) as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            checker = HealthChecker(
                database_session_manager=mock_session_manager,
                openrouter_client=mock_openrouter_client,
            )

            # Verify logger was requested with correct module name
            mock_get_logger.assert_called_once_with(
                "ml_agents_v2.infrastructure.health_checker"
            )
            assert checker.logger == mock_logger
