"""Publish command - Trigger export and Cloudflare deploy."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

app = typer.Typer()
console = Console()


@app.command()
def main(
    date: str = typer.Argument(..., help="Date to publish (YYYY-MM-DD)"),
    skip_build: bool = typer.Option(
        False,
        "--skip-build",
        help="Skip site build, deploy only",
    ),
):
    """Trigger export and Cloudflare deployment.

    Builds the static site from exported JSON payloads and deploys to
    Cloudflare Pages. Records deployment metadata in the ledger.

    Examples:

        nh publish 2025-11-14              # Full build and deploy

        nh publish 2025-11-14 --skip-build # Deploy only
    """
    console.print(f"\n[bold]Publish Operation[/bold]")
    console.print(f"Date: {date}")
    if skip_build:
        console.print("Mode: Deploy only (skip build)")
    console.print()

    # TODO: Implement publish logic
    # - Verify export JSON exists
    # - Run site ingestion scripts
    # - Build Astro site
    # - Deploy to Cloudflare via Wrangler
    # - Record deploy metadata in ledger

    console.print("[yellow]Note:[/yellow] Publish command not yet fully implemented")
    console.print("Use './scripts/publish/static_site.sh' as a workaround")
