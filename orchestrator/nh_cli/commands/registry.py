"""Registry command - Validate and inspect prompt registry."""

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from services.registry import get_registry_provider

app = typer.Typer()
console = Console()


@app.command("validate")
def validate(
    format_type: str = typer.Option(
        "tsv",
        "--format",
        "-f",
        help="Registry format (tsv or sqlite)",
    ),
):
    """Validate the prompt registry.

    Checks for duplicate IDs, missing fields, invalid configurations,
    and wave ordering issues.

    Examples:

        nh registry validate              # Validate TSV registry

        nh registry validate --format tsv # Explicit format
    """
    # Get repo root
    repo_root = Path.cwd().parent if Path.cwd().name == "orchestrator" else Path.cwd()

    # Get registry path
    if format_type == "tsv":
        registry_path = repo_root / "orchestrator" / "config" / "prompts.tsv"
    else:
        console.print(f"[red]Error:[/red] Unsupported format: {format_type}")
        raise typer.Exit(code=10)

    if not registry_path.exists():
        console.print(f"[red]Error:[/red] Registry not found: {registry_path}")
        raise typer.Exit(code=10)

    # Load and validate
    try:
        provider = get_registry_provider(registry_path, format_type=format_type)
        prompts = provider.load()

        console.print(f"\n[bold]Registry Validation[/bold]")
        console.print(f"Path: {registry_path}")
        console.print(f"Format: {format_type}")
        console.print(f"Prompts loaded: {len(prompts)}\n")

        # Validate
        is_valid, errors = provider.validate()

        if is_valid:
            console.print("[green]✓[/green] Registry is valid\n")

            # Display summary
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Wave", style="cyan")
            table.add_column("Prompts", justify="right")

            waves = {}
            for prompt in prompts:
                wave = prompt.wave.value
                waves[wave] = waves.get(wave, 0) + 1

            for wave, count in sorted(waves.items()):
                table.add_row(wave, str(count))

            console.print(table)
            raise typer.Exit(code=0)
        else:
            console.print("[red]✗[/red] Registry validation failed:\n")
            for error in errors:
                console.print(f"  - {error}")
            raise typer.Exit(code=10)

    except Exception as e:
        console.print(f"[red]Error:[/red] Failed to load registry: {e}")
        raise typer.Exit(code=10)
