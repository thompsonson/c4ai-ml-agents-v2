"""Acceptance tests for health command functionality."""

from unittest.mock import Mock, patch

from click.testing import CliRunner

from ml_agents_v2.cli.main import cli
from ml_agents_v2.infrastructure.health_checker import HealthStatus


class TestHealthCommand:
    """Test health command functionality and output formatting."""

    def test_health_command_success(self):
        """Test health command with all systems healthy."""
        runner = CliRunner()

        # Mock the health checker to return healthy status
        mock_health_status = HealthStatus(
            status="healthy",
            checks={
                "database": {"status": "healthy", "details": "Connected"},
                "openrouter": {
                    "status": "healthy",
                    "details": "API key valid",
                    "credits": 100.50,
                },
                "benchmarks": {"status": "healthy", "details": "5 available"},
            },
        )

        with patch("ml_agents_v2.cli.main.Container") as mock_container:
            mock_health_checker = Mock()
            mock_health_checker.check_health.return_value = mock_health_status

            mock_container_instance = Mock()
            mock_container_instance.health_checker.return_value = mock_health_checker
            mock_container.return_value = mock_container_instance

            result = runner.invoke(cli, ["health"])

            assert result.exit_code == 0
            assert "System Health: ✓ Healthy" in result.output
            assert "Database" in result.output
            assert "Openrouter" in result.output  # Note: Capitalized as title case
            assert "✓" in result.output  # Success indicators
            assert "Connected" in result.output
            assert "API key valid" in result.output

    def test_health_command_degraded(self):
        """Test health command with some systems degraded."""
        runner = CliRunner()

        mock_health_status = HealthStatus(
            status="degraded",
            checks={
                "database": {"status": "healthy", "details": "Connected"},
                "openrouter": {
                    "status": "degraded",
                    "details": "Rate limited",
                    "credits": 5.00,
                },
                "benchmarks": {"status": "healthy", "details": "5 available"},
            },
        )

        with patch("ml_agents_v2.cli.main.Container") as mock_container:
            mock_health_checker = Mock()
            mock_health_checker.check_health.return_value = mock_health_status

            mock_container_instance = Mock()
            mock_container_instance.health_checker.return_value = mock_health_checker
            mock_container.return_value = mock_container_instance

            result = runner.invoke(cli, ["health"])

            assert result.exit_code == 0
            assert "System Health: ⚠ Degraded" in result.output
            assert "Rate limited" in result.output
            assert "⚠" in result.output  # Warning indicators

    def test_health_command_unhealthy(self):
        """Test health command with critical systems failing."""
        runner = CliRunner()

        mock_health_status = HealthStatus(
            status="unhealthy",
            checks={
                "database": {"status": "unhealthy", "details": "Connection failed"},
                "openrouter": {"status": "unhealthy", "details": "Invalid API key"},
                "benchmarks": {"status": "healthy", "details": "5 available"},
            },
        )

        with patch("ml_agents_v2.cli.main.Container") as mock_container:
            mock_health_checker = Mock()
            mock_health_checker.check_health.return_value = mock_health_status

            mock_container_instance = Mock()
            mock_container_instance.health_checker.return_value = mock_health_checker
            mock_container.return_value = mock_container_instance

            result = runner.invoke(cli, ["health"])

            assert result.exit_code == 1  # Non-zero exit for unhealthy
            assert "System Health: ✗ Unhealthy" in result.output
            assert "Connection failed" in result.output
            assert "Invalid API key" in result.output
            assert "✗" in result.output  # Error indicators

    def test_health_command_exception_handling(self):
        """Test health command handles exceptions gracefully."""
        runner = CliRunner()

        with patch("ml_agents_v2.cli.main.Container") as mock_container:
            mock_health_checker = Mock()
            mock_health_checker.check_health.side_effect = Exception(
                "Health check failed"
            )

            mock_container_instance = Mock()
            mock_container_instance.health_checker.return_value = mock_health_checker
            mock_container.return_value = mock_container_instance

            result = runner.invoke(cli, ["health"])

            assert result.exit_code == 1
            assert "Health check failed" in result.output
            assert "✗" in result.output

    def test_health_command_verbose_output(self):
        """Test health command with verbose flag shows more detail."""
        runner = CliRunner()

        mock_health_status = HealthStatus(
            status="healthy",
            checks={
                "database": {
                    "status": "healthy",
                    "details": "Connected",
                    "response_time": "25ms",
                    "connection_pool": "5/10 active",
                },
                "openrouter": {
                    "status": "healthy",
                    "details": "API key valid",
                    "credits": 100.50,
                    "rate_limit": "1000/hour",
                },
            },
        )

        with patch("ml_agents_v2.cli.main.Container") as mock_container:
            mock_health_checker = Mock()
            mock_health_checker.check_health.return_value = mock_health_status

            mock_container_instance = Mock()
            mock_container_instance.health_checker.return_value = mock_health_checker
            mock_container.return_value = mock_container_instance

            result = runner.invoke(cli, ["--verbose", "health"])

            assert result.exit_code == 0
            assert "25ms" in result.output  # Verbose details
            assert "5/10 active" in result.output
            assert "1000/hour" in result.output

    def test_health_command_quiet_output(self):
        """Test health command with quiet flag shows minimal output."""
        runner = CliRunner()

        mock_health_status = HealthStatus(
            status="healthy",
            checks={
                "database": {"status": "healthy"},
                "openrouter": {"status": "healthy"},
            },
        )

        with patch("ml_agents_v2.cli.main.Container") as mock_container:
            mock_health_checker = Mock()
            mock_health_checker.check_health.return_value = mock_health_status

            mock_container_instance = Mock()
            mock_container_instance.health_checker.return_value = mock_health_checker
            mock_container.return_value = mock_container_instance

            result = runner.invoke(cli, ["--quiet", "health"])

            assert result.exit_code == 0
            # Quiet mode should still show overall status but minimal details
            assert "✓" in result.output or "healthy" in result.output.lower()
