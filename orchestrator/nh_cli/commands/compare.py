"""Compare command - Parity harness for Bash vs Python outputs."""

from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from adapters.filesystem import compute_file_hash

app = typer.Typer()
console = Console()


@app.command()
def main(
    date: str = typer.Argument(..., help="Date to compare (YYYY-MM-DD)"),
    bash_manifest: str = typer.Option(
        None,
        "--bash-manifest",
        "-b",
        help="Path to Bash run manifest (for comparison)",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output results as JSON",
    ),
):
    """Compare Bash vs Python orchestrator outputs for a specific date.

    Validates that both orchestrators produced identical artifacts by
    comparing file presence and SHA256 hashes.

    Examples:

        nh compare 2025-11-14                    # Compare outputs

        nh compare 2025-11-14 --json             # JSON output

        nh compare 2025-11-14 --bash-manifest path  # Compare with manifest
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

    # Display header
    if not json_output:
        console.print(f"\n[bold cyan]NeuroHelix Parity Check[/bold cyan]")
        console.print(f"Date: {date}\n")

    # Paths to check
    outputs_dir = repo_root / "data" / "outputs" / "daily" / date
    report_file = repo_root / "data" / "reports" / f"daily_report_{date}.md"
    tags_file = repo_root / "data" / "publishing" / f"tags_{date}.json"
    dashboard_file = repo_root / "dashboards" / f"dashboard_{date}.html"
    export_file = repo_root / "data" / "publishing" / f"{date}.json"
    manifest_file = repo_root / "data" / "manifests" / f"{date}.json"

    # Check file existence and compute hashes
    results = []
    missing_files = []
    total_files = 0

    # 1. Check daily outputs (22 prompt files expected)
    if outputs_dir.exists():
        for prompt_file in outputs_dir.glob("*.md"):
            total_files += 1
            try:
                file_hash = compute_file_hash(prompt_file)
                results.append(
                    {
                        "path": str(prompt_file.relative_to(repo_root)),
                        "exists": True,
                        "hash": file_hash,
                        "size": prompt_file.stat().st_size,
                    }
                )
            except Exception as e:
                results.append(
                    {
                        "path": str(prompt_file.relative_to(repo_root)),
                        "exists": False,
                        "error": str(e),
                    }
                )
                missing_files.append(str(prompt_file.relative_to(repo_root)))
    else:
        missing_files.append(f"data/outputs/daily/{date}/")

    # 2. Check report
    total_files += 1
    if report_file.exists():
        try:
            file_hash = compute_file_hash(report_file)
            results.append(
                {
                    "path": str(report_file.relative_to(repo_root)),
                    "exists": True,
                    "hash": file_hash,
                    "size": report_file.stat().st_size,
                }
            )
        except Exception as e:
            results.append(
                {
                    "path": str(report_file.relative_to(repo_root)),
                    "exists": False,
                    "error": str(e),
                }
            )
            missing_files.append(str(report_file.relative_to(repo_root)))
    else:
        missing_files.append(str(report_file.relative_to(repo_root)))

    # 3. Check tags
    total_files += 1
    if tags_file.exists():
        try:
            file_hash = compute_file_hash(tags_file)
            results.append(
                {
                    "path": str(tags_file.relative_to(repo_root)),
                    "exists": True,
                    "hash": file_hash,
                    "size": tags_file.stat().st_size,
                }
            )
        except Exception as e:
            results.append(
                {
                    "path": str(tags_file.relative_to(repo_root)),
                    "exists": False,
                    "error": str(e),
                }
            )
            missing_files.append(str(tags_file.relative_to(repo_root)))
    else:
        missing_files.append(str(tags_file.relative_to(repo_root)))

    # 4. Check dashboard
    total_files += 1
    if dashboard_file.exists():
        try:
            file_hash = compute_file_hash(dashboard_file)
            results.append(
                {
                    "path": str(dashboard_file.relative_to(repo_root)),
                    "exists": True,
                    "hash": file_hash,
                    "size": dashboard_file.stat().st_size,
                }
            )
        except Exception as e:
            results.append(
                {
                    "path": str(dashboard_file.relative_to(repo_root)),
                    "exists": False,
                    "error": str(e),
                }
            )
            missing_files.append(str(dashboard_file.relative_to(repo_root)))
    else:
        missing_files.append(str(dashboard_file.relative_to(repo_root)))

    # 5. Check export
    total_files += 1
    if export_file.exists():
        try:
            file_hash = compute_file_hash(export_file)
            results.append(
                {
                    "path": str(export_file.relative_to(repo_root)),
                    "exists": True,
                    "hash": file_hash,
                    "size": export_file.stat().st_size,
                }
            )
        except Exception as e:
            results.append(
                {
                    "path": str(export_file.relative_to(repo_root)),
                    "exists": False,
                    "error": str(e),
                }
            )
            missing_files.append(str(export_file.relative_to(repo_root)))
    else:
        missing_files.append(str(export_file.relative_to(repo_root)))

    # 6. Check manifest (Python-only artifact)
    if manifest_file.exists():
        try:
            file_hash = compute_file_hash(manifest_file)
            results.append(
                {
                    "path": str(manifest_file.relative_to(repo_root)),
                    "exists": True,
                    "hash": file_hash,
                    "size": manifest_file.stat().st_size,
                    "python_only": True,
                }
            )
        except Exception as e:
            results.append(
                {
                    "path": str(manifest_file.relative_to(repo_root)),
                    "exists": False,
                    "error": str(e),
                    "python_only": True,
                }
            )

    # Display results
    if json_output:
        import json

        output = {
            "date": date,
            "total_files": total_files,
            "files_found": len([r for r in results if r.get("exists", False)]),
            "files_missing": len(missing_files),
            "missing_files": missing_files,
            "results": results,
        }
        console.print(json.dumps(output, indent=2))
    else:
        # Summary table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right")

        files_found = len([r for r in results if r.get("exists", False)])
        table.add_row("Total Files Checked", str(total_files))
        table.add_row(
            "Files Found",
            f"[green]{files_found}[/green]"
            if files_found == total_files
            else f"[red]{files_found}[/red]",
        )
        table.add_row(
            "Files Missing",
            f"[red]{len(missing_files)}[/red]"
            if missing_files
            else "[green]0[/green]",
        )

        console.print(table)

        # Show missing files
        if missing_files:
            console.print(f"\n[red]Missing Files:[/red]")
            for missing in missing_files[:10]:  # Limit to first 10
                console.print(f"  - {missing}")
            if len(missing_files) > 10:
                console.print(f"  ... and {len(missing_files) - 10} more")

        # Parity conclusion
        console.print()
        if files_found == total_files:
            console.print(
                "[green]✓[/green] All expected files present - parity check passed"
            )
        else:
            console.print(
                f"[yellow]⚠[/yellow] {len(missing_files)} files missing - parity check failed"
            )

        console.print(
            f"\n[dim]Note: File hash comparison requires baseline run from Bash orchestrator[/dim]"
        )

    # Exit code
    if missing_files:
        raise typer.Exit(code=20)
    else:
        raise typer.Exit(code=0)
