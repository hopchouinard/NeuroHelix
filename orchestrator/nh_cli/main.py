"""Main Typer CLI application for NeuroHelix orchestrator."""

import typer
from rich.console import Console

from nh_cli.commands import (
    automation,
    cleanup,
    compare,
    config,
    diag,
    publish,
    registry,
    reprocess,
    run,
)

# Create console for rich output
console = Console()

# Create main Typer app
app = typer.Typer(
    name="nh",
    help="NeuroHelix orchestrator CLI - Automated AI research pipeline",
    add_completion=False,
)

# Add command modules
app.add_typer(run.app, name="run", help="Execute daily pipeline")
app.add_typer(reprocess.app, name="reprocess", help="Rebuild artifacts for a past day")
app.add_typer(cleanup.app, name="cleanup", help="Remove temporary files and stale locks")
app.add_typer(publish.app, name="publish", help="Trigger export and Cloudflare deploy")
app.add_typer(automation.app, name="automation", help="Manage LaunchD automation")
app.add_typer(registry.app, name="registry", help="Validate and inspect prompt registry")
app.add_typer(config.app, name="config", help="Manage .nh.toml configuration")
app.add_typer(diag.app, name="diag", help="Print diagnostics and system status")
app.add_typer(compare.app, name="compare", help="Compare Bash vs Python outputs")


@app.callback()
def main_callback():
    """NeuroHelix orchestrator - Automated AI research pipeline."""
    pass


if __name__ == "__main__":
    app()
