"""Evaluate command implementation."""

import asyncio
import uuid
from datetime import datetime
from typing import Any

import click
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

from ml_agents_v2.core.domain.value_objects.agent_config import AgentConfig

console = Console()


def _map_agent_type(cli_agent_type: str) -> str:
    """Map CLI agent type to domain agent type."""
    mapping = {"none": "none", "cot": "chain_of_thought"}
    return mapping.get(cli_agent_type, cli_agent_type)


def _parse_model_string(model: str) -> tuple[str, str]:
    """Parse model string into provider and name."""
    if "/" in model:
        provider, name = model.split("/", 1)
        return provider, name
    else:
        # Default to anthropic if no provider specified
        return "anthropic", model


@click.group()
def evaluate() -> None:
    """Evaluation management commands.

    Create, run, and list AI reasoning evaluations against benchmarks.
    """
    pass


@evaluate.command()
@click.option(
    "--agent",
    type=click.Choice(["none", "cot"]),
    required=True,
    help="Reasoning approach: 'none' for direct prompting, 'cot' for Chain of Thought",
)
@click.option(
    "--model", required=True, help="Model identifier (e.g., anthropic/claude-3-sonnet)"
)
@click.option(
    "--benchmark", required=True, help="Benchmark short name (e.g., GPQA, FOLIO)"
)
@click.option(
    "--temp",
    type=float,
    default=1.0,
    help="Temperature for model (0.0-2.0, default: 1.0)",
)
@click.option(
    "--max-tokens", type=int, default=1000, help="Maximum output tokens (default: 1000)"
)
@click.pass_context
def create(
    ctx: click.Context,
    agent: str,
    model: str,
    benchmark: str,
    temp: float,
    max_tokens: int,
) -> None:
    """Create new evaluation configuration."""
    try:
        container = ctx.obj["container"]
        orchestrator = container.evaluation_orchestrator()

        # Parse model into provider and name
        model_provider, model_name = _parse_model_string(model)

        # Map CLI agent type to domain agent type
        domain_agent_type = _map_agent_type(agent)

        # Create AgentConfig
        agent_config = AgentConfig(
            agent_type=domain_agent_type,
            model_provider=model_provider,
            model_name=model_name,
            model_parameters={"temperature": temp, "max_tokens": max_tokens},
            agent_parameters={},
        )

        # Create evaluation
        evaluation = orchestrator.create_evaluation(
            agent_config=agent_config, benchmark_name=benchmark
        )

        # Display success message
        short_id = str(evaluation)[:8]
        agent_display = "Chain of Thought" if agent == "cot" else "Direct prompting"

        console.print(f"✓ Created evaluation {short_id} (pending)", style="green")
        console.print(f"  Agent: {agent_display}")
        console.print(f"  Model: {model}")
        console.print(f"  Benchmark: {benchmark}")
        console.print(f"  Run with: ml-agents evaluate run {short_id}")

    except ValueError as e:
        error_msg = str(e)
        console.print(f"✗ Error: {error_msg}", style="red")

        if "not found" in error_msg.lower():
            if "benchmark" in error_msg.lower():
                console.print(
                    "  Use 'ml-agents benchmark list' to see available benchmarks",
                    style="dim",
                )
            ctx.exit(1)
        else:
            ctx.exit(1)
    except Exception as e:
        console.print(f"✗ Error creating evaluation: {str(e)}", style="red")
        ctx.exit(1)


