"""Reprocess command - Rebuild artifacts for a past day."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

app = typer.Typer()
console = Console()


@app.command()
def main(
    date: str = typer.Argument(..., help="Date to reprocess (YYYY-MM-DD)"),
    force: Optional[str] = typer.Option(
        None,
        "--force",
        "-f",
        help="Force rerun of specific wave or prompt",
    ),
):
    """Rebuild artifacts for a past day.

    Validates that the date has a manifest and safely reruns selected
    prompts or waves with proper dependency tracking.

    Examples:

        nh reprocess 2025-11-14                # Reprocess all waves

        nh reprocess 2025-11-14 --force search # Force rerun search wave
    """
    console.print(f"\n[bold]Reprocess Operation[/bold]")
    console.print(f"Date: {date}")
    if force:
        console.print(f"Force: {force}")
    console.print()

    # TODO: Implement reprocess logic
    # - Load manifest for the date
    # - Determine which prompts to rerun based on --force
    # - Execute with proper dependency tracking
    # - Update manifest and ledger

    console.print("[yellow]Note:[/yellow] Reprocess command not yet fully implemented")
    console.print("Use 'nh run --date {date} --force {target}' as a workaround")
