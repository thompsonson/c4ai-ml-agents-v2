"""Benchmark command implementation."""

from typing import Any

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
        benchmarks = benchmark_processor.list_available_benchmarks()

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


@benchmark.command("import")
@click.argument("csv_path", type=click.Path(exists=True, dir_okay=False, readable=True))
@click.option("--name", help="Benchmark name (defaults to filename)")
@click.option("--description", help="Benchmark description")
@click.pass_context
def import_benchmark(
    ctx: click.Context, csv_path: str, name: str, description: str
) -> None:
    """Import benchmark from CSV file with INPUT,OUTPUT columns."""
    try:
        container = ctx.obj["container"]
        benchmark_processor = container.benchmark_processor()

        # Import benchmark from CSV
        console.print(f"📥 Importing benchmark from {csv_path}...", style="blue")

        benchmark_info = benchmark_processor.import_benchmark_from_csv(
            csv_file_path=csv_path, benchmark_name=name, description=description
        )

        console.print(
            f"✅ Successfully imported benchmark '{benchmark_info.name}' "
            f"with {benchmark_info.question_count} questions",
            style="green",
        )

        # Display summary
        table = Table(title="Imported Benchmark Summary")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Name", benchmark_info.name)
        table.add_row("Description", benchmark_info.description)
        table.add_row("Questions", str(benchmark_info.question_count))
        table.add_row("Format Version", benchmark_info.format_version)

        console.print(table)

    except Exception as e:
        console.print(f"✗ Error importing benchmark: {str(e)}", style="red")
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


def _display_benchmark_details(benchmark: Any) -> None:
    """Display detailed information about a specific benchmark (BenchmarkInfo DTO)."""
    # Main information panel
    info_content = f"""
[bold]{benchmark.name}[/bold]

Description:
{benchmark.description}

Statistics:
• Questions: {benchmark.question_count}
• Format Version: {benchmark.format_version}
• Created: {benchmark.created_at.strftime('%Y-%m-%d %H:%M:%S')}
"""

    console.print(
        Panel(info_content.strip(), title="Benchmark Details", border_style="blue")
    )

    # For BenchmarkInfo, we don't have access to full metadata or questions
    # This is expected - BenchmarkInfo is a summary DTO
    console.print(
        "[dim]💡 Use 'ml-agents evaluate create' to run evaluations with this benchmark[/dim]"
    )
