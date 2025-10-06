"""Health command implementation."""

import click
from rich.console import Console
from rich.table import Table

from ml_agents_v2.infrastructure.health_checker import HealthStatus

console = Console()


@click.command()
@click.pass_context
def health(ctx: click.Context) -> None:
    """System health and connectivity check.

    Verifies that all system components are functioning properly:
    - Database connectivity
    - OpenRouter API access and credits
    - Benchmark availability
    """
    try:
        # Get options from context
        verbose = ctx.obj.get("verbose", False)
        quiet = ctx.obj.get("quiet", False)
        container = ctx.obj["container"]

        # Get health checker from container
        health_checker = container.health_checker()

        # Perform health check
        health_status = health_checker.check_health()

        # Display results based on verbosity
        if quiet:
            _display_quiet_health(health_status)
        elif verbose:
            _display_verbose_health(health_status)
        else:
            _display_standard_health(health_status)

        # Exit with appropriate code
        if health_status.status == "unhealthy":
            ctx.exit(1)
        # For healthy/degraded, exit normally (return None for success)

    except click.ClickException:
        # Re-raise click exceptions
        raise
    except Exception as e:
        console.print(f"✗ Health check failed: {str(e)}", style="red")
        ctx.exit(1)


def _display_quiet_health(health_status: HealthStatus) -> None:
    """Display minimal health information."""
    status_icon = _get_status_icon(health_status.status)
    console.print(f"{status_icon} {health_status.status.title()}")


def _display_standard_health(health_status: HealthStatus) -> None:
    """Display standard health information with table."""
    status_icon = _get_status_icon(health_status.status)
    status_color = _get_status_color(health_status.status)

    console.print(
        f"System Health: {status_icon} {health_status.status.title()}",
        style=status_color,
    )

    # Create table for component status
    table = Table(title="Component Status")
    table.add_column("Component", style="cyan", no_wrap=True)
    table.add_column("Status", justify="center")
    table.add_column("Details", style="dim")

    for component, check_data in health_status.checks.items():
        component_icon = _get_status_icon(check_data["status"])
        component_name = component.replace("_", " ").title()
        status_text = f"{component_icon} {check_data['status'].title()}"
        details = check_data.get("details", "")

        # Add credits info for OpenRouter
        if component == "openrouter" and "credits" in check_data:
            credits = check_data["credits"]
            details += f" (${credits:.2f} credits)"

        table.add_row(component_name, status_text, details)

    console.print(table)


def _display_verbose_health(health_status: HealthStatus) -> None:
    """Display detailed health information."""
    status_icon = _get_status_icon(health_status.status)
    status_color = _get_status_color(health_status.status)

    console.print(
        f"System Health: {status_icon} {health_status.status.title()}",
        style=status_color,
    )

    # Create detailed table
    table = Table(title="Detailed Component Status")
    table.add_column("Component", style="cyan", no_wrap=True)
    table.add_column("Status", justify="center")
    table.add_column("Details", style="dim")
    table.add_column("Additional Info", style="dim")

    for component, check_data in health_status.checks.items():
        component_icon = _get_status_icon(check_data["status"])
        component_name = component.replace("_", " ").title()
        status_text = f"{component_icon} {check_data['status'].title()}"
        details = check_data.get("details", "")

        # Gather additional verbose information
        additional_info = []
        for key, value in check_data.items():
            if key not in ["status", "details"]:
                if key == "credits":
                    additional_info.append(f"Credits: ${value:.2f}")
                else:
                    additional_info.append(f"{key.replace('_', ' ').title()}: {value}")

        additional_text = "\n".join(additional_info)
        table.add_row(component_name, status_text, details, additional_text)

    console.print(table)


def _get_status_icon(status: str) -> str:
    """Get icon for status."""
    icons = {"healthy": "✓", "degraded": "⚠", "unhealthy": "✗"}
    return icons.get(status, "?")


def _get_status_color(status: str) -> str:
    """Get color for status."""
    colors = {"healthy": "green", "degraded": "yellow", "unhealthy": "red"}
    return colors.get(status, "white")
