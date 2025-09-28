"""Acceptance tests for evaluate command functionality."""

import uuid
from datetime import datetime
from unittest.mock import Mock, patch

from click.testing import CliRunner

from ml_agents_v2.cli.main import cli
from ml_agents_v2.core.domain.entities.evaluation import Evaluation
from ml_agents_v2.core.domain.value_objects.agent_config import AgentConfig


class TestEvaluateCommands:
    """Test evaluation management commands."""

    def test_evaluate_create_command_success(self):
        """Test evaluate create command creates new evaluation."""
        runner = CliRunner()

        # Mock successful evaluation creation
        mock_evaluation_id = uuid.uuid4()
        mock_evaluation = Evaluation(
            evaluation_id=mock_evaluation_id,
            agent_config=AgentConfig(
                agent_type="chain_of_thought",
                model_provider="anthropic",
                model_name="claude-3-sonnet",
                model_parameters={"temperature": 1.0, "max_tokens": 1000},
                agent_parameters={},
            ),
            preprocessed_benchmark_id=uuid.uuid4(),
            status="pending",
            created_at=datetime.now(),
            started_at=None,
            completed_at=None,
            results=None,
            failure_reason=None,
        )

        with patch("ml_agents_v2.cli.main.Container") as mock_container:
            mock_orchestrator = Mock()
            mock_orchestrator.create_evaluation.return_value = mock_evaluation_id

            mock_container_instance = Mock()
            mock_container_instance.evaluation_orchestrator.return_value = (
                mock_orchestrator
            )
            mock_container.return_value = mock_container_instance

            result = runner.invoke(
                cli,
                [
                    "evaluate",
                    "create",
                    "--agent",
                    "cot",
                    "--model",
                    "anthropic/claude-3-sonnet",
                    "--benchmark",
                    "GPQA",
                ],
            )

            assert result.exit_code == 0
            assert "✓ Created evaluation" in result.output
            assert str(mock_evaluation_id)[:8] in result.output  # Short ID
            assert "pending" in result.output
            assert "cot" in result.output or "Chain of Thought" in result.output
            assert "anthropic/claude-3-sonnet" in result.output
            assert "GPQA" in result.output
            assert "ml-agents evaluate run" in result.output

    def test_evaluate_create_command_with_options(self):
        """Test evaluate create command with temperature and max-tokens options."""
        runner = CliRunner()

        mock_evaluation_id = uuid.uuid4()
        mock_evaluation = Evaluation(
            evaluation_id=mock_evaluation_id,
            agent_config=AgentConfig(
                agent_type="none",
                model_provider="openai",
                model_name="gpt-4",
                model_parameters={"temperature": 0.5, "max_tokens": 2000},
                agent_parameters={},
            ),
            preprocessed_benchmark_id=uuid.uuid4(),
            status="pending",
            created_at=datetime.now(),
            started_at=None,
            completed_at=None,
            results=None,
            failure_reason=None,
        )

        with patch("ml_agents_v2.cli.main.Container") as mock_container:
            mock_orchestrator = Mock()
            mock_orchestrator.create_evaluation.return_value = mock_evaluation_id

            mock_container_instance = Mock()
            mock_container_instance.evaluation_orchestrator.return_value = (
                mock_orchestrator
            )
            mock_container.return_value = mock_container_instance

            result = runner.invoke(
                cli,
                [
                    "evaluate",
                    "create",
                    "--agent",
                    "none",
                    "--model",
                    "openai/gpt-4",
                    "--benchmark",
                    "FOLIO",
                    "--temp",
                    "0.5",
                    "--max-tokens",
                    "2000",
                ],
            )

            assert result.exit_code == 0
            assert "✓ Created evaluation" in result.output
            assert "none" in result.output or "Direct" in result.output
            assert "gpt-4" in result.output

            # Verify orchestrator was called with correct config
            mock_orchestrator.create_evaluation.assert_called_once()
            call_args = mock_orchestrator.create_evaluation.call_args[1]
            assert call_args["agent_config"].model_parameters["temperature"] == 0.5
            assert call_args["agent_config"].model_parameters["max_tokens"] == 2000

    def test_evaluate_create_command_invalid_agent(self):
        """Test evaluate create command with invalid agent type."""
        runner = CliRunner()

        result = runner.invoke(
            cli,
            [
                "evaluate",
                "create",
                "--agent",
                "invalid",
                "--model",
                "test-model",
                "--benchmark",
                "GPQA",
            ],
        )

        assert result.exit_code != 0
        assert "Invalid value" in result.output
        assert "none" in result.output
        assert "cot" in result.output

    def test_evaluate_create_command_benchmark_not_found(self):
        """Test evaluate create command when benchmark doesn't exist."""
        runner = CliRunner()

        with patch("ml_agents_v2.cli.main.Container") as mock_container:
            mock_orchestrator = Mock()
            mock_orchestrator.create_evaluation.side_effect = ValueError(
                "Benchmark 'UNKNOWN' not found"
            )

            mock_container_instance = Mock()
            mock_container_instance.evaluation_orchestrator.return_value = (
                mock_orchestrator
            )
            mock_container.return_value = mock_container_instance

            result = runner.invoke(
                cli,
                [
                    "evaluate",
                    "create",
                    "--agent",
                    "cot",
                    "--model",
                    "anthropic/claude-3-sonnet",
                    "--benchmark",
                    "UNKNOWN",
                ],
            )

            assert result.exit_code == 1
            assert "✗ Error" in result.output
            assert "Benchmark 'UNKNOWN' not found" in result.output
            assert "ml-agents benchmark list" in result.output

    def test_evaluate_run_command_success(self):
        """Test evaluate run command executes evaluation with progress."""
        runner = CliRunner()

        evaluation_id = str(uuid.uuid4())

        with patch("ml_agents_v2.cli.main.Container") as mock_container:
            mock_orchestrator = Mock()

            # Mock successful execution
            mock_orchestrator.execute_evaluation.return_value = None

            # Mock progress tracking
            mock_progress_tracker = Mock()
            mock_progress_tracker.get_progress.side_effect = [
                {"current": 0, "total": 100, "percentage": 0.0, "status": "starting"},
                {
                    "current": 25,
                    "total": 100,
                    "percentage": 25.0,
                    "status": "processing",
                },
                {
                    "current": 50,
                    "total": 100,
                    "percentage": 50.0,
                    "status": "processing",
                },
                {
                    "current": 100,
                    "total": 100,
                    "percentage": 100.0,
                    "status": "completed",
                },
            ]

            mock_container_instance = Mock()
            mock_container_instance.evaluation_orchestrator.return_value = (
                mock_orchestrator
            )
            mock_container_instance.progress_tracker.return_value = (
                mock_progress_tracker
            )
            mock_container.return_value = mock_container_instance

            result = runner.invoke(cli, ["evaluate", "run", evaluation_id])

            assert result.exit_code == 0
            assert f"Running evaluation {evaluation_id[:8]}" in result.output
            assert "✓ Completed" in result.output or "100%" in result.output

    def test_evaluate_run_command_not_found(self):
        """Test evaluate run command when evaluation doesn't exist."""
        runner = CliRunner()

        evaluation_id = str(uuid.uuid4())

        with patch("ml_agents_v2.cli.main.Container") as mock_container:
            mock_orchestrator = Mock()
            mock_orchestrator.execute_evaluation.side_effect = ValueError(
                f"Evaluation {evaluation_id} not found"
            )

            mock_container_instance = Mock()
            mock_container_instance.evaluation_orchestrator.return_value = (
                mock_orchestrator
            )
            mock_container.return_value = mock_container_instance

            result = runner.invoke(cli, ["evaluate", "run", evaluation_id])

            assert result.exit_code == 1
            assert "✗ Error" in result.output
            assert f"Evaluation {evaluation_id} not found" in result.output

    def test_evaluate_run_command_already_completed(self):
        """Test evaluate run command on already completed evaluation."""
        runner = CliRunner()

        evaluation_id = str(uuid.uuid4())

        with patch("ml_agents_v2.cli.main.Container") as mock_container:
            mock_orchestrator = Mock()
            mock_orchestrator.execute_evaluation.side_effect = ValueError(
                "Evaluation already completed"
            )

            mock_container_instance = Mock()
            mock_container_instance.evaluation_orchestrator.return_value = (
                mock_orchestrator
            )
            mock_container.return_value = mock_container_instance

            result = runner.invoke(cli, ["evaluate", "run", evaluation_id])

            assert result.exit_code == 1
            assert "✗ Error" in result.output
            assert "already completed" in result.output

    def test_evaluate_list_command_success(self):
        """Test evaluate list command shows evaluations in table format."""
        runner = CliRunner()

        # Mock evaluation data
        mock_evaluations = [
            {
                "evaluation_id": uuid.uuid4(),
                "status": "completed",
                "agent_type": "chain_of_thought",
                "model_name": "claude-3-sonnet",
                "benchmark_name": "GPQA",
                "accuracy": 98.7,
                "created_at": datetime.now(),
            },
            {
                "evaluation_id": uuid.uuid4(),
                "status": "failed",
                "agent_type": "none",
                "model_name": "gpt-4",
                "benchmark_name": "FOLIO",
                "accuracy": None,
                "created_at": datetime.now(),
            },
        ]

        with patch("ml_agents_v2.cli.main.Container") as mock_container:
            mock_orchestrator = Mock()
            mock_orchestrator.list_evaluations.return_value = mock_evaluations

            mock_container_instance = Mock()
            mock_container_instance.evaluation_orchestrator.return_value = (
                mock_orchestrator
            )
            mock_container.return_value = mock_container_instance

            result = runner.invoke(cli, ["evaluate", "list"])

            assert result.exit_code == 0
            assert "ID" in result.output
            assert "Status" in result.output
            assert "Agent" in result.output
            assert "Model" in result.output
            assert "Benchmark" in result.output
            assert "Accuracy" in result.output
            assert "completed" in result.output
            assert "failed" in result.output
            assert "98.7%" in result.output
            assert "GPQA" in result.output
            assert "FOLIO" in result.output

    def test_evaluate_list_command_with_filters(self):
        """Test evaluate list command with status and benchmark filters."""
        runner = CliRunner()

        mock_evaluations = [
            {
                "evaluation_id": uuid.uuid4(),
                "status": "completed",
                "agent_type": "chain_of_thought",
                "model_name": "claude-3-sonnet",
                "benchmark_name": "GPQA",
                "accuracy": 95.0,
                "created_at": datetime.now(),
            }
        ]

        with patch("ml_agents_v2.cli.main.Container") as mock_container:
            mock_orchestrator = Mock()
            mock_orchestrator.list_evaluations.return_value = mock_evaluations

            mock_container_instance = Mock()
            mock_container_instance.evaluation_orchestrator.return_value = (
                mock_orchestrator
            )
            mock_container.return_value = mock_container_instance

            result = runner.invoke(
                cli,
                ["evaluate", "list", "--status", "completed", "--benchmark", "GPQA"],
            )

            assert result.exit_code == 0
            assert "completed" in result.output
            assert "GPQA" in result.output

            # Verify filters were passed to orchestrator
            mock_orchestrator.list_evaluations.assert_called_once()
            call_args = mock_orchestrator.list_evaluations.call_args[1]
            assert call_args.get("status_filter") == "completed"
            assert call_args.get("benchmark_filter") == "GPQA"

    def test_evaluate_list_command_empty(self):
        """Test evaluate list command when no evaluations exist."""
        runner = CliRunner()

        with patch("ml_agents_v2.cli.main.Container") as mock_container:
            mock_orchestrator = Mock()
            mock_orchestrator.list_evaluations.return_value = []

            mock_container_instance = Mock()
            mock_container_instance.evaluation_orchestrator.return_value = (
                mock_orchestrator
            )
            mock_container.return_value = mock_container_instance

            result = runner.invoke(cli, ["evaluate", "list"])

            assert result.exit_code == 0
            assert "No evaluations found" in result.output

    def test_evaluate_commands_integration_workflow(self):
        """Test complete workflow: create → run → list evaluation."""
        runner = CliRunner()

        evaluation_id = uuid.uuid4()
        mock_evaluation = Evaluation(
            evaluation_id=evaluation_id,
            agent_config=AgentConfig(
                agent_type="chain_of_thought",
                model_provider="anthropic",
                model_name="claude-3-sonnet",
                model_parameters={"temperature": 1.0, "max_tokens": 1000},
                agent_parameters={},
            ),
            preprocessed_benchmark_id=uuid.uuid4(),
            status="pending",
            created_at=datetime.now(),
            started_at=None,
            completed_at=None,
            results=None,
            failure_reason=None,
        )

        with patch("ml_agents_v2.cli.main.Container") as mock_container:
            mock_orchestrator = Mock()
            mock_orchestrator.create_evaluation.return_value = evaluation_id
            mock_orchestrator.execute_evaluation.return_value = None
            mock_orchestrator.list_evaluations.return_value = [
                {
                    "evaluation_id": evaluation_id,
                    "status": "completed",
                    "agent_type": "chain_of_thought",
                    "model_name": "claude-3-sonnet",
                    "benchmark_name": "GPQA",
                    "accuracy": 97.5,
                    "created_at": datetime.now(),
                }
            ]

            mock_progress_tracker = Mock()
            mock_progress_tracker.get_progress.return_value = {
                "current": 100,
                "total": 100,
                "percentage": 100.0,
                "status": "completed",
            }

            mock_container_instance = Mock()
            mock_container_instance.evaluation_orchestrator.return_value = (
                mock_orchestrator
            )
            mock_container_instance.progress_tracker.return_value = (
                mock_progress_tracker
            )
            mock_container.return_value = mock_container_instance

            # Step 1: Create evaluation
            create_result = runner.invoke(
                cli,
                [
                    "evaluate",
                    "create",
                    "--agent",
                    "cot",
                    "--model",
                    "anthropic/claude-3-sonnet",
                    "--benchmark",
                    "GPQA",
                ],
            )
            assert create_result.exit_code == 0
            assert "✓ Created evaluation" in create_result.output

            # Step 2: Run evaluation
            run_result = runner.invoke(cli, ["evaluate", "run", str(evaluation_id)])
            assert run_result.exit_code == 0

            # Step 3: List evaluations
            list_result = runner.invoke(cli, ["evaluate", "list"])
            assert list_result.exit_code == 0
            assert "completed" in list_result.output
            assert "97.5%" in list_result.output
