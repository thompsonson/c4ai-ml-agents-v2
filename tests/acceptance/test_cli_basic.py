"""Acceptance tests for basic CLI structure and entry point."""

from click.testing import CliRunner

from ml_agents_v2.cli.main import cli


class TestCLIBasic:
    """Test basic CLI functionality like help, version, and command discovery."""

    def test_cli_help_displays_main_commands(self):
        """Test that --help shows available command groups."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "ML Agents v2" in result.output
        assert "evaluate" in result.output
        assert "benchmark" in result.output
        assert "health" in result.output

    def test_cli_version_displays_version(self):
        """Test that --version shows version information."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])

        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_evaluate_group_help(self):
        """Test that evaluate --help shows evaluation commands."""
        runner = CliRunner()
        result = runner.invoke(cli, ["evaluate", "--help"])

        assert result.exit_code == 0
        assert "create" in result.output
        assert "run" in result.output
        assert "list" in result.output

    def test_benchmark_group_help(self):
        """Test that benchmark --help shows benchmark commands."""
        runner = CliRunner()
        result = runner.invoke(cli, ["benchmark", "--help"])

        assert result.exit_code == 0
        assert "list" in result.output
        assert "show" in result.output

    def test_health_command_help(self):
        """Test that health --help shows health command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["health", "--help"])

        assert result.exit_code == 0
        assert "health" in result.output.lower()

    def test_invalid_command_shows_error(self):
        """Test that invalid commands show helpful error messages."""
        runner = CliRunner()
        result = runner.invoke(cli, ["invalid-command"])

        assert result.exit_code != 0
        assert "No such command" in result.output

    def test_global_options_work(self):
        """Test that global options like --verbose are recognized."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--verbose", "--help"])

        assert result.exit_code == 0
        assert "ML Agents v2" in result.output
