"""Reprocess command - Rebuild artifacts for a past day."""

import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from getpass import getuser
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console

from config.toml_config import ConfigLoader
from nh_cli.utils.default_command_group import create_default_command_group
from services.audit import AuditService
from services.git_safety import GitDirtyError, ensure_clean_repo, get_git_status


@dataclass
class CleanupTarget:
    label: str
    path: Path
    is_glob: bool = False


@dataclass
class CleanupSummary:
    touched: int = 0
    skipped: int = 0


app = typer.Typer(cls=create_default_command_group("main"))
console = Console()


def _relative_to_repo(path: Path, repo_root: Path) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def _build_cleanup_targets(repo_root: Path, date: str) -> List[CleanupTarget]:
    """Return the list of per-date artifacts that should be removed before rerun."""

    base_targets = [
        CleanupTarget("Daily outputs", repo_root / "data" / "outputs" / "daily" / date),
        CleanupTarget("Daily report", repo_root / "data" / "reports" / f"daily_report_{date}.md"),
        CleanupTarget("Publishing payload", repo_root / "data" / "publishing" / f"{date}.json"),
        CleanupTarget(
            "Publishing tags", repo_root / "data" / "publishing" / f"tags_{date}.json"
        ),
        CleanupTarget(
            "Publishing source manifest",
            repo_root / "data" / "publishing" / "source_manifests" / f"{date}.json",
        ),
        CleanupTarget(
            "Publishing vector export",
            repo_root / "data" / "publishing" / "vector_exports" / f"{date}.json",
        ),
        CleanupTarget("Dashboard", repo_root / "dashboards" / f"dashboard_{date}.html"),
        CleanupTarget("Manifest", repo_root / "data" / "manifests" / f"{date}.json"),
        CleanupTarget(
            "Runtime ledger",
            repo_root / "data" / "runtime" / f"execution_ledger_{date}.json",
        ),
        CleanupTarget(
            "Prompt execution log",
            repo_root / "logs" / f"prompt_execution_{date}.log",
        ),
    ]

    glob_targets = [
        CleanupTarget(
            "Orchestrator logs", repo_root / "logs" / f"orchestrator_*{date}*.log", is_glob=True
        )
    ]

    return base_targets + glob_targets


def _print_cleanup_plan(repo_root: Path, targets: List[CleanupTarget]) -> None:
    console.print("[bold]Cleanup plan[/bold]")
    if not targets:
        console.print("  [dim]No cleanup targets defined.[/dim]")
        console.print()
        return

    for target in targets:
        rel = _relative_to_repo(target.path, repo_root)
        if target.is_glob:
            matches = list(target.path.parent.glob(target.path.name))
            if matches:
                console.print(f"  - {rel} ({len(matches)} file(s))")
            else:
                console.print(f"  - {rel} [dim](no matches)[/dim]")
        else:
            if target.path.exists():
                console.print(f"  - {rel}")
            else:
                console.print(f"  - {rel} [dim](not found)[/dim]")
    console.print()


def _execute_cleanup(
    repo_root: Path, targets: List[CleanupTarget], dry_run: bool
) -> CleanupSummary:
    summary = CleanupSummary()

    for target in targets:
        if target.is_glob:
            matches = list(target.path.parent.glob(target.path.name))
            if not matches:
                summary.skipped += 1
                continue
            for match in matches:
                if _handle_single_path(repo_root, match, dry_run):
                    summary.touched += 1
                else:
                    summary.skipped += 1
            continue

        if not target.path.exists():
            summary.skipped += 1
            continue

        if _handle_single_path(repo_root, target.path, dry_run):
            summary.touched += 1
        else:
            summary.skipped += 1

    return summary


def _handle_single_path(repo_root: Path, path: Path, dry_run: bool) -> bool:
    if not path.exists():
        return False

    rel = _relative_to_repo(path, repo_root)
    if dry_run:
        console.print(f"[yellow][DRY RUN][/yellow] Would remove {rel}")
        return True

    try:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        console.print(f"[green]Removed[/green] {rel}")
        return True
    except Exception as exc:  # pragma: no cover - defensive logging
        console.print(f"[red]Error:[/red] Failed to remove {rel}: {exc}")
        raise typer.Exit(code=30) from exc


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

    audit_service = AuditService(repo_root)
    forced_items = [force] if force else []

    # Display header
    console.print(f"\n[bold cyan]NeuroHelix Reprocess[/bold cyan]")
    console.print(f"Date: {date}")
    if force:
        console.print(f"Force: {force}")
    if dry_run:
        console.print("[yellow]Mode: DRY RUN[/yellow]")
    console.print()

    cleanup_targets = _build_cleanup_targets(repo_root, date)
    _print_cleanup_plan(repo_root, cleanup_targets)
    cleanup_summary = _execute_cleanup(repo_root, cleanup_targets, dry_run=dry_run)

    action = "would be removed" if dry_run else "removed"
    console.print(
        f"Cleanup summary: {cleanup_summary.touched} item(s) {action}, "
        f"{cleanup_summary.skipped} skipped."
    )

    if dry_run:
        console.print(
            "\n[yellow]Dry run complete.[/yellow] No files were removed and the pipeline was not "
            "executed."
        )
        audit_service.log_reprocess(
            date=date,
            forced_items=forced_items,
            regenerated_files=[],
            dry_run=True,
        )
        raise typer.Exit(code=0)

    # Build command to delegate to 'nh run'
    cmd = ["nh", "run", "--date", date]

    if force:
        cmd.extend(["--force", force])

    env = os.environ.copy()
    env["RUN_MODE"] = "manual_override"
    env["MANUAL_OVERRIDE_OPERATOR"] = (
        os.environ.get("USER") or os.environ.get("LOGNAME") or getuser()
    )
    env["MANUAL_OVERRIDE_REASON"] = "force reprocess"
    env["MANUAL_OVERRIDE_DATE"] = date

    # Show command
    console.print(f"[dim]Delegating to: {' '.join(cmd)}[/dim]\n")

    # Execute via nh run
    try:
        result = subprocess.run(cmd, check=False, env=env)

        # Log to audit trail (only if not dry run)
        if not dry_run and result.returncode == 0:
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
