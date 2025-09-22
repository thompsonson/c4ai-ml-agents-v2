"""Main CLI entry point for ML Agents v2."""

import click
from rich.console import Console

from ml_agents_v2.infrastructure.container import Container

from .commands.benchmark import benchmark as benchmark_commands
from .commands.evaluate import evaluate as evaluate_commands
from .commands.health import health as health_command

console = Console()


@click.group()
@click.version_option(version="0.1.0", prog_name="ml-agents")
@click.option("--verbose", is_flag=True, help="Enable verbose output")
@click.option("--quiet", is_flag=True, help="Suppress non-essential output")
@click.pass_context
def cli(ctx: click.Context, verbose: bool, quiet: bool) -> None:
    """ML Agents v2 - Reasoning research platform.

    A CLI tool for evaluating different AI reasoning approaches across
    various benchmarks. Supports Chain of Thought, direct prompting,
    and future reasoning methodologies.
    """
    # Ensure context object exists and initialize container
    ctx.ensure_object(dict)

    # Create and wire dependency injection container
    container = Container()
    container.wire(modules=[__name__])

    # Store container and options in context
    ctx.obj["container"] = container
    ctx.obj["verbose"] = verbose
    ctx.obj["quiet"] = quiet


# Remove stub evaluate commands - they're now imported


# Add imported commands to CLI
cli.add_command(benchmark_commands, name="benchmark")
cli.add_command(evaluate_commands, name="evaluate")
cli.add_command(health_command, name="health")


if __name__ == "__main__":
    cli()
