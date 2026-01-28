"""
Command-line interface for Lead-Gen.

Provides commands for:
- Running workflows
- Validating configuration
- Checking environment
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

console = Console()


@click.group()
@click.version_option(package_name="lead-gen")
def main() -> None:
    """
    Lead-Gen: Enterprise-grade lead generation platform.

    Generate personalized outreach for businesses using AI.
    """
    pass


@main.command()
@click.argument("workflow_path", type=click.Path(exists=True))
@click.option("--dry-run", is_flag=True, help="Validate without executing")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed output")
def run(workflow_path: str, dry_run: bool, verbose: bool) -> None:
    """
    Run a workflow from YAML configuration.

    WORKFLOW_PATH: Path to the workflow YAML file.
    """
    asyncio.run(_run_workflow(workflow_path, dry_run, verbose))


async def _run_workflow(workflow_path: str, dry_run: bool, verbose: bool) -> None:
    """Async workflow runner."""
    from lead_gen.models.workflow import WorkflowConfig
    from lead_gen.tools.base import ToolContext
    from lead_gen.workflows.base import WorkflowRunner

    console.print(Panel.fit(
        f"[bold blue]Lead-Gen Workflow Runner[/bold blue]\n"
        f"Workflow: {workflow_path}",
        border_style="blue",
    ))

    try:
        # Load configuration
        config = WorkflowConfig.from_yaml(workflow_path)

        # Validate
        errors = config.validate_workflow()
        if errors:
            console.print("[red]Configuration errors:[/red]")
            for error in errors:
                console.print(f"  - {error}")
            sys.exit(1)

        # Show workflow info
        table = Table(title="Workflow Configuration")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Name", config.name)
        table.add_row("Description", config.description or "-")
        table.add_row("Steps", str(config.total_steps))
        table.add_row("Dry Run", str(dry_run))

        console.print(table)
        console.print()

        # Show steps
        steps_table = Table(title="Workflow Steps")
        steps_table.add_column("#", style="dim")
        steps_table.add_column("Name", style="cyan")
        steps_table.add_column("Type", style="yellow")
        steps_table.add_column("Enabled", style="green")

        for i, step in enumerate(config.steps, 1):
            steps_table.add_row(
                str(i),
                step.name,
                step.type.value,
                "Yes" if step.enabled else "No",
            )

        console.print(steps_table)
        console.print()

        if dry_run:
            console.print("[yellow]Dry run mode - no actual execution[/yellow]")
            return

        # Run workflow
        context = ToolContext(dry_run=dry_run)
        runner = WorkflowRunner()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Running workflow...", total=None)

            result = await runner.run(config, context)

            progress.update(task, description="[green]Completed!")

        # Show results
        console.print()
        results_table = Table(title="Execution Results")
        results_table.add_column("Metric", style="cyan")
        results_table.add_column("Value", style="green")

        results_table.add_row("Status", result.status.value)
        results_table.add_row("Leads Processed", str(result.total_leads_processed))
        results_table.add_row("Steps Completed", f"{result.completed_steps}/{result.total_steps}")
        results_table.add_row("API Calls", str(context.api_calls))
        results_table.add_row("Tokens Used", str(context.tokens_used))
        results_table.add_row("Cost (USD)", f"${context.cost_usd:.4f}")
        results_table.add_row("Duration", f"{context.elapsed_seconds:.2f}s")

        console.print(results_table)

        if result.error_message:
            console.print(f"\n[red]Error: {result.error_message}[/red]")
            sys.exit(1)

    except FileNotFoundError:
        console.print(f"[red]Workflow file not found: {workflow_path}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        if verbose:
            console.print_exception()
        sys.exit(1)


@main.command()
def validate_env() -> None:
    """Validate environment configuration and API keys."""
    from lead_gen.core.config import get_settings

    console.print(Panel.fit(
        "[bold blue]Environment Validation[/bold blue]",
        border_style="blue",
    ))

    try:
        settings = get_settings()

        table = Table(title="Configuration Status")
        table.add_column("Setting", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Value", style="dim")

        # Environment
        table.add_row(
            "Environment",
            "[green]OK[/green]",
            settings.environment.value,
        )

        # API Keys
        missing_keys = settings.validate_required_keys(require_hunter=False)

        # Google Places
        has_places = "GOOGLE_PLACES_API_KEY" not in missing_keys
        table.add_row(
            "Google Places API",
            "[green]OK[/green]" if has_places else "[red]Missing[/red]",
            "***" if has_places else "-",
        )

        # OpenAI
        has_openai = "OPENAI_API_KEY" not in missing_keys
        table.add_row(
            "OpenAI API",
            "[green]OK[/green]" if has_openai else "[red]Missing[/red]",
            "***" if has_openai else "-",
        )

        # Google Service Account
        has_sa = not any("GOOGLE_SERVICE_ACCOUNT" in k for k in missing_keys)
        table.add_row(
            "Google Service Account",
            "[green]OK[/green]" if has_sa else "[red]Missing[/red]",
            str(settings.google_service_account_path) if has_sa else "-",
        )

        # Hunter (optional)
        has_hunter = bool(settings.hunter_api_key.get_secret_value())
        table.add_row(
            "Hunter.io API (optional)",
            "[green]OK[/green]" if has_hunter else "[yellow]Not configured[/yellow]",
            "***" if has_hunter else "-",
        )

        console.print(table)

        # Settings
        settings_table = Table(title="Settings")
        settings_table.add_column("Setting", style="cyan")
        settings_table.add_column("Value", style="green")

        settings_table.add_row("Log Level", settings.log_level.value)
        settings_table.add_row("Secret Backend", settings.secret_backend.value)
        settings_table.add_row("GDPR Retention Days", str(settings.gdpr.retention_days))
        settings_table.add_row("Rate Limit (Places)", f"{settings.rate_limits.google_places}/min")
        settings_table.add_row("Rate Limit (OpenAI)", f"{settings.rate_limits.openai}/min")
        settings_table.add_row("OpenAI Model", settings.openai.model)

        console.print(settings_table)

        if missing_keys:
            console.print(f"\n[yellow]Missing required keys: {', '.join(missing_keys)}[/yellow]")
            console.print("See .env.example for configuration instructions.")
            sys.exit(1)
        else:
            console.print("\n[green]All required configuration is present![/green]")

    except Exception as e:
        console.print(f"[red]Error loading configuration: {e}[/red]")
        sys.exit(1)


@main.command()
@click.argument("output_path", type=click.Path(), default="workflow.yaml")
def init(output_path: str) -> None:
    """Create a new workflow configuration file."""
    from lead_gen.models.workflow import EXAMPLE_WORKFLOW_YAML

    path = Path(output_path)

    if path.exists():
        if not click.confirm(f"{output_path} already exists. Overwrite?"):
            console.print("[yellow]Cancelled.[/yellow]")
            return

    path.write_text(EXAMPLE_WORKFLOW_YAML)
    console.print(f"[green]Created workflow configuration: {output_path}[/green]")
    console.print("\nNext steps:")
    console.print("1. Edit the workflow file with your settings")
    console.print("2. Set up your API keys in .env")
    console.print("3. Run: lead-gen run workflow.yaml")


@main.command()
def version() -> None:
    """Show version information."""
    from lead_gen import __version__

    console.print(f"Lead-Gen version: {__version__}")


if __name__ == "__main__":
    main()
