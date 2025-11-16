"""Run command - Execute daily pipeline."""

from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from adapters.filesystem import FileLock, LockError
from adapters.gemini_cli import GeminiCLIAdapter
from config.settings_schema import WaveType
from config.toml_config import ConfigLoader
from nh_cli.utils.default_command_group import create_default_command_group
from services.ledger import LedgerService
from services.manifest import ManifestService
from services.notifier import NotifierHooksConfig, NotifierService
from services.registry import get_registry_provider
from services.runner import RunnerService

app = typer.Typer(cls=create_default_command_group("main"))
console = Console()


@app.command()
def main(
    date: Optional[str] = typer.Option(
        None,
        "--date",
        "-d",
        help="Run date (YYYY-MM-DD). Default: today",
    ),
    wave: Optional[str] = typer.Option(
        None,
        "--wave",
        "-w",
        help="Execute specific wave only (search, aggregator, tagger, render, export, publish)",
    ),
    force: Optional[str] = typer.Option(
        None,
        "--force",
        "-f",
        help="Force rerun of specific prompt ID or wave name",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview actions without executing",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output results as JSON",
    ),
):
    """Execute the daily research pipeline.

    By default, runs all waves for today's date. Can be scoped to specific
    dates, waves, or prompts using flags.

    Examples:

        nh run                           # Run all waves for today

        nh run --date 2025-11-14         # Run for specific date

        nh run --wave search             # Run only search wave

        nh run --force prompt_id         # Force rerun specific prompt

        nh run --dry-run                 # Preview without executing
    """
    # Resolve date
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    # Validate date format
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        console.print(f"[red]Error:[/red] Invalid date format: {date}", style="bold")
        console.print("Expected format: YYYY-MM-DD")
        raise typer.Exit(code=10)

    # Get repo root (assume we're running from orchestrator/)
    repo_root = Path.cwd().parent if Path.cwd().name == "orchestrator" else Path.cwd()
    orchestrator_root = repo_root / "orchestrator" if repo_root.name != "orchestrator" else repo_root

    config_loader = ConfigLoader(orchestrator_root)
    config = config_loader.load()

    # Initialize services
    ledger_service = LedgerService(repo_root)
    manifest_service = ManifestService(repo_root)
    gemini_adapter = GeminiCLIAdapter(repo_root, enable_rate_limiting=True)

    notifier_service = NotifierService(
        repo_root,
        NotifierHooksConfig(
            enable_success=config.notifier.enable_success,
            enable_failure=config.notifier.enable_failure,
            success_script=repo_root / config.notifier.success_script,
            failure_script=repo_root / config.notifier.failure_script,
        ),
    )

    # Load registry
    registry_path = repo_root / "orchestrator" / "config" / "prompts.tsv"
    if not registry_path.exists():
        console.print(
            f"[red]Error:[/red] Registry not found: {registry_path}", style="bold"
        )
        raise typer.Exit(code=10)

    try:
        registry_provider = get_registry_provider(registry_path, format_type="tsv")
        prompts = registry_provider.load()

        # Validate registry
        is_valid, errors = registry_provider.validate()
        if not is_valid:
            console.print("[red]Error:[/red] Registry validation failed:", style="bold")
            for error in errors:
                console.print(f"  - {error}")
            raise typer.Exit(code=10)

    except Exception as e:
        console.print(f"[red]Error:[/red] Failed to load registry: {e}", style="bold")
        raise typer.Exit(code=10)

    # Determine which waves to run
    waves_to_run = []
    if wave:
        try:
            waves_to_run = [WaveType(wave.lower())]
        except ValueError:
            console.print(f"[red]Error:[/red] Invalid wave: {wave}", style="bold")
            console.print(
                "Valid waves: search, aggregator, tagger, render, export, publish"
            )
            raise typer.Exit(code=10)
    else:
        waves_to_run = [
            WaveType.SEARCH,
            WaveType.AGGREGATOR,
            WaveType.TAGGER,
            WaveType.RENDER,
            WaveType.EXPORT,
        ]

    # Parse force flag
    forced_prompts = []
    forced_waves = []
    if force:
        # Check if it's a wave or prompt ID
        try:
            forced_waves = [WaveType(force.lower())]
        except ValueError:
            forced_prompts = [force]

    # Create manifest
    manifest = manifest_service.create_manifest(
        date=date,
        forced_prompts=forced_prompts,
        forced_waves=forced_waves,
        dry_run=dry_run,
    )

    # Display run summary
    console.print(f"\n[bold cyan]NeuroHelix Pipeline Run[/bold cyan]")
    console.print(f"Date: {date}")
    console.print(f"Run ID: {manifest.run_id}")
    console.print(f"Waves: {', '.join(w.value for w in waves_to_run)}")
    if dry_run:
        console.print("[yellow]Mode: DRY RUN[/yellow]")
    if forced_prompts:
        console.print(f"Forced prompts: {', '.join(forced_prompts)}")
    if forced_waves:
        console.print(f"Forced waves: {', '.join(w.value for w in forced_waves)}")
    console.print()

    # Acquire lock
    lock_path = repo_root / "var" / "locks" / "nh-run.lock"
    lock = FileLock(lock_path, ttl_seconds=7200)

    try:
        lock.acquire(command=f"nh run --date {date}", force=False)
    except LockError as e:
        console.print(f"[red]Error:[/red] {e}", style="bold")
        console.print(
            "\nAnother run is already in progress. Use --force to override (not recommended)."
        )
        raise typer.Exit(code=20)

    try:
        # Compute hashes for telemetry
        registry_hash = ledger_service.compute_registry_hash(registry_path)
        config_fingerprint = ledger_service.compute_config_fingerprint(
            {"date": date, "waves": [w.value for w in waves_to_run]}
        )

        # Initialize runner
        runner = RunnerService(
            repo_root, gemini_adapter, ledger_service, manifest_service
        )

        # Execute waves
        all_completed = []
        all_failed = []

        for wave_type in waves_to_run:
            completed, failed = runner.execute_wave(
                wave=wave_type,
                prompts=prompts,
                date=date,
                run_id=manifest.run_id,
                registry_hash=registry_hash,
                config_fingerprint=config_fingerprint,
                forced_prompts=forced_prompts,
                forced_waves=forced_waves,
                dry_run=dry_run,
            )
            all_completed.extend(completed)
            all_failed.extend(failed)

        # Update manifest
        manifest.completed_prompts = all_completed
        manifest.failed_prompts = all_failed
        manifest.ended_at = datetime.now()

        # Save manifest
        manifest_service.save_manifest(manifest, date)

        # Display results
        console.print("\n[bold]Execution Summary[/bold]\n")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right")

        table.add_row("Total Prompts", str(len(all_completed) + len(all_failed)))
        table.add_row(
            "Completed",
            f"[green]{len(all_completed)}[/green]",
        )
        table.add_row(
            "Failed",
            f"[red]{len(all_failed)}[/red]" if all_failed else "0",
        )

        duration = (manifest.ended_at - manifest.started_at).total_seconds()
        table.add_row("Duration", f"{duration:.1f}s")

        console.print(table)

        # Show statistics
        stats = ledger_service.get_summary_stats(date)
        if stats["total_retries"] > 0:
            console.print(f"\nTotal retries: {stats['total_retries']}")

        run_log_path = ledger_service.get_run_log_path(date)

        if not dry_run:
            if all_failed:
                sent = notifier_service.notify_failures(date, all_failed, run_log_path)
                if sent:
                    console.print("[dim]Failure notifier dispatched[/dim]")
            elif config.notifier.enable_success:
                sent = notifier_service.notify_success(date, run_log_path)
                if sent:
                    console.print("[dim]Success notifier dispatched[/dim]")

        # Exit code
        if all_failed:
            console.print(
                f"\n[yellow]Warning:[/yellow] {len(all_failed)} prompts failed"
            )
            raise typer.Exit(code=30)
        else:
            console.print("\n[green]✓[/green] Pipeline completed successfully")
            raise typer.Exit(code=0)

    finally:
        lock.release()
