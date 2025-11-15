"""Cleanup command - Remove temporary files and stale locks."""

from datetime import datetime, timedelta
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from services.audit import AuditService

app = typer.Typer()
console = Console()


@app.command()
def main(
    keep_days: int = typer.Option(
        90,
        "--keep-days",
        "-k",
        help="Keep artifacts newer than this many days",
        min=1,
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview cleanup without removing files",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output results as JSON",
    ),
):
    """Clean up temporary files, stale locks, and old artifacts.

    Removes:
    - Stale lock files (older than TTL)
    - Old daily outputs (older than --keep-days)
    - Old manifests, logs, and temporary files

    Examples:

        nh cleanup                      # Clean with 90-day retention

        nh cleanup --keep-days 30       # Keep only last 30 days

        nh cleanup --dry-run            # Preview what would be removed
    """
    # Get repo root
    repo_root = Path.cwd().parent if Path.cwd().name == "orchestrator" else Path.cwd()

    # Initialize audit service
    audit_service = AuditService(repo_root)

    # Display header
    if not json_output:
        console.print(f"\n[bold cyan]NeuroHelix Cleanup[/bold cyan]")
        console.print(f"Retention: {keep_days} days")
        if dry_run:
            console.print("[yellow]Mode: DRY RUN[/yellow]")
        console.print()

    # Calculate cutoff date
    cutoff_date = datetime.now() - timedelta(days=keep_days)
    cutoff_timestamp = cutoff_date.timestamp()

    removed_files = []
    removed_locks = []
    bytes_freed = 0

    # 1. Clean stale locks
    locks_dir = repo_root / "var" / "locks"
    if locks_dir.exists():
        for lock_file in locks_dir.glob("*.lock"):
            try:
                mtime = lock_file.stat().st_mtime
                if mtime < cutoff_timestamp:
                    size = lock_file.stat().st_size
                    if not dry_run:
                        lock_file.unlink()
                    removed_locks.append(str(lock_file))
                    bytes_freed += size
            except Exception as e:
                console.print(f"[yellow]Warning:[/yellow] Could not remove {lock_file}: {e}")

    # 2. Clean old daily outputs
    outputs_dir = repo_root / "data" / "outputs" / "daily"
    if outputs_dir.exists():
        for date_dir in outputs_dir.iterdir():
            if date_dir.is_dir():
                try:
                    # Parse date from directory name
                    dir_date = datetime.strptime(date_dir.name, "%Y-%m-%d")
                    if dir_date < cutoff_date:
                        # Calculate size
                        dir_size = sum(
                            f.stat().st_size for f in date_dir.rglob("*") if f.is_file()
                        )
                        if not dry_run:
                            import shutil

                            shutil.rmtree(date_dir)
                        removed_files.append(str(date_dir))
                        bytes_freed += dir_size
                except ValueError:
                    # Skip non-date directories
                    pass
                except Exception as e:
                    console.print(
                        f"[yellow]Warning:[/yellow] Could not remove {date_dir}: {e}"
                    )

    # 3. Clean old reports
    reports_dir = repo_root / "data" / "reports"
    if reports_dir.exists():
        for report_file in reports_dir.glob("daily_report_*.md"):
            try:
                mtime = report_file.stat().st_mtime
                if mtime < cutoff_timestamp:
                    size = report_file.stat().st_size
                    if not dry_run:
                        report_file.unlink()
                    removed_files.append(str(report_file))
                    bytes_freed += size
            except Exception as e:
                console.print(
                    f"[yellow]Warning:[/yellow] Could not remove {report_file}: {e}"
                )

    # 4. Clean old manifests
    manifests_dir = repo_root / "data" / "manifests"
    if manifests_dir.exists():
        for manifest_file in manifests_dir.glob("*.json"):
            try:
                mtime = manifest_file.stat().st_mtime
                if mtime < cutoff_timestamp:
                    size = manifest_file.stat().st_size
                    if not dry_run:
                        manifest_file.unlink()
                    removed_files.append(str(manifest_file))
                    bytes_freed += size
            except Exception as e:
                console.print(
                    f"[yellow]Warning:[/yellow] Could not remove {manifest_file}: {e}"
                )

    # 5. Clean old logs
    for log_type in ["runs", "ledger"]:
        log_dir = repo_root / "logs" / log_type
        if log_dir.exists():
            for log_file in log_dir.iterdir():
                if log_file.is_file():
                    try:
                        mtime = log_file.stat().st_mtime
                        if mtime < cutoff_timestamp:
                            size = log_file.stat().st_size
                            if not dry_run:
                                log_file.unlink()
                            removed_files.append(str(log_file))
                            bytes_freed += size
                    except Exception as e:
                        console.print(
                            f"[yellow]Warning:[/yellow] Could not remove {log_file}: {e}"
                        )

    # 6. Clean old dashboards
    dashboards_dir = repo_root / "dashboards"
    if dashboards_dir.exists():
        for dashboard_file in dashboards_dir.glob("dashboard_*.html"):
            try:
                mtime = dashboard_file.stat().st_mtime
                if mtime < cutoff_timestamp:
                    size = dashboard_file.stat().st_size
                    if not dry_run:
                        dashboard_file.unlink()
                    removed_files.append(str(dashboard_file))
                    bytes_freed += size
            except Exception as e:
                console.print(
                    f"[yellow]Warning:[/yellow] Could not remove {dashboard_file}: {e}"
                )

    # 7. Clean old publishing artifacts
    publishing_dir = repo_root / "data" / "publishing"
    if publishing_dir.exists():
        for pub_file in publishing_dir.glob("*.json"):
            try:
                mtime = pub_file.stat().st_mtime
                if mtime < cutoff_timestamp:
                    size = pub_file.stat().st_size
                    if not dry_run:
                        pub_file.unlink()
                    removed_files.append(str(pub_file))
                    bytes_freed += size
            except Exception as e:
                console.print(f"[yellow]Warning:[/yellow] Could not remove {pub_file}: {e}")

    # Log to audit trail
    if not dry_run:
        audit_service.log_cleanup(
            removed_files=removed_files,
            removed_locks=removed_locks,
            bytes_freed=bytes_freed,
            dry_run=dry_run,
        )

    # Display results
    if json_output:
        import json

        result = {
            "files_removed": len(removed_files),
            "locks_removed": len(removed_locks),
            "bytes_freed": bytes_freed,
            "dry_run": dry_run,
        }
        console.print(json.dumps(result))
    else:
        console.print("[bold]Cleanup Summary[/bold]\n")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right")

        table.add_row("Files Removed", str(len(removed_files)))
        table.add_row("Locks Removed", str(len(removed_locks)))
        table.add_row("Space Freed", f"{bytes_freed / 1024 / 1024:.2f} MB")

        console.print(table)

        if dry_run:
            console.print(
                "\n[yellow]Note:[/yellow] This was a dry run. No files were actually removed."
            )
        else:
            console.print("\n[green]✓[/green] Cleanup completed successfully")

    raise typer.Exit(code=0)
