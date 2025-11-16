"""Publish command - Trigger export and Cloudflare deploy."""

import subprocess
import time
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console

from services.audit import AuditService

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
    # Validate date format
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        console.print(f"[red]Error:[/red] Invalid date format: {date}", style="bold")
        console.print("Expected format: YYYY-MM-DD")
        raise typer.Exit(code=10)

    # Get repo root
    repo_root = Path.cwd().parent if Path.cwd().name == "orchestrator" else Path.cwd()

    # Verify export JSON exists
    export_json = repo_root / "data" / "publishing" / f"{date}.json"
    if not export_json.exists():
        console.print(
            f"[red]Error:[/red] Export JSON not found: {export_json}", style="bold"
        )
        console.print(
            f"\nRun 'nh run --date {date} --wave export' to generate export first"
        )
        raise typer.Exit(code=20)

    # Display header
    console.print(f"\n[bold cyan]NeuroHelix Publish[/bold cyan]")
    console.print(f"Date: {date}")
    if skip_build:
        console.print("Mode: Deploy only (skip build)")
    console.print()

    # Initialize audit service
    audit_service = AuditService(repo_root)

    # Track timing
    started_at = time.time()
    deploy_url = None
    success = False

    try:
        # Run publish script
        publish_script = repo_root / "scripts" / "publish" / "static_site.sh"

        if not publish_script.exists():
            console.print(
                f"[red]Error:[/red] Publish script not found: {publish_script}",
                style="bold",
            )
            raise typer.Exit(code=20)

        console.print(f"[dim]Running: {publish_script}[/dim]\n")

        # Execute script
        result = subprocess.run(
            [str(publish_script)],
            cwd=str(repo_root),
            capture_output=False,
            text=True,
        )

        success = result.returncode == 0

        if success:
            console.print("\n[green]✓[/green] Publish completed successfully")
            # Try to parse deploy URL from logs if available
            log_dir = repo_root / "logs" / "publishing"
            if log_dir.exists():
                latest_log = max(log_dir.glob("publish_*.log"), default=None, key=lambda p: p.stat().st_mtime)
                if latest_log:
                    with open(latest_log) as f:
                        for line in f:
                            if "https://" in line and "pages.dev" in line:
                                # Extract URL from line
                                import re
                                match = re.search(r'https://[^\s]+\.pages\.dev[^\s]*', line)
                                if match:
                                    deploy_url = match.group(0)
                                    break

            if deploy_url:
                console.print(f"Deploy URL: {deploy_url}")

        else:
            console.print(
                f"\n[red]✗[/red] Publish failed with exit code {result.returncode}"
            )

        # Log to audit trail
        duration = time.time() - started_at
        audit_service.log_publish(
            date=date, deploy_url=deploy_url, success=success, duration_seconds=duration
        )

        raise typer.Exit(code=result.returncode)

    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}", style="bold")
        raise typer.Exit(code=10)
