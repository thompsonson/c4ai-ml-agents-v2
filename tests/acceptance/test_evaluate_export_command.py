"""Acceptance tests for evaluate export command functionality.

This test does NOT cheat - it creates real data in a test database
and tests the actual export functionality end-to-end.
"""

import csv
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from ml_agents_v2.cli.main import cli
from ml_agents_v2.core.domain.entities.evaluation import Evaluation
from ml_agents_v2.core.domain.entities.evaluation_question_result import (
    EvaluationQuestionResult,
)
from ml_agents_v2.core.domain.entities.preprocessed_benchmark import (
    PreprocessedBenchmark,
)
from ml_agents_v2.core.domain.value_objects.agent_config import AgentConfig
from ml_agents_v2.core.domain.value_objects.question import Question
from ml_agents_v2.core.domain.value_objects.reasoning_trace import ReasoningTrace
from ml_agents_v2.infrastructure.database.repositories.benchmark_repository_impl import (
    BenchmarkRepositoryImpl,
)
from ml_agents_v2.infrastructure.database.repositories.evaluation_repository_impl import (
    EvaluationRepositoryImpl,
)
from ml_agents_v2.infrastructure.database.session_manager import DatabaseSessionManager


class TestEvaluateExportCommand:
    """Test the evaluate export command with real data (no mocking core functionality)."""

    @pytest.fixture
    def temp_db_session_manager(self, tmp_path):
        """Create a temporary database with tables for testing."""
        db_path = tmp_path / "test_export.db"
        session_manager = DatabaseSessionManager(f"sqlite:///{db_path}")
        session_manager.create_tables()
        return session_manager

    @pytest.fixture
    def test_evaluation_id(self):
        """Generate a test evaluation ID."""
        return uuid.uuid4()

    @pytest.fixture
    def test_benchmark_id(self):
        """Generate a test benchmark ID."""
        return uuid.uuid4()

    @pytest.fixture
    def sample_evaluation(self, test_evaluation_id, test_benchmark_id):
        """Create a sample evaluation entity."""
        agent_config = AgentConfig(
            agent_type="chain_of_thought",
            model_provider="anthropic",
            model_name="claude-3-sonnet",
            model_parameters={"temperature": 1.0, "max_tokens": 1000},
            agent_parameters={},
        )

        return Evaluation(
            evaluation_id=test_evaluation_id,
            agent_config=agent_config,
            preprocessed_benchmark_id=test_benchmark_id,
            status="completed",
            created_at=datetime.now(),
            started_at=datetime.now(),
            completed_at=datetime.now(),
            results=None,
            failure_reason=None,
        )

    @pytest.fixture
    def sample_benchmark(self, test_benchmark_id):
        """Create a sample benchmark entity."""
        questions = [
            Question(id="1", text="What is 2+2?", expected_answer="4", metadata={}),
            Question(id="2", text="What is 3+3?", expected_answer="6", metadata={}),
            Question(id="3", text="What is 5+5?", expected_answer="10", metadata={}),
        ]

        return PreprocessedBenchmark(
            benchmark_id=test_benchmark_id,
            name="TEST_BENCHMARK",
            description="Test benchmark for export functionality",
            questions=questions,
            metadata={},
            created_at=datetime.now(),
            question_count=len(questions),
            format_version="1.0",
        )

    @pytest.fixture
    def sample_question_results(self, test_evaluation_id):
        """Create sample evaluation question results."""
        results = []

        # Question 1: Correct answer
        results.append(
            EvaluationQuestionResult(
                id=uuid.uuid4(),
                evaluation_id=test_evaluation_id,
                question_id="1",
                question_text="What is 2+2?",
                expected_answer="4",
                actual_answer="4",
                is_correct=True,
                execution_time=1.23,
                reasoning_trace=ReasoningTrace(
                    approach_type="chain_of_thought",
                    reasoning_text="Let me think: 2 + 2 = 4",
                    metadata={"model": "claude-3-sonnet"},
                ),
                error_message=None,
                technical_details=None,
                processed_at=datetime.now(),
            )
        )

        # Question 2: Incorrect answer
        results.append(
            EvaluationQuestionResult(
                id=uuid.uuid4(),
                evaluation_id=test_evaluation_id,
                question_id="2",
                question_text="What is 3+3?",
                expected_answer="6",
                actual_answer="7",
                is_correct=False,
                execution_time=2.45,
                reasoning_trace=ReasoningTrace(
                    approach_type="chain_of_thought",
                    reasoning_text="Let me think: 3 + 3 = 7",
                    metadata={"model": "claude-3-sonnet"},
                ),
                error_message=None,
                technical_details=None,
                processed_at=datetime.now(),
            )
        )

        # Question 3: Error case
        results.append(
            EvaluationQuestionResult(
                id=uuid.uuid4(),
                evaluation_id=test_evaluation_id,
                question_id="3",
                question_text="What is 5+5?",
                expected_answer="10",
                actual_answer=None,
                is_correct=None,
                execution_time=0.89,
                reasoning_trace=None,
                error_message="Model timeout",
                technical_details="Connection timed out after 30 seconds",
                processed_at=datetime.now(),
            )
        )

        return results

    def test_export_command_full_workflow(
        self,
        temp_db_session_manager,
        sample_evaluation,
        sample_benchmark,
        sample_question_results,
        test_evaluation_id,
    ):
        """Test complete export workflow with real database operations."""
        # Setup: Create real data in test database
        evaluation_repo = EvaluationRepositoryImpl(temp_db_session_manager)
        benchmark_repo = BenchmarkRepositoryImpl(temp_db_session_manager)

        # Save benchmark
        benchmark_repo.save(sample_benchmark)

        # Save evaluation
        evaluation_repo.save(sample_evaluation)

        # Save question results directly to database
        with temp_db_session_manager.get_session() as session:
            from ml_agents_v2.infrastructure.database.models.evaluation_question_result import (
                EvaluationQuestionResultModel,
            )

            for result in sample_question_results:
                model = EvaluationQuestionResultModel.from_domain(result)
                session.add(model)
            session.commit()

        # Create temporary output file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            output_path = f.name

        try:
            runner = CliRunner()

            # Mock the container to use our test database
            with patch("ml_agents_v2.cli.main.Container") as mock_container:
                # Import needed classes for proper mocking
                # Create real orchestrator with test repositories and mocks for other dependencies
                from unittest.mock import Mock

                from ml_agents_v2.core.application.services.evaluation_orchestrator import (
                    EvaluationOrchestrator,
                )
                from ml_agents_v2.infrastructure.csv.evaluation_results_csv_writer import (
                    EvaluationResultsCsvWriter,
                )
                from ml_agents_v2.infrastructure.database.repositories.evaluation_question_result_repository_impl import (
                    EvaluationQuestionResultRepositoryImpl,
                )

                question_result_repo = EvaluationQuestionResultRepositoryImpl(
                    temp_db_session_manager
                )
                export_service = EvaluationResultsCsvWriter()

                mock_reasoning_service = Mock()
                mock_domain_services = Mock()

                test_orchestrator = EvaluationOrchestrator(
                    evaluation_repository=evaluation_repo,
                    evaluation_question_result_repository=question_result_repo,
                    benchmark_repository=benchmark_repo,
                    reasoning_infrastructure_service=mock_reasoning_service,
                    domain_service_registry=mock_domain_services,
                    export_service=export_service,
                )

                # Mock the container to return our test orchestrator
                mock_container_instance = mock_container.return_value
                mock_container_instance.evaluation_orchestrator.return_value = (
                    test_orchestrator
                )

                # Execute the export command
                short_id = str(test_evaluation_id)[:8]
                result = runner.invoke(
                    cli,
                    [
                        "evaluate",
                        "export",
                        short_id,
                        "--format",
                        "csv",
                        "--output",
                        output_path,
                    ],
                )

                # Verify command succeeded
                assert result.exit_code == 0, f"Command failed: {result.output}"
                assert "✓ Exported" in result.output
                assert short_id in result.output
                assert output_path in result.output

                # Verify CSV file was created and contains correct data
                output_file = Path(output_path)
                assert output_file.exists(), "Output CSV file was not created"

                # Read and verify CSV contents
                with open(output_path, newline="", encoding="utf-8") as csvfile:
                    reader = csv.DictReader(csvfile)
                    rows = list(reader)

                # Verify we have the correct number of rows
                assert len(rows) == 3, f"Expected 3 rows, got {len(rows)}"

                # Verify CSV headers
                expected_headers = {
                    "evaluation_id",
                    "question_id",
                    "question_text",
                    "expected_answer",
                    "actual_answer",
                    "is_correct",
                    "execution_time",
                    "error_message",
                    "processed_at",
                }
                assert set(rows[0].keys()) == expected_headers

                # Verify specific row data
                # Row 1: Correct answer
                row1 = rows[0]
                assert row1["question_id"] == "1"
                assert row1["question_text"] == "What is 2+2?"
                assert row1["expected_answer"] == "4"
                assert row1["actual_answer"] == "4"
                assert row1["is_correct"] == "True"
                assert float(row1["execution_time"]) == 1.23
                assert row1["error_message"] == ""

                # Row 2: Incorrect answer
                row2 = rows[1]
                assert row2["question_id"] == "2"
                assert row2["expected_answer"] == "6"
                assert row2["actual_answer"] == "7"
                assert row2["is_correct"] == "False"
                assert float(row2["execution_time"]) == 2.45

                # Row 3: Error case
                row3 = rows[2]
                assert row3["question_id"] == "3"
                assert row3["actual_answer"] == ""
                assert row3["is_correct"] == ""
                assert row3["error_message"] == "Model timeout"
                assert float(row3["execution_time"]) == 0.89

        finally:
            # Clean up temporary file
            Path(output_path).unlink(missing_ok=True)

    def test_export_command_evaluation_not_found(self):
        """Test export command with non-existent evaluation ID."""
        runner = CliRunner()

        # Use a non-existent evaluation ID
        non_existent_id = "12345678"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            output_path = f.name

        try:
            with patch("ml_agents_v2.cli.main.Container") as mock_container:
                from ml_agents_v2.core.application.services.exceptions import (
                    EvaluationNotFoundError,
                )

                # Mock orchestrator to raise exception
                mock_orchestrator = (
                    mock_container.return_value.evaluation_orchestrator.return_value
                )
                mock_orchestrator.export_evaluation_results.side_effect = (
                    EvaluationNotFoundError(f"Evaluation {non_existent_id} not found")
                )

                result = runner.invoke(
                    cli,
                    [
                        "evaluate",
                        "export",
                        non_existent_id,
                        "--format",
                        "csv",
                        "--output",
                        output_path,
                    ],
                )

                # Verify command failed appropriately
                assert result.exit_code == 1
                assert "✗ Error" in result.output
                assert non_existent_id in result.output

        finally:
            # Clean up temporary file
            Path(output_path).unlink(missing_ok=True)

    def test_export_command_invalid_format(self):
        """Test export command with invalid format option."""
        runner = CliRunner()

        test_id = "12345678"

        result = runner.invoke(
            cli,
            [
                "evaluate",
                "export",
                test_id,
                "--format",
                "invalid_format",
                "--output",
                "test.csv",
            ],
        )

        # Should fail due to invalid format choice
        assert result.exit_code != 0
        assert "Invalid value" in result.output or "invalid_format" in result.output

    def test_export_command_missing_output_file(self):
        """Test export command without output file specified."""
        runner = CliRunner()

        test_id = "12345678"

        result = runner.invoke(
            cli,
            [
                "evaluate",
                "export",
                test_id,
                "--format",
                "csv",
                # Missing --output parameter
            ],
        )

        # Should fail due to missing required output parameter
        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output
