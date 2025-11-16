"""Registry command - Validate and inspect prompt registry."""

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from services.registry import get_registry_provider
from services.sqlite_registry import migrate_tsv_to_sqlite, SQLiteRegistryProvider
from config.toml_config import ConfigLoader

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
        else:
            console.print("[red]✗[/red] Registry validation failed:\n")
            for error in errors:
                console.print(f"  - {error}")
            raise typer.Exit(code=10)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/red] Failed to load registry: {e}")
        raise typer.Exit(code=10)


@app.command("migrate")
def migrate(
    output: str = typer.Option(
        "config/prompts.db",
        "--output",
        "-o",
        help="Output SQLite database path",
    ),
    input_tsv: str = typer.Option(
        "config/prompts.tsv",
        "--input",
        "-i",
        help="Input TSV registry path",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing database",
    ),
):
    """Migrate TSV registry to SQLite database.

    Examples:

        nh registry migrate                           # Use default paths

        nh registry migrate --output custom.db        # Custom output path

        nh registry migrate --force                   # Overwrite existing DB
    """
    # Get repo root
    repo_root = Path.cwd().parent if Path.cwd().name == "orchestrator" else Path.cwd()

    # Resolve paths
    input_path = repo_root / "orchestrator" / input_tsv
    output_path = repo_root / "orchestrator" / output

    # Validate input
    if not input_path.exists():
        console.print(f"[red]Error:[/red] Input TSV not found: {input_path}")
        raise typer.Exit(code=10)

    # Check output
    if output_path.exists() and not force:
        console.print(
            f"[yellow]Warning:[/yellow] Database already exists: {output_path}"
        )
        console.print("Use --force to overwrite")
        raise typer.Exit(code=1)

    try:
        # Perform migration
        console.print(f"\n[bold]Migrating TSV → SQLite[/bold]")
        console.print(f"Input:  {input_path}")
        console.print(f"Output: {output_path}\n")

        count = migrate_tsv_to_sqlite(input_path, output_path)

        console.print(f"[green]✓[/green] Migrated {count} prompts successfully")
        console.print("\nTo use SQLite registry, set environment variables (e.g., in .env.local):")
        console.print("NH_REGISTRY_BACKEND=sqlite")
        console.print("NH_REGISTRY_SQLITE_PATH=config/prompts.db")

    except Exception as e:
        console.print(f"[red]Error:[/red] Migration failed: {e}")
        raise typer.Exit(code=30)


@app.command("list")
def list_prompts(
    wave: str = typer.Option(
        None,
        "--wave",
        "-w",
        help="Filter by wave (search, aggregator, tagger, etc.)",
    ),
    backend: str = typer.Option(
        None,
        "--backend",
        "-b",
        help="Registry backend (tsv or sqlite)",
    ),
):
    """List prompts in the registry.

    Examples:

        nh registry list                    # List all prompts

        nh registry list --wave search      # List search wave prompts

        nh registry list --backend sqlite   # Use SQLite backend
    """
    # Get repo root
    repo_root = Path.cwd().parent if Path.cwd().name == "orchestrator" else Path.cwd()

    # Load config to determine backend
    config_loader = ConfigLoader(repo_root / "orchestrator")

    if backend is None:
        backend = config_loader.get_registry_backend()

    registry_path = config_loader.get_registry_path()

    if not registry_path.exists():
        console.print(f"[red]Error:[/red] Registry not found: {registry_path}")
        console.print(f"\nExpected backend: {backend}")
        if backend == "sqlite":
            console.print("Run 'nh registry migrate' to create SQLite database")
        raise typer.Exit(code=10)

    try:
        # Load prompts
        provider = get_registry_provider(registry_path, format_type=backend)
        prompts = provider.load()

        # Filter by wave if specified
        if wave:
            from config.settings_schema import WaveType

            wave_type = WaveType(wave)
            prompts = [p for p in prompts if p.wave == wave_type]

        # Display table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Title", style="white")
        table.add_column("Wave", style="yellow")
        table.add_column("Model", style="green")
        table.add_column("Concurrency", style="blue")

        for prompt in prompts:
            table.add_row(
                prompt.prompt_id,
                prompt.title,
                prompt.wave.value,
                prompt.model,
                prompt.concurrency_class.value,
            )

        console.print(f"\n[bold]Registry: {backend.upper()}[/bold]")
        console.print(f"Total prompts: {len(prompts)}\n")
        console.print(table)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=10)
