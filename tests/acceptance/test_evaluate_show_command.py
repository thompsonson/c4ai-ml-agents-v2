"""Acceptance tests for evaluate show command functionality."""

import uuid
from datetime import datetime
from unittest.mock import Mock, patch

from click.testing import CliRunner

from ml_agents_v2.cli.main import cli


class TestEvaluateShowCommand:
    """Test evaluation show command."""

    def test_evaluate_show_command_completed_evaluation(self):
        """Test evaluate show command displays detailed results for completed evaluation."""
        runner = CliRunner()

        evaluation_id = str(uuid.uuid4())

        with patch("ml_agents_v2.cli.main.Container") as mock_container:
            mock_orchestrator = Mock()

            # Mock get_evaluation_info to return completed evaluation
            from ml_agents_v2.core.application.dto.evaluation_info import EvaluationInfo

            evaluation_info = Mock(spec=EvaluationInfo)
            evaluation_info.evaluation_id = uuid.UUID(evaluation_id)
            evaluation_info.status = "completed"
            evaluation_info.agent_type = "chain_of_thought"
            evaluation_info.model_name = "claude-3-sonnet"
            evaluation_info.benchmark_name = "GPQA"
            evaluation_info.created_at = datetime.now()
            evaluation_info.completed_at = datetime.now()
            mock_orchestrator.get_evaluation_info.return_value = evaluation_info

            # Mock get_evaluation_results for detailed results
            from ml_agents_v2.core.application.dto.evaluation_summary import (
                EvaluationSummary,
            )

            evaluation_summary = Mock(spec=EvaluationSummary)
            evaluation_summary.evaluation_id = uuid.UUID(evaluation_id)
            evaluation_summary.status = "completed"
            evaluation_summary.agent_type = "chain_of_thought"
            evaluation_summary.model_name = "claude-3-sonnet"
            evaluation_summary.benchmark_name = "GPQA"
            evaluation_summary.total_questions = 448
            evaluation_summary.correct_answers = 141
            evaluation_summary.accuracy = 31.47
            evaluation_summary.execution_time_minutes = 7.66
            evaluation_summary.average_time_per_question = 1.036
            evaluation_summary.error_count = 0
            evaluation_summary.created_at = datetime.now()
            evaluation_summary.completed_at = datetime.now()

            mock_orchestrator.get_evaluation_results.return_value = evaluation_summary

            mock_container_instance = Mock()
            mock_container_instance.evaluation_orchestrator.return_value = (
                mock_orchestrator
            )
            mock_container.return_value = mock_container_instance

            result = runner.invoke(cli, ["evaluate", "show", evaluation_id])

            assert result.exit_code == 0
            assert f"Evaluation Details: {evaluation_id[:8]}" in result.output
            assert "completed" in result.output
            assert "GPQA" in result.output
            assert "Chain of Thought" in result.output
            assert "claude-3-sonnet" in result.output
            assert "448" in result.output  # total questions
            assert "141" in result.output  # correct answers
            assert "31.47%" in result.output  # accuracy
            assert (
                "1.04s" in result.output or "1.036" in result.output
            )  # avg execution time
            assert "0" in result.output  # error count

    def test_evaluate_show_command_with_short_id(self):
        """Test evaluate show command works with short evaluation ID."""
        runner = CliRunner()

        evaluation_id = str(uuid.uuid4())
        short_id = evaluation_id[:8]

        with patch("ml_agents_v2.cli.main.Container") as mock_container:
            mock_orchestrator = Mock()

            # Mock list_evaluations to find by short ID (same pattern as run command)
            from ml_agents_v2.core.application.dto.evaluation_info import EvaluationInfo

            evaluation_info = Mock(spec=EvaluationInfo)
            evaluation_info.evaluation_id = uuid.UUID(evaluation_id)
            evaluation_info.status = "completed"
            evaluation_info.agent_type = "chain_of_thought"
            evaluation_info.model_name = "claude-3-sonnet"
            evaluation_info.benchmark_name = "GPQA"
            evaluation_info.created_at = datetime.now()
            evaluation_info.completed_at = datetime.now()

            mock_orchestrator.list_evaluations.return_value = [evaluation_info]
            mock_orchestrator.get_evaluation_info.return_value = evaluation_info

            # Mock get_evaluation_results
            from ml_agents_v2.core.application.dto.evaluation_summary import (
                EvaluationSummary,
            )

            evaluation_summary = Mock(spec=EvaluationSummary)
            evaluation_summary.evaluation_id = uuid.UUID(evaluation_id)
            evaluation_summary.status = "completed"
            evaluation_summary.agent_type = "chain_of_thought"
            evaluation_summary.model_name = "claude-3-sonnet"
            evaluation_summary.benchmark_name = "GPQA"
            evaluation_summary.total_questions = 448
            evaluation_summary.correct_answers = 141
            evaluation_summary.accuracy = 31.47
            evaluation_summary.execution_time_minutes = 7.66
            evaluation_summary.average_time_per_question = 1.036
            evaluation_summary.error_count = 0
            evaluation_summary.created_at = datetime.now()
            evaluation_summary.completed_at = datetime.now()

            mock_orchestrator.get_evaluation_results.return_value = evaluation_summary

            mock_container_instance = Mock()
            mock_container_instance.evaluation_orchestrator.return_value = (
                mock_orchestrator
            )
            mock_container.return_value = mock_container_instance

            result = runner.invoke(cli, ["evaluate", "show", short_id])

            assert result.exit_code == 0
            assert f"Evaluation Details: {short_id}" in result.output
            assert "31.47%" in result.output

    def test_evaluate_show_command_interrupted_evaluation(self):
        """Test evaluate show command displays partial results for interrupted evaluation."""
        runner = CliRunner()

        evaluation_id = str(uuid.uuid4())

        with patch("ml_agents_v2.cli.main.Container") as mock_container:
            mock_orchestrator = Mock()

            # Mock get_evaluation_info to return interrupted evaluation
            from ml_agents_v2.core.application.dto.evaluation_info import EvaluationInfo

            evaluation_info = Mock(spec=EvaluationInfo)
            evaluation_info.evaluation_id = uuid.UUID(evaluation_id)
            evaluation_info.status = "interrupted"
            evaluation_info.agent_type = "chain_of_thought"
            evaluation_info.model_name = "claude-3-sonnet"
            evaluation_info.benchmark_name = "GPQA"
            evaluation_info.created_at = datetime.now()
            evaluation_info.completed_at = None
            mock_orchestrator.get_evaluation_info.return_value = evaluation_info

            # Mock get_evaluation_progress for partial results
            from ml_agents_v2.core.application.dto.progress_info import ProgressInfo

            progress_info = Mock(spec=ProgressInfo)
            progress_info.current_question = 89
            progress_info.total_questions = 448
            progress_info.successful_answers = 28
            progress_info.failed_questions = 61
            progress_info.success_rate = 31.46
            mock_orchestrator.get_evaluation_progress.return_value = progress_info

            mock_container_instance = Mock()
            mock_container_instance.evaluation_orchestrator.return_value = (
                mock_orchestrator
            )
            mock_container.return_value = mock_container_instance

            result = runner.invoke(cli, ["evaluate", "show", evaluation_id])

            assert result.exit_code == 0
            assert f"Evaluation Details: {evaluation_id[:8]}" in result.output
            assert "interrupted" in result.output
            assert "89/448" in result.output  # progress
            assert "28" in result.output  # successful answers
            assert "31.46%" in result.output  # current accuracy

    def test_evaluate_show_command_not_found(self):
        """Test evaluate show command when evaluation doesn't exist."""
        runner = CliRunner()

        evaluation_id = str(uuid.uuid4())

        with patch("ml_agents_v2.cli.main.Container") as mock_container:
            mock_orchestrator = Mock()

            # Mock evaluation not found
            from ml_agents_v2.core.domain.repositories.exceptions import (
                EntityNotFoundError,
            )

            mock_orchestrator.get_evaluation_info.side_effect = EntityNotFoundError(
                "Evaluation", evaluation_id
            )

            mock_container_instance = Mock()
            mock_container_instance.evaluation_orchestrator.return_value = (
                mock_orchestrator
            )
            mock_container.return_value = mock_container_instance

            result = runner.invoke(cli, ["evaluate", "show", evaluation_id])

            assert result.exit_code == 1
            assert "✗ Error" in result.output
            assert evaluation_id in result.output

    def test_evaluate_show_command_multiple_matches_for_short_id(self):
        """Test evaluate show command when short ID matches multiple evaluations."""
        runner = CliRunner()

        # Two evaluations with same first 8 characters (unlikely but possible)
        eval1_id = "12345678-1111-1111-1111-111111111111"
        eval2_id = "12345678-2222-2222-2222-222222222222"
        short_id = "12345678"

        with patch("ml_agents_v2.cli.main.Container") as mock_container:
            mock_orchestrator = Mock()

            # Mock list_evaluations to return multiple matches
            from ml_agents_v2.core.application.dto.evaluation_info import EvaluationInfo

            eval1_info = Mock(spec=EvaluationInfo)
            eval1_info.evaluation_id = uuid.UUID(eval1_id)
            eval1_info.status = "completed"

            eval2_info = Mock(spec=EvaluationInfo)
            eval2_info.evaluation_id = uuid.UUID(eval2_id)
            eval2_info.status = "failed"

            mock_orchestrator.list_evaluations.return_value = [eval1_info, eval2_info]

            mock_container_instance = Mock()
            mock_container_instance.evaluation_orchestrator.return_value = (
                mock_orchestrator
            )
            mock_container.return_value = mock_container_instance

            result = runner.invoke(cli, ["evaluate", "show", short_id])

            assert result.exit_code == 1
            assert "✗ Error" in result.output
            assert "Multiple evaluations found" in result.output
            assert "longer ID" in result.output
            assert "completed" in result.output
            assert "failed" in result.output

    def test_evaluate_show_command_pending_evaluation(self):
        """Test evaluate show command displays basic info for pending evaluation."""
        runner = CliRunner()

        evaluation_id = str(uuid.uuid4())

        with patch("ml_agents_v2.cli.main.Container") as mock_container:
            mock_orchestrator = Mock()

            # Mock get_evaluation_info to return pending evaluation
            from ml_agents_v2.core.application.dto.evaluation_info import EvaluationInfo

            evaluation_info = Mock(spec=EvaluationInfo)
            evaluation_info.evaluation_id = uuid.UUID(evaluation_id)
            evaluation_info.status = "pending"
            evaluation_info.agent_type = "chain_of_thought"
            evaluation_info.model_name = "claude-3-sonnet"
            evaluation_info.benchmark_name = "GPQA"
            evaluation_info.created_at = datetime.now()
            evaluation_info.completed_at = None
            mock_orchestrator.get_evaluation_info.return_value = evaluation_info

            mock_container_instance = Mock()
            mock_container_instance.evaluation_orchestrator.return_value = (
                mock_orchestrator
            )
            mock_container.return_value = mock_container_instance

            result = runner.invoke(cli, ["evaluate", "show", evaluation_id])

            assert result.exit_code == 0
            assert f"Evaluation Details: {evaluation_id[:8]}" in result.output
            assert "pending" in result.output
            assert "GPQA" in result.output
            assert "Chain of Thought" in result.output
            assert "claude-3-sonnet" in result.output
            # Should not show progress/accuracy for pending evaluations
            assert "-" in result.output  # placeholder values
