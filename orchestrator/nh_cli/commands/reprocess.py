"""Reprocess command - Rebuild artifacts for a past day."""

import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from config.toml_config import ConfigLoader
from services.audit import AuditService
from services.git_safety import GitDirtyError, ensure_clean_repo, get_git_status

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
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview actions without executing",
    ),
    allow_dirty: bool = typer.Option(
        False,
        "--allow-dirty",
        help="Allow reprocess even if git working tree is dirty",
    ),
):
    """Rebuild artifacts for a past day.

    Validates that the date has existing data and safely reruns selected
    prompts or waves with proper dependency tracking.

    Examples:

        nh reprocess 2025-11-14                # Reprocess all waves

        nh reprocess 2025-11-14 --force search # Force rerun search wave

        nh reprocess 2025-11-14 --dry-run      # Preview what would be rerun
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

    orchestrator_root = repo_root / "orchestrator" if repo_root.name != "orchestrator" else repo_root
    config_loader = ConfigLoader(orchestrator_root)
    config = config_loader.load()

    require_clean = config.maintenance.require_clean_git
    try:
        ensure_clean_repo(repo_root, allow_dirty or not require_clean)
    except GitDirtyError as err:
        status = get_git_status(repo_root)
        console.print(f"[red]Error:[/red] {err}", style="bold")
        if status.dirty_files:
            console.print("\nDirty files:")
            for line in status.dirty_files:
                console.print(f"  {line}")
        raise typer.Exit(code=10)

    # Check if date has existing data
    outputs_dir = repo_root / "data" / "outputs" / "daily" / date
    manifest_path = repo_root / "data" / "manifests" / f"{date}.json"

    if not outputs_dir.exists() and not manifest_path.exists():
        console.print(
            f"[red]Error:[/red] No existing data found for {date}", style="bold"
        )
        console.print(f"  Outputs directory: {outputs_dir} (not found)")
        console.print(f"  Manifest: {manifest_path} (not found)")
        console.print("\nUse 'nh run --date {date}' to create initial run")
        raise typer.Exit(code=20)

    # Display header
    console.print(f"\n[bold cyan]NeuroHelix Reprocess[/bold cyan]")
    console.print(f"Date: {date}")
    if force:
        console.print(f"Force: {force}")
    if dry_run:
        console.print("[yellow]Mode: DRY RUN[/yellow]")
    console.print()

    # Build command to delegate to 'nh run'
    cmd = ["nh", "run", "--date", date]

    if force:
        cmd.extend(["--force", force])

    if dry_run:
        cmd.append("--dry-run")

    # Show command
    console.print(f"[dim]Delegating to: {' '.join(cmd)}[/dim]\n")

    # Execute via nh run
    try:
        result = subprocess.run(cmd, check=False)

        # Log to audit trail (only if not dry run)
        if not dry_run and result.returncode == 0:
            audit_service = AuditService(repo_root)
            forced_items = [force] if force else []
            # We don't know which files were regenerated without reading ledger
            # So we just log that reprocess was successful
            audit_service.log_reprocess(
                date=date,
                forced_items=forced_items,
                regenerated_files=[],  # Would need to parse ledger to get this
                dry_run=dry_run,
            )

        raise typer.Exit(code=result.returncode)

    except FileNotFoundError:
        console.print("[red]Error:[/red] 'nh' command not found", style="bold")
        console.print("Make sure you're running from within the virtual environment")
        raise typer.Exit(code=10)
