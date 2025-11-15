"""Automation command - Manage LaunchD jobs."""

import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from services.audit import AuditService

app = typer.Typer()
console = Console()

PLIST_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.neurohelix.daily</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>-m</string>
        <string>nh_cli</string>
        <string>run</string>
    </array>
    <key>WorkingDirectory</key>
    <string>{repo_root}</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>{path_env}</string>
    </dict>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>7</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>{repo_root}/logs/launchd_stdout.log</string>
    <key>StandardErrorPath</key>
    <string>{repo_root}/logs/launchd_stderr.log</string>
</dict>
</plist>
"""


@app.command("install")
def install(
    plist: Optional[str] = typer.Option(
        None,
        "--plist",
        "-p",
        help="Path to plist file (default: auto-generate)",
    ),
    hour: int = typer.Option(
        7,
        "--hour",
        "-H",
        help="Hour to run (0-23)",
        min=0,
        max=23,
    ),
    minute: int = typer.Option(
        0,
        "--minute",
        "-M",
        help="Minute to run (0-59)",
        min=0,
        max=59,
    ),
):
    """Install LaunchD job for daily automation.

    Validates environment prerequisites before installing the LaunchD
    plist for automated daily runs.

    Examples:

        nh automation install                    # Install with defaults (7:00 AM)

        nh automation install --hour 8 --minute 30  # Run at 8:30 AM

        nh automation install --plist /path      # Use custom plist
    """
    console.print("\n[bold cyan]Install LaunchD Automation[/bold cyan]\n")

    # Get repo root
    repo_root = Path.cwd().parent if Path.cwd().name == "orchestrator" else Path.cwd()

    # Validate environment
    console.print("Validating environment...")

    # Check for Python
    import sys

    python_path = sys.executable
    console.print(f"  Python: {python_path} ✓")

    # Check for required environment variables
    path_env = os.getenv("PATH", "")
    if not path_env:
        console.print("[red]Error:[/red] PATH environment variable not set", style="bold")
        raise typer.Exit(code=10)

    # Determine plist path
    if plist:
        plist_path = Path(plist)
    else:
        # Auto-generate
        launchagents_dir = Path.home() / "Library" / "LaunchAgents"
        launchagents_dir.mkdir(parents=True, exist_ok=True)
        plist_path = launchagents_dir / "com.neurohelix.daily.plist"

        # Generate plist content
        plist_content = PLIST_TEMPLATE.format(
            python_path=python_path,
            repo_root=str(repo_root),
            path_env=path_env,
        )

        # Update hour/minute
        plist_content = plist_content.replace("<integer>7</integer>", f"<integer>{hour}</integer>")
        plist_content = plist_content.replace("<integer>0</integer>", f"<integer>{minute}</integer>", 1)

        # Write plist
        with open(plist_path, "w") as f:
            f.write(plist_content)

        console.print(f"  Generated plist: {plist_path} ✓")

    # Load plist
    console.print("\nLoading LaunchD job...")
    try:
        subprocess.run(
            ["launchctl", "load", str(plist_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        console.print(f"  Loaded: com.neurohelix.daily ✓")
    except subprocess.CalledProcessError as e:
        if "already loaded" not in e.stderr.lower():
            console.print(f"[red]Error:[/red] Failed to load: {e.stderr}", style="bold")
            raise typer.Exit(code=30)
        console.print("  Already loaded ✓")

    # Write audit log
    audit_service = AuditService(repo_root)
    audit_service.log_automation_install(
        plist_path=str(plist_path),
        schedule={"hour": hour, "minute": minute},
        success=True,
    )

    console.print(f"\n[green]✓[/green] Automation installed successfully")
    console.print(f"Daily runs scheduled for {hour:02d}:{minute:02d}")


@app.command("status")
def status():
    """Show automation status and next scheduled run.

    Displays LaunchD job status, last run time from ledger, next
    scheduled fire time, and lock status.

    Examples:

        nh automation status
    """
    console.print("\n[bold cyan]Automation Status[/bold cyan]\n")

    # Get repo root
    repo_root = Path.cwd().parent if Path.cwd().name == "orchestrator" else Path.cwd()

    # Check if job is loaded
    try:
        result = subprocess.run(
            ["launchctl", "list"],
            capture_output=True,
            text=True,
            check=True,
        )
        is_loaded = "com.neurohelix.daily" in result.stdout
    except:
        is_loaded = False

    # Check for plist file
    plist_path = Path.home() / "Library" / "LaunchAgents" / "com.neurohelix.daily.plist"
    plist_exists = plist_path.exists()

    # Get last run from ledger
    ledger_dir = repo_root / "logs" / "ledger"
    last_run = None
    if ledger_dir.exists():
        ledger_files = sorted(ledger_dir.glob("*.jsonl"), reverse=True)
        if ledger_files:
            last_run = ledger_files[0].stem  # Date from filename

    # Check lock status
    lock_path = repo_root / "var" / "locks" / "nh-run.lock"
    is_locked = lock_path.exists()

    # Display table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Property", style="cyan")
    table.add_column("Value")

    table.add_row(
        "LaunchD Job",
        "[green]Loaded[/green]" if is_loaded else "[red]Not Loaded[/red]",
    )
    table.add_row(
        "Plist File",
        f"[green]{plist_path}[/green]" if plist_exists else "[red]Not Found[/red]",
    )
    table.add_row("Last Run", last_run if last_run else "[dim]Never[/dim]")
    table.add_row(
        "Lock Status",
        "[yellow]Locked[/yellow]" if is_locked else "[green]Available[/green]",
    )

    console.print(table)

    if plist_exists:
        console.print(f"\n[dim]Schedule: Daily at 07:00 (from plist)[/dim]")


@app.command("remove")
def remove():
    """Remove LaunchD job.

    Unloads and removes the LaunchD plist, disabling daily automation.

    Examples:

        nh automation remove
    """
    console.print("\n[bold cyan]Remove LaunchD Automation[/bold cyan]\n")

    # Get repo root
    repo_root = Path.cwd().parent if Path.cwd().name == "orchestrator" else Path.cwd()

    # Plist path
    plist_path = Path.home() / "Library" / "LaunchAgents" / "com.neurohelix.daily.plist"

    # Unload if loaded
    console.print("Unloading LaunchD job...")
    try:
        subprocess.run(
            ["launchctl", "unload", str(plist_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        console.print("  Unloaded ✓")
    except subprocess.CalledProcessError as e:
        if "could not find" not in e.stderr.lower():
            console.print(f"[yellow]Warning:[/yellow] {e.stderr}")
        console.print("  Not loaded (skipped)")

    # Remove plist
    if plist_path.exists():
        plist_path.unlink()
        console.print(f"  Removed plist: {plist_path} ✓")
    else:
        console.print("  Plist not found (skipped)")

    # Write audit log
    audit_service = AuditService(repo_root)
    audit_service.log_automation_remove(plist_path=str(plist_path), success=True)

    console.print(f"\n[green]✓[/green] Automation removed successfully")
