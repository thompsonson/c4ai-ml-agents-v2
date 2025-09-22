"""Acceptance tests for benchmark command functionality."""

import uuid
from datetime import datetime
from unittest.mock import Mock, patch

from click.testing import CliRunner

from ml_agents_v2.cli.main import cli
from ml_agents_v2.core.domain.entities.preprocessed_benchmark import (
    PreprocessedBenchmark,
)
from ml_agents_v2.core.domain.value_objects.question import Question


class TestBenchmarkCommands:
    """Test benchmark management commands."""

    def test_benchmark_list_command_success(self):
        """Test benchmark list command shows available benchmarks."""
        runner = CliRunner()

        # Mock benchmark data
        questions = [
            Question(
                id="1", text="Test question 1", expected_answer="Answer 1", metadata={}
            ),
            Question(
                id="2", text="Test question 2", expected_answer="Answer 2", metadata={}
            ),
        ]

        mock_benchmarks = [
            PreprocessedBenchmark(
                benchmark_id=uuid.uuid4(),
                name="GPQA",
                description="Graduate-level physics, chemistry, and biology questions",
                questions=questions,
                metadata={"difficulty": "graduate", "domain": "science"},
                created_at=datetime.now(),
                question_count=len(questions),
                format_version="1.0",
            ),
            PreprocessedBenchmark(
                benchmark_id=uuid.uuid4(),
                name="FOLIO",
                description="Logic-based reasoning benchmark",
                questions=questions,
                metadata={"difficulty": "advanced", "domain": "logic"},
                created_at=datetime.now(),
                question_count=len(questions),
                format_version="1.0",
            ),
        ]

        with patch("ml_agents_v2.cli.main.Container") as mock_container:
            mock_benchmark_processor = Mock()
            mock_benchmark_processor.list_benchmarks.return_value = mock_benchmarks

            mock_container_instance = Mock()
            mock_container_instance.benchmark_processor.return_value = (
                mock_benchmark_processor
            )
            mock_container.return_value = mock_container_instance

            result = runner.invoke(cli, ["benchmark", "list"])

            assert result.exit_code == 0
            assert "GPQA" in result.output
            assert "FOLIO" in result.output
            assert "Graduate-level physics" in result.output
            assert "Logic-based reasoning" in result.output

    def test_benchmark_list_command_empty(self):
        """Test benchmark list command when no benchmarks available."""
        runner = CliRunner()

        with patch("ml_agents_v2.cli.main.Container") as mock_container:
            mock_benchmark_processor = Mock()
            mock_benchmark_processor.list_benchmarks.return_value = []

            mock_container_instance = Mock()
            mock_container_instance.benchmark_processor.return_value = (
                mock_benchmark_processor
            )
            mock_container.return_value = mock_container_instance

            result = runner.invoke(cli, ["benchmark", "list"])

            assert result.exit_code == 0
            assert "No benchmarks available" in result.output

    def test_benchmark_show_command_success(self):
        """Test benchmark show command displays detailed benchmark info."""
        runner = CliRunner()

        # Create detailed benchmark for show command
        questions = [
            Question(id="q1", text="What is 2+2?", expected_answer="4", metadata={}),
            Question(
                id="q2",
                text="What is the capital of France?",
                expected_answer="Paris",
                metadata={},
            ),
            Question(
                id="q3", text="What is H2O?", expected_answer="Water", metadata={}
            ),
        ]

        mock_benchmark = PreprocessedBenchmark(
            benchmark_id=uuid.uuid4(),
            name="SAMPLE_BENCHMARK",
            description="Sample test benchmark for demonstrations",
            questions=questions,
            metadata={
                "difficulty": "easy",
                "domain": "general",
                "source": "synthetic",
                "created_by": "research_team",
            },
            created_at=datetime.now(),
            question_count=len(questions),
            format_version="1.0",
        )

        with patch("ml_agents_v2.cli.main.Container") as mock_container:
            mock_benchmark_processor = Mock()
            mock_benchmark_processor.get_benchmark_details.return_value = mock_benchmark

            mock_container_instance = Mock()
            mock_container_instance.benchmark_processor.return_value = (
                mock_benchmark_processor
            )
            mock_container.return_value = mock_container_instance

            result = runner.invoke(cli, ["benchmark", "show", "SAMPLE"])

            assert result.exit_code == 0
            assert "SAMPLE_BENCHMARK" in result.output
            assert "Sample test benchmark" in result.output
            assert "Questions: 3" in result.output
            assert "What is 2+2?" in result.output
            assert "What is the capital" in result.output
            assert "difficulty" in result.output and "easy" in result.output

    def test_benchmark_show_command_not_found(self):
        """Test benchmark show command when benchmark doesn't exist."""
        runner = CliRunner()

        with patch("ml_agents_v2.cli.main.Container") as mock_container:
            mock_benchmark_processor = Mock()
            mock_benchmark_processor.get_benchmark_details.return_value = None

            mock_container_instance = Mock()
            mock_container_instance.benchmark_processor.return_value = (
                mock_benchmark_processor
            )
            mock_container.return_value = mock_container_instance

            result = runner.invoke(cli, ["benchmark", "show", "NONEXISTENT"])

            assert result.exit_code == 1
            assert "Benchmark 'NONEXISTENT' not found" in result.output

    def test_benchmark_show_command_error_handling(self):
        """Test benchmark show command handles service errors gracefully."""
        runner = CliRunner()

        with patch("ml_agents_v2.cli.main.Container") as mock_container:
            mock_benchmark_processor = Mock()
            mock_benchmark_processor.get_benchmark_details.side_effect = Exception(
                "Database connection failed"
            )

            mock_container_instance = Mock()
            mock_container_instance.benchmark_processor.return_value = (
                mock_benchmark_processor
            )
            mock_container.return_value = mock_container_instance

            result = runner.invoke(cli, ["benchmark", "show", "SAMPLE"])

            assert result.exit_code == 1
            assert "Error retrieving benchmark" in result.output
            assert "Database connection failed" in result.output

    def test_benchmark_list_with_verbose_option(self):
        """Test benchmark list command with verbose flag shows more details."""
        runner = CliRunner()

        # Create 50 unique questions
        questions = [
            Question(
                id=f"q_{i}",
                text=f"Test question {i}",
                expected_answer=f"Answer {i}",
                metadata={},
            )
            for i in range(50)
        ]
        mock_benchmarks = [
            PreprocessedBenchmark(
                benchmark_id=uuid.uuid4(),
                name="VERBOSE_TEST",
                description="Test benchmark for verbose output",
                questions=questions,  # 50 unique questions
                metadata={"complexity": "high", "version": "1.2"},
                created_at=datetime.now(),
                question_count=len(questions),
                format_version="1.0",
            )
        ]

        with patch("ml_agents_v2.cli.main.Container") as mock_container:
            mock_benchmark_processor = Mock()
            mock_benchmark_processor.list_benchmarks.return_value = mock_benchmarks

            mock_container_instance = Mock()
            mock_container_instance.benchmark_processor.return_value = (
                mock_benchmark_processor
            )
            mock_container.return_value = mock_container_instance

            result = runner.invoke(cli, ["--verbose", "benchmark", "list"])

            assert result.exit_code == 0
            assert "VERBOSE_TEST" in result.output
            assert "50 questions" in result.output  # Verbose should show question count
            assert "complexity: high" in result.output  # Verbose should show metadata

    def test_benchmark_commands_integration(self):
        """Test that benchmark commands work together (list then show)."""
        runner = CliRunner()

        questions = [
            Question(id="1", text="Test", expected_answer="Answer", metadata={})
        ]
        mock_benchmark_list = [
            PreprocessedBenchmark(
                benchmark_id=uuid.uuid4(),
                name="INTEGRATION_TEST",
                description="Integration test benchmark",
                questions=questions,
                metadata={},
                created_at=datetime.now(),
                question_count=len(questions),
                format_version="1.0",
            )
        ]

        mock_benchmark_detail = mock_benchmark_list[0]

        with patch("ml_agents_v2.cli.main.Container") as mock_container:
            mock_benchmark_processor = Mock()
            mock_benchmark_processor.list_benchmarks.return_value = mock_benchmark_list
            mock_benchmark_processor.get_benchmark_details.return_value = (
                mock_benchmark_detail
            )

            mock_container_instance = Mock()
            mock_container_instance.benchmark_processor.return_value = (
                mock_benchmark_processor
            )
            mock_container.return_value = mock_container_instance

            # First list benchmarks
            list_result = runner.invoke(cli, ["benchmark", "list"])
            assert list_result.exit_code == 0
            assert "INTEGRATION_TEST" in list_result.output

            # Then show detailed view of the benchmark
            show_result = runner.invoke(cli, ["benchmark", "show", "INTEGRATION_TEST"])
            assert show_result.exit_code == 0
            assert "Integration test benchmark" in show_result.output