@evaluate.command()
@click.argument("evaluation_id")
@click.pass_context
def run(ctx: click.Context, evaluation_id: str) -> None:
    """Execute evaluation with real-time progress."""
    try:
        container = ctx.obj["container"]
        orchestrator = container.evaluation_orchestrator()

        # Convert string to UUID if needed
        try:
            eval_uuid = uuid.UUID(evaluation_id)
        except ValueError:
            # Try to find by short ID (first 8 characters)
            # Get all evaluations and find one that starts with the provided ID
            all_evaluations = orchestrator.list_evaluations()
            matching_evaluations = [
                eval_info
                for eval_info in all_evaluations
                if str(eval_info.evaluation_id).startswith(evaluation_id)
            ]

            if len(matching_evaluations) == 0:
                console.print(
                    f"✗ Error: No evaluation found with ID starting with '{evaluation_id}'",
                    style="red",
                )
                ctx.exit(1)
            elif len(matching_evaluations) > 1:
                console.print(
                    f"✗ Error: Multiple evaluations found with ID starting with '{evaluation_id}'. Please use a longer ID.",
                    style="red",
                )
                console.print("Matching evaluations:")
                for eval_info in matching_evaluations:
                    console.print(
                        f"  {str(eval_info.evaluation_id)[:8]} - {eval_info.status}"
                    )
                ctx.exit(1)
            else:
                eval_uuid = matching_evaluations[0].evaluation_id

        short_id = str(eval_uuid)[:8]

        # Check evaluation status for resume capability (Phase 8)
        evaluation_info = orchestrator.get_evaluation_info(eval_uuid)

        if evaluation_info.status == "interrupted":
            console.print(
                f"📋 Resuming interrupted evaluation {short_id}...", style="yellow"
            )
            # Get current progress
            progress_info = orchestrator.get_evaluation_progress(eval_uuid)
            console.print(
                f"   Already completed: {progress_info.current_question}/{progress_info.total_questions} questions"
            )
            console.print(f"   Success rate so far: {progress_info.success_rate:.1f}%")
        elif evaluation_info.status == "completed":
            console.print(f"✓ Evaluation {short_id} already completed", style="green")
            return
        elif evaluation_info.status == "failed":
            console.print(f"✗ Evaluation {short_id} previously failed", style="red")
            return
        else:
            console.print(f"🚀 Starting evaluation {short_id}...")

        # Execute evaluation with enhanced progress tracking (Phase 8)
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("({task.completed}/{task.total})"),
            TextColumn("Success: {task.fields[success_rate]:.1f}%"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:

            initial_progress = orchestrator.get_evaluation_progress(eval_uuid)
            total_questions = initial_progress.total_questions

            task = progress.add_task(
                "Executing evaluation...",
                total=total_questions,
                completed=initial_progress.current_question,
                success_rate=initial_progress.success_rate,
            )

            # Enhanced progress callback (Phase 8)
            def progress_callback(progress_info: Any) -> None:
                progress.update(
                    task,
                    completed=progress_info.current_question,
                    description=f"Processing questions ({progress_info.successful_answers} successful, {progress_info.failed_questions} failed)",
                    success_rate=progress_info.success_rate,
                )

            try:
                # Execute the evaluation with interruption handling
                asyncio.run(
                    orchestrator.execute_evaluation(
                        evaluation_id=eval_uuid, progress_callback=progress_callback
                    )
                )
            except KeyboardInterrupt:
                console.print("\n⏸️  Evaluation interrupted by user", style="yellow")
                console.print(
                    "   Progress has been saved. Use the same command to resume.",
                    style="dim",
                )
                ctx.exit(0)

        console.print("✓ Completed evaluation", style="green")

    except ValueError as e:
        error_msg = str(e)
        console.print(f"✗ Error: {error_msg}", style="red")
        ctx.exit(1)
    except Exception as e:
        console.print(f"✗ Error running evaluation: {str(e)}", style="red")
        ctx.exit(1)


@evaluate.command("list")
@click.option(
    "--status",
    type=click.Choice(["pending", "running", "completed", "failed", "interrupted"]),
    help="Filter by evaluation status",
)
@click.option("--benchmark", help="Filter by benchmark name")
@click.pass_context
def list_evaluations(ctx: click.Context, status: str, benchmark: str) -> None:
    """List evaluations with optional filtering."""
    try:
        container = ctx.obj["container"]
        orchestrator = container.evaluation_orchestrator()

        # Get evaluations with filters
        evaluations = orchestrator.list_evaluations(
            status_filter=status, benchmark_name_filter=benchmark
        )

        if not evaluations:
            console.print("No evaluations found.", style="yellow")
            return

        # Create table with Phase 8 progress column
        table = Table(title="Evaluations")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Status", justify="center")
        table.add_column("Agent", style="dim")
        table.add_column("Model", style="dim")
        table.add_column("Benchmark", style="bold")
        table.add_column("Progress", justify="center", style="blue")
        table.add_column("Accuracy", justify="right", style="green")
        table.add_column("Failures", justify="right", style="red")
        table.add_column("Created", style="dim")

        for evaluation in evaluations:
            # Format short ID
            short_id = str(evaluation.evaluation_id)[:8]

            # Format status with color
            status_text = evaluation.status
            status_style = {
                "completed": "green",
                "failed": "red",
                "running": "yellow",
                "pending": "blue",
                "interrupted": "orange1",
            }.get(status_text, "white")

            # Format agent type
            agent_display = {"chain_of_thought": "cot", "none": "none"}.get(
                evaluation.agent_type, evaluation.agent_type
            )

            # Phase 8: Enhanced progress and accuracy display
            progress_text = "-"
            accuracy_text = "-"
            failures_text = "-"

            try:
                if evaluation.status in ["completed", "interrupted", "running"]:
                    # Get computed results from question results for any evaluation with progress
                    if evaluation.status == "completed":
                        # For completed evaluations, get full results
                        results = orchestrator.get_evaluation_results(
                            evaluation.evaluation_id
                        )
                        accuracy_text = f"{results.accuracy:.1f}%"
                        progress_text = (
                            f"{results.total_questions}/{results.total_questions}"
                        )
                        failure_rate = (
                            (results.error_count / results.total_questions) * 100
                            if results.total_questions > 0
                            else 0
                        )
                        failures_text = f"{failure_rate:.1f}%"
                    else:
                        # For interrupted/running evaluations, get current progress
                        progress_info = orchestrator.get_evaluation_progress(
                            evaluation.evaluation_id
                        )
                        progress_text = f"{progress_info.current_question}/{progress_info.total_questions}"
                        if progress_info.current_question > 0:
                            accuracy_text = f"{progress_info.success_rate:.1f}%"
                        failure_rate = (
                            (
                                progress_info.failed_questions
                                / progress_info.total_questions
                            )
                            * 100
                            if progress_info.total_questions > 0
                            else 0
                        )
                        failures_text = f"{failure_rate:.1f}%"
                elif evaluation.accuracy is not None:
                    # Fallback to stored accuracy for backwards compatibility
                    accuracy_text = f"{evaluation.accuracy:.1f}%"
            except Exception:
                # If we can't get progress/results, use stored values
                if evaluation.accuracy is not None:
                    accuracy_text = f"{evaluation.accuracy:.1f}%"

            # Format created time (relative)
            created_at = evaluation.created_at
            time_diff = (datetime.now() - created_at).total_seconds()
            if time_diff < 3600:  # Less than 1 hour
                time_text = f"{int(time_diff / 60)} min ago"
            elif time_diff < 86400:  # Less than 1 day
                time_text = f"{int(time_diff / 3600)} hours ago"
            else:
                time_text = f"{int(time_diff / 86400)} days ago"

            table.add_row(
                short_id,
                f"[{status_style}]{status_text}[/{status_style}]",
                agent_display,
                evaluation.model_name,
                evaluation.benchmark_name,
                progress_text,
                accuracy_text,
                failures_text,
                time_text,
            )

        console.print(table)

    except Exception as e:
        console.print(f"✗ Error listing evaluations: {str(e)}", style="red")
        ctx.exit(1)


@evaluate.command()
@click.argument("evaluation_id")
@click.pass_context
def show(ctx: click.Context, evaluation_id: str) -> None:
    """Show detailed evaluation results and information."""
    try:
        container = ctx.obj["container"]
        orchestrator = container.evaluation_orchestrator()

        # Convert string to UUID if needed (same logic as run command)
        try:
            eval_uuid = uuid.UUID(evaluation_id)
        except ValueError:
            # Try to find by short ID (first 8 characters)
            all_evaluations = orchestrator.list_evaluations()
            matching_evaluations = [
                eval_info
                for eval_info in all_evaluations
                if str(eval_info.evaluation_id).startswith(evaluation_id)
            ]

            if len(matching_evaluations) == 0:
                console.print(
                    f"✗ Error: No evaluation found with ID starting with '{evaluation_id}'",
                    style="red",
                )
                ctx.exit(1)
            elif len(matching_evaluations) > 1:
                console.print(
                    f"✗ Error: Multiple evaluations found with ID starting with '{evaluation_id}'. Please use a longer ID.",
                    style="red",
                )
                console.print("Matching evaluations:")
                for eval_info in matching_evaluations:
                    console.print(
                        f"  {str(eval_info.evaluation_id)[:8]} - {eval_info.status}"
                    )
                ctx.exit(1)
            else:
                eval_uuid = matching_evaluations[0].evaluation_id

        short_id = str(eval_uuid)[:8]

        # Get basic evaluation information
        evaluation_info = orchestrator.get_evaluation_info(eval_uuid)

        # Create table for detailed view
        table = Table(title=f"Evaluation Details: {short_id}")
        table.add_column("Field", style="cyan", width=20)
        table.add_column("Value", style="white")

        # Add basic information
        table.add_row("Status", evaluation_info.status)
        table.add_row("Benchmark", evaluation_info.benchmark_name)

        # Format agent type display
        agent_display = {
            "chain_of_thought": "Chain of Thought",
            "none": "Direct prompting",
        }.get(evaluation_info.agent_type, evaluation_info.agent_type)
        table.add_row("Agent Type", agent_display)
        table.add_row("Model", evaluation_info.model_name)

        # Add detailed results based on status
        if evaluation_info.status == "completed":
            try:
                # Get detailed results for completed evaluations
                results = orchestrator.get_evaluation_results(eval_uuid)
                table.add_row("Total Questions", str(results.total_questions))
                table.add_row("Correct Answers", str(results.correct_answers))
                table.add_row("Accuracy", f"{results.accuracy:.2f}%")
                table.add_row(
                    "Avg Execution Time", f"{results.average_time_per_question:.2f}s"
                )
                table.add_row("Error Count", str(results.error_count))

                # Format execution time
                if results.execution_time_minutes >= 1:
                    time_text = f"{results.execution_time_minutes:.1f}m"
                else:
                    time_text = f"{results.execution_time_minutes * 60:.1f}s"
                table.add_row("Total Time", time_text)

            except Exception:
                # Fallback if detailed results not available
                table.add_row("Total Questions", "-")
                table.add_row("Correct Answers", "-")
                table.add_row("Accuracy", "-")
                table.add_row("Avg Execution Time", "-")
                table.add_row("Error Count", "-")
                table.add_row("Total Time", "-")

        elif evaluation_info.status in ["interrupted", "running"]:
            try:
                # Get progress for interrupted/running evaluations
                progress_info = orchestrator.get_evaluation_progress(eval_uuid)
                table.add_row(
                    "Progress",
                    f"{progress_info.current_question}/{progress_info.total_questions}",
                )
                table.add_row("Correct Answers", str(progress_info.successful_answers))
                if progress_info.current_question > 0:
                    table.add_row(
                        "Current Accuracy", f"{progress_info.success_rate:.2f}%"
                    )
                else:
                    table.add_row("Current Accuracy", "-")
                table.add_row("Failed Questions", str(progress_info.failed_questions))

            except Exception:
                # Fallback if progress not available
                table.add_row("Progress", "-")
                table.add_row("Correct Answers", "-")
                table.add_row("Current Accuracy", "-")
                table.add_row("Failed Questions", "-")
        else:
            # Pending or failed evaluations
            table.add_row("Total Questions", "-")
            table.add_row("Correct Answers", "-")
            table.add_row("Accuracy", "-")
            table.add_row("Progress", "-")

        # Add timestamps
        created_at = evaluation_info.created_at
        time_diff = (datetime.now() - created_at).total_seconds()
        if time_diff < 3600:  # Less than 1 hour
            created_text = f"{int(time_diff / 60)} minutes ago"
        elif time_diff < 86400:  # Less than 1 day
            created_text = f"{int(time_diff / 3600)} hours ago"
        else:
            created_text = f"{int(time_diff / 86400)} days ago"

        table.add_row("Created", created_text)

        if evaluation_info.completed_at:
            completed_diff = (
                datetime.now() - evaluation_info.completed_at
            ).total_seconds()
            if completed_diff < 3600:  # Less than 1 hour
                completed_text = f"{int(completed_diff / 60)} minutes ago"
            elif completed_diff < 86400:  # Less than 1 day
                completed_text = f"{int(completed_diff / 3600)} hours ago"
            else:
                completed_text = f"{int(completed_diff / 86400)} days ago"
            table.add_row("Completed", completed_text)
        else:
            table.add_row("Completed", "-")

        console.print(table)

    except ValueError as e:
        error_msg = str(e)
        console.print(f"✗ Error: {error_msg}", style="red")
        ctx.exit(1)
    except Exception as e:
        console.print(f"✗ Error showing evaluation: {str(e)}", style="red")
        ctx.exit(1)


@evaluate.command()
@click.argument("evaluation_id")
@click.option(
    "--format",
    type=click.Choice(["csv"]),
    default="csv",
    help="Export format (default: csv)",
)
@click.option(
    "--output",
    required=True,
    help="Output file path for the exported data",
)
@click.pass_context
def export(ctx: click.Context, evaluation_id: str, format: str, output: str) -> None:
    """Export evaluation results to file.

    Export question-level results for the specified evaluation to a file
    in the requested format. Includes question text, expected/actual answers,
    correctness, timing, and error information.
    """
    try:
        container = ctx.obj["container"]
        orchestrator = container.evaluation_orchestrator()

        # Convert string to UUID if needed (same logic as run/show commands)
        try:
            eval_uuid = uuid.UUID(evaluation_id)
        except ValueError:
            # Try to find by short ID (first 8 characters)
            all_evaluations = orchestrator.list_evaluations()
            matching_evaluations = [
                eval_info
                for eval_info in all_evaluations
                if str(eval_info.evaluation_id).startswith(evaluation_id)
            ]

            if len(matching_evaluations) == 0:
                console.print(
                    f"✗ Error: No evaluation found with ID starting with '{evaluation_id}'",
                    style="red",
                )
                ctx.exit(1)
            elif len(matching_evaluations) > 1:
                console.print(
                    f"✗ Error: Multiple evaluations found with ID starting with '{evaluation_id}'. Please use a longer ID.",
                    style="red",
                )
                console.print("Matching evaluations:")
                for eval_info in matching_evaluations:
                    console.print(
                        f"  {str(eval_info.evaluation_id)[:8]} - {eval_info.status}"
                    )
                ctx.exit(1)
            else:
                eval_uuid = matching_evaluations[0].evaluation_id

        short_id = str(eval_uuid)[:8]

        # Execute export
        console.print(f"🔄 Exporting evaluation {short_id} to {format.upper()}...")

        orchestrator.export_evaluation_results(
            evaluation_id=eval_uuid, export_format=format, output_path=output
        )

        console.print(f"✓ Exported evaluation {short_id} to {output}", style="green")
        console.print(f"  Format: {format.upper()}")
        console.print(f"  File: {output}")

    except ValueError as e:
        error_msg = str(e)
        console.print(f"✗ Error: {error_msg}", style="red")
        ctx.exit(1)
    except Exception as e:
        console.print(f"✗ Error exporting evaluation: {str(e)}", style="red")
        ctx.exit(1)
