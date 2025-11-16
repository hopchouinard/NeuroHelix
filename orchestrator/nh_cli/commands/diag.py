"""Diagnostics command - System status and environment check."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer()
console = Console()


@app.command()
def main(
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output as JSON",
    ),
):
    """Print diagnostics and system status.

    Checks for required binaries, environment variables, file permissions,
    and reports version information.

    Examples:

        nh diag            # Human-readable output

        nh diag --json     # JSON output for scripting
    """
    diagnostics = {}

    # Python version
    diagnostics["python_version"] = sys.version.split()[0]

    # Check for required binaries
    binaries = ["gemini", "pnpm", "wrangler", "git"]
    binary_status = {}

    for binary in binaries:
        path = shutil.which(binary)
        if path:
            # Get version
            try:
                if binary == "gemini":
                    result = subprocess.run(
                        [binary, "--version"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    version = result.stdout.strip() if result.returncode == 0 else "unknown"
                elif binary == "git":
                    result = subprocess.run(
                        [binary, "--version"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    version = result.stdout.strip().split()[-1] if result.returncode == 0 else "unknown"
                else:
                    result = subprocess.run(
                        [binary, "--version"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    version = result.stdout.strip().split()[0] if result.returncode == 0 else "unknown"
            except Exception:
                version = "unknown"

            binary_status[binary] = {"available": True, "path": path, "version": version}
        else:
            binary_status[binary] = {"available": False}

    diagnostics["binaries"] = binary_status

    # Environment variables
    env_vars = [
        "NH_DEFAULT_MODEL",
        "CLOUDFLARE_API_TOKEN",
        "NH_REPO_ROOT",
    ]
    env_status = {}
    for var in env_vars:
        value = os.getenv(var)
        env_status[var] = {"set": value is not None, "value": "***" if value else None}

    diagnostics["environment"] = env_status

    # Directory permissions
    repo_root = Path.cwd().parent if Path.cwd().name == "orchestrator" else Path.cwd()
    directories = [
        repo_root / "data" / "outputs",
        repo_root / "data" / "reports",
        repo_root / "data" / "manifests",
        repo_root / "logs" / "runs",
        repo_root / "logs" / "ledger",
        repo_root / "var" / "locks",
    ]

    dir_status = {}
    for directory in directories:
        exists = directory.exists()
        writable = os.access(directory, os.W_OK) if exists else False
        dir_status[str(directory)] = {"exists": exists, "writable": writable}

    diagnostics["directories"] = dir_status

    # Output
    if json_output:
        console.print(json.dumps(diagnostics, indent=2))
    else:
        console.print("\n[bold]NeuroHelix Diagnostics[/bold]\n")

        # Python
        console.print(f"Python: {diagnostics['python_version']}")

        # Binaries
        console.print("\n[bold]Required Binaries[/bold]")
        table = Table(show_header=True)
        table.add_column("Binary")
        table.add_column("Status")
        table.add_column("Version")

        for binary, status in binary_status.items():
            if status["available"]:
                table.add_row(
                    binary,
                    "[green]✓[/green]",
                    status.get("version", "unknown"),
                )
            else:
                table.add_row(binary, "[red]✗[/red]", "not found")

        console.print(table)

        # Environment
        console.print("\n[bold]Environment Variables[/bold]")
        env_table = Table(show_header=True)
        env_table.add_column("Variable")
        env_table.add_column("Status")

        for var, status in env_status.items():
            if status["set"]:
                env_table.add_row(var, "[green]Set[/green]")
            else:
                env_table.add_row(var, "[yellow]Not set[/yellow]")

        console.print(env_table)

        # Directories
        console.print("\n[bold]Directory Permissions[/bold]")
        dir_table = Table(show_header=True)
        dir_table.add_column("Directory")
        dir_table.add_column("Exists")
        dir_table.add_column("Writable")

        for directory, status in dir_status.items():
            exists_mark = "[green]✓[/green]" if status["exists"] else "[red]✗[/red]"
            writable_mark = (
                "[green]✓[/green]" if status["writable"] else "[red]✗[/red]"
            )
            dir_table.add_row(Path(directory).name, exists_mark, writable_mark)

        console.print(dir_table)
        console.print()
