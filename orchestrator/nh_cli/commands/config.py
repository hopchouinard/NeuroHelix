"""Config command - Manage .nh.toml configuration."""

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from config.toml_config import ConfigLoader, get_config

app = typer.Typer()
console = Console()


@app.command("init")
def init(
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing config file",
    ),
):
    """Initialize a new .nh.toml configuration file.

    Creates a sample configuration file with all available options
    and default values.

    Examples:

        nh config init              # Create .nh.toml with defaults

        nh config init --force      # Overwrite existing config
    """
    # Get repo root
    repo_root = Path.cwd().parent if Path.cwd().name == "orchestrator" else Path.cwd()
    orchestrator_root = repo_root / "orchestrator"

    config_loader = ConfigLoader(orchestrator_root)
    config_path = config_loader.config_path

    if config_path.exists() and not force:
        console.print(
            f"[yellow]Warning:[/yellow] Config file already exists: {config_path}"
        )
        console.print("Use --force to overwrite")
        raise typer.Exit(code=1)

    try:
        created_path = config_loader.create_sample_config()
        console.print(f"[green]✓[/green] Created config file: {created_path}")
        console.print("\nEdit the file to customize orchestrator behavior.")

    except Exception as e:
        console.print(f"[red]Error:[/red] Failed to create config: {e}")
        raise typer.Exit(code=30)


@app.command("show")
def show(
    show_defaults: bool = typer.Option(
        False,
        "--defaults",
        "-d",
        help="Show default values for unset options",
    ),
):
    """Show current configuration.

    Displays the merged configuration from .nh.toml and environment
    variables with precedence applied.

    Examples:

        nh config show              # Show current config

        nh config show --defaults   # Include default values
    """
    # Get repo root
    repo_root = Path.cwd().parent if Path.cwd().name == "orchestrator" else Path.cwd()
    orchestrator_root = repo_root / "orchestrator"

    try:
        config = get_config(orchestrator_root)

        console.print("\n[bold]Current Configuration[/bold]\n")

        # Orchestrator settings
        console.print("[cyan]Orchestrator:[/cyan]")
        console.print(f"  default_model: {config.orchestrator.default_model}")
        console.print(f"  max_parallel_jobs: {config.orchestrator.max_parallel_jobs}")
        console.print(
            f"  enable_rate_limiting: {config.orchestrator.enable_rate_limiting}"
        )
        console.print(f"  approval_mode: {config.orchestrator.approval_mode}")

        # Paths
        console.print("\n[cyan]Paths:[/cyan]")
        console.print(f"  repo_root: {config.paths.repo_root or '(default: cwd)'}")
        console.print(f"  data_dir: {config.paths.data_dir or '(default: data/)'}")
        console.print(f"  logs_dir: {config.paths.logs_dir or '(default: logs/)'}")

        # Registry
        console.print("\n[cyan]Registry:[/cyan]")
        console.print(f"  backend: {config.registry.backend}")
        console.print(f"  sqlite_path: {config.registry.sqlite_path}")
        console.print(f"  tsv_path: {config.registry.tsv_path}")

        # Cloudflare
        console.print("\n[cyan]Cloudflare:[/cyan]")
        console.print(
            f"  api_token: {'(set)' if config.cloudflare.api_token else '(not set)'}"
        )
        console.print(
            f"  account_id: {config.cloudflare.account_id or '(not set)'}"
        )
        console.print(f"  project_name: {config.cloudflare.project_name}")

        # Show config file location
        config_loader = ConfigLoader(orchestrator_root)
        console.print(f"\n[dim]Config file: {config_loader.config_path}[/dim]")
        if config_loader.config_path.exists():
            console.print("[dim]Status: Loaded from file[/dim]")
        else:
            console.print("[dim]Status: Using defaults (no .nh.toml found)[/dim]")

    except Exception as e:
        console.print(f"[red]Error:[/red] Failed to load config: {e}")
        raise typer.Exit(code=10)


@app.command("validate")
def validate():
    """Validate configuration file.

    Checks .nh.toml for syntax errors and invalid values.

    Examples:

        nh config validate
    """
    # Get repo root
    repo_root = Path.cwd().parent if Path.cwd().name == "orchestrator" else Path.cwd()
    orchestrator_root = repo_root / "orchestrator"

    config_loader = ConfigLoader(orchestrator_root)

    if not config_loader.config_path.exists():
        console.print(
            f"[yellow]Warning:[/yellow] No config file found: {config_loader.config_path}"
        )
        console.print("Using default values. Run 'nh config init' to create one.")
        raise typer.Exit(code=0)

    try:
        # Try to load config
        config = config_loader.load(reload=True)

        console.print(f"\n[bold]Validating Configuration[/bold]")
        console.print(f"File: {config_loader.config_path}\n")

        # Perform validation checks
        errors = []

        # Check registry backend
        if config.registry.backend not in ("tsv", "sqlite"):
            errors.append(
                f"Invalid registry backend: {config.registry.backend} "
                "(must be 'tsv' or 'sqlite')"
            )

        # Check max parallel jobs
        if not (1 <= config.orchestrator.max_parallel_jobs <= 16):
            errors.append(
                f"Invalid max_parallel_jobs: {config.orchestrator.max_parallel_jobs} "
                "(must be 1-16)"
            )

        # Check approval mode
        valid_modes = ("yolo", "interactive", "conservative")
        if config.orchestrator.approval_mode not in valid_modes:
            errors.append(
                f"Invalid approval_mode: {config.orchestrator.approval_mode} "
                f"(must be one of {valid_modes})"
            )

        if errors:
            console.print("[red]✗[/red] Validation failed:\n")
            for error in errors:
                console.print(f"  - {error}")
            raise typer.Exit(code=10)
        else:
            console.print("[green]✓[/green] Configuration is valid")

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/red] Failed to parse config: {e}")
        raise typer.Exit(code=10)


@app.command("get")
def get_value(
    key: str = typer.Argument(..., help="Configuration key (e.g., orchestrator.default_model)"),
):
    """Get a specific configuration value.

    Examples:

        nh config get orchestrator.default_model

        nh config get registry.backend
    """
    # Get repo root
    repo_root = Path.cwd().parent if Path.cwd().name == "orchestrator" else Path.cwd()
    orchestrator_root = repo_root / "orchestrator"

    try:
        config = get_config(orchestrator_root)

        # Parse key
        parts = key.split(".")
        if len(parts) != 2:
            console.print(f"[red]Error:[/red] Invalid key format: {key}")
            console.print("Expected format: section.key (e.g., orchestrator.default_model)")
            raise typer.Exit(code=10)

        section, field = parts

        # Get value
        if section == "orchestrator":
            value = getattr(config.orchestrator, field, None)
        elif section == "paths":
            value = getattr(config.paths, field, None)
        elif section == "registry":
            value = getattr(config.registry, field, None)
        elif section == "cloudflare":
            value = getattr(config.cloudflare, field, None)
        else:
            console.print(f"[red]Error:[/red] Unknown section: {section}")
            console.print("Valid sections: orchestrator, paths, registry, cloudflare")
            raise typer.Exit(code=10)

        if value is None:
            console.print(f"[yellow]Warning:[/yellow] {key} is not set")
        else:
            console.print(value)

    except AttributeError:
        console.print(f"[red]Error:[/red] Unknown key: {key}")
        raise typer.Exit(code=10)
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=10)
