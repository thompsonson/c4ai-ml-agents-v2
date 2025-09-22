"""Benchmark command implementation."""

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ml_agents_v2.core.domain.entities.preprocessed_benchmark import (
    PreprocessedBenchmark,
)

console = Console()


@click.group()
def benchmark() -> None:
    """Benchmark management commands.

    Browse and inspect available preprocessed benchmarks.
    """
    pass


@benchmark.command("list")
@click.pass_context
def list_benchmarks(ctx: click.Context) -> None:
    """List available benchmarks."""
    try:
        # Get options from context
        verbose = ctx.obj.get("verbose", False)
        container = ctx.obj["container"]

        # Get benchmark processor from container
        benchmark_processor = container.benchmark_processor()

        # Get list of benchmarks
        benchmarks = benchmark_processor.list_benchmarks()

        if not benchmarks:
            console.print("No benchmarks available.", style="yellow")
            return

        # Display benchmarks based on verbosity
        if verbose:
            _display_verbose_benchmark_list(benchmarks)
        else:
            _display_standard_benchmark_list(benchmarks)

    except Exception as e:
        console.print(f"✗ Error listing benchmarks: {str(e)}", style="red")
        ctx.exit(1)


@benchmark.command("show")
@click.argument("name")
@click.pass_context
def show_benchmark(ctx: click.Context, name: str) -> None:
    """Show benchmark details."""
    try:
        container = ctx.obj["container"]

        # Get benchmark processor from container
        benchmark_processor = container.benchmark_processor()

        # Get benchmark details
        benchmark = benchmark_processor.get_benchmark_details(name)

        if benchmark is None:
            console.print(f"✗ Benchmark '{name}' not found.", style="red")
            ctx.exit(1)

        # Display detailed benchmark information
        _display_benchmark_details(benchmark)

    except Exception as e:
        console.print(f"✗ Error retrieving benchmark: {str(e)}", style="red")
        ctx.exit(1)


def _display_standard_benchmark_list(benchmarks: list[PreprocessedBenchmark]) -> None:
    """Display standard benchmark list with table."""
    table = Table(title="Available Benchmarks")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Description", style="dim")
    table.add_column("Questions", justify="right", style="green")

    for benchmark in benchmarks:
        table.add_row(
            benchmark.name, benchmark.description, str(benchmark.question_count)
        )

    console.print(table)


def _display_verbose_benchmark_list(benchmarks: list[PreprocessedBenchmark]) -> None:
    """Display detailed benchmark list with metadata."""
    table = Table(title="Available Benchmarks (Verbose)")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Description", style="dim")
    table.add_column("Questions", justify="right", style="green")
    table.add_column("Metadata", style="dim")

    for benchmark in benchmarks:
        # Format metadata for display
        metadata_items = []
        for key, value in benchmark.metadata.items():
            metadata_items.append(f"{key}: {value}")
        metadata_text = "\n".join(metadata_items) if metadata_items else "None"

        # Show question count with verbose format
        question_text = f"{benchmark.question_count} questions"

        table.add_row(
            benchmark.name, benchmark.description, question_text, metadata_text
        )

    console.print(table)


def _display_benchmark_details(benchmark: PreprocessedBenchmark) -> None:
    """Display detailed information about a specific benchmark."""
    # Main information panel
    info_content = f"""
[bold]{benchmark.name}[/bold]

[dim]Description:[/dim]
{benchmark.description}

[dim]Statistics:[/dim]
• Questions: {benchmark.question_count}
• Format Version: {benchmark.format_version}
• Created: {benchmark.created_at.strftime('%Y-%m-%d %H:%M:%S')}
"""

    console.print(
        Panel(info_content.strip(), title="Benchmark Details", border_style="blue")
    )

    # Metadata section
    if benchmark.metadata:
        metadata_table = Table(title="Metadata")
        metadata_table.add_column("Property", style="cyan")
        metadata_table.add_column("Value", style="dim")

        for key, value in benchmark.metadata.items():
            metadata_table.add_row(key, str(value))

        console.print(metadata_table)

    # Sample questions (first few)
    questions = benchmark.get_questions()
    if questions:
        sample_size = min(3, len(questions))
        sample_table = Table(
            title=f"Sample Questions (showing {sample_size} of {len(questions)})"
        )
        sample_table.add_column("ID", style="cyan", no_wrap=True)
        sample_table.add_column("Question", style="dim")
        sample_table.add_column("Expected Answer", style="green")

        for question in questions[:sample_size]:
            # Truncate long questions for display
            question_text = question.text
            if len(question_text) > 80:
                question_text = question_text[:77] + "..."

            expected_answer = question.expected_answer
            if len(expected_answer) > 30:
                expected_answer = expected_answer[:27] + "..."

            sample_table.add_row(question.id, question_text, expected_answer)

        console.print(sample_table)

        if len(questions) > sample_size:
            console.print(
                f"[dim]... and {len(questions) - sample_size} more questions[/dim]"
            )
