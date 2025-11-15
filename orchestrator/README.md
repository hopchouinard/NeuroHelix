# NeuroHelix Python Orchestrator

Python-based orchestrator for the NeuroHelix automated AI research pipeline. This replaces the Bash-based orchestrator with a robust, testable, and maintainable Typer CLI application.

## Status

**Current Phase:** Initial Implementation (Feature Branch)

### Completed
- ✅ Project structure and packaging (Poetry/uv)
- ✅ Pydantic models for configuration and registry
- ✅ TSV registry loader with validation
- ✅ Filesystem utilities (locking, hashing, paths)
- ✅ Manifest and dependency tracking
- ✅ Ledger and audit logging
- ✅ Gemini CLI adapter with retries
- ✅ Runner service with concurrency pools
- ✅ Typer CLI app with command modules

### In Progress
- 🔄 Documentation and usage guides
- 🔄 Test suite (unit and integration)

### Pending
- ⏳ LaunchD automation service
- ⏳ Full implementation of maintenance commands
- ⏳ Migration parity harness
- ⏳ Production deployment

## Requirements

- Python 3.14.0+
- Poetry 2.2.1 or uv 0.9.9
- Gemini CLI (for execution)
- pnpm (for static site publishing)

## Installation

### Development Setup

```bash
# Navigate to orchestrator directory
cd orchestrator

# Install dependencies with Poetry
poetry install

# Or use uv (faster alternative)
uv sync

# Activate virtual environment
poetry shell  # or: source .venv/bin/activate
```

### Verify Installation

```bash
# Check all required binaries and environment
nh diag

# Validate prompt registry
nh registry validate
```

## Usage

### Basic Commands

```bash
# Run daily pipeline for today
nh run

# Run for specific date
nh run --date 2025-11-14

# Run specific wave only
nh run --wave search

# Force rerun of specific prompt or wave
nh run --force prompt_id
nh run --force search

# Dry run (preview without executing)
nh run --dry-run
```

### Registry Management

```bash
# Validate prompt registry
nh registry validate

# Validate with specific format
nh registry validate --format tsv
```

### Maintenance Commands

```bash
# Clean up old artifacts (90 day retention)
nh cleanup

# Custom retention period
nh cleanup --keep-days 30

# Preview cleanup
nh cleanup --dry-run

# Reprocess specific date
nh reprocess 2025-11-14

# Publish to Cloudflare
nh publish 2025-11-14
```

### Automation Management

```bash
# Install LaunchD automation
nh automation install

# Check automation status
nh automation status

# Remove automation
nh automation remove
```

### Diagnostics

```bash
# Human-readable diagnostics
nh diag

# JSON output for scripting
nh diag --json
```

## Architecture

### Project Structure

```
orchestrator/
├── nh_cli/                 # Typer CLI application
│   ├── main.py            # Main app entry point
│   └── commands/          # Command modules
│       ├── run.py         # Pipeline execution
│       ├── registry.py    # Registry validation
│       ├── diag.py        # Diagnostics
│       ├── cleanup.py     # Cleanup operations
│       ├── reprocess.py   # Reprocessing
│       ├── publish.py     # Publishing
│       └── automation.py  # LaunchD management
├── services/              # Core services
│   ├── registry.py        # Registry loading/validation
│   ├── runner.py          # Wave scheduling & execution
│   ├── manifest.py        # Dependency tracking
│   └── ledger.py          # Telemetry & logging
├── adapters/              # External integrations
│   ├── gemini_cli.py      # Gemini CLI wrapper
│   └── filesystem.py      # File operations & locking
├── config/                # Configuration
│   ├── prompts.tsv        # Prompt registry (TSV format)
│   └── settings_schema.py # Pydantic models
└── tests/                 # Test suite
    ├── unit/              # Unit tests
    ├── integration/       # Integration tests
    └── fixtures/          # Test fixtures
```

### Key Components

#### Registry System

The prompt registry (`config/prompts.tsv`) defines execution policies for each prompt:

- **prompt_id**: Unique identifier
- **title**: Human-readable name
- **wave**: Pipeline wave (search, aggregator, tagger, render, export, publish)
- **category**: Grouping category
- **model**: Gemini model to use
- **temperature**: Temperature setting
- **timeout_sec**: Timeout in seconds
- **max_retries**: Maximum retry attempts
- **concurrency_class**: Concurrency level (sequential, low, medium, high)
- **expected_outputs**: Output file pattern

#### Wave System

Prompts execute in six waves with dependency tracking:

1. **search** - Individual research prompts
2. **aggregator** - Synthesize search outputs
3. **tagger** - Extract metadata
4. **render** - Generate HTML dashboard
5. **export** - Create JSON payload
6. **publish** - Deploy to Cloudflare

#### Telemetry & Logging

Three-tier logging system:

1. **Run Logs** (`logs/runs/YYYY-MM-DD.log`) - Human-readable execution logs
2. **Ledger** (`logs/ledger/YYYY-MM-DD.jsonl`) - Structured execution metadata
3. **Audit Log** (`logs/audit/YYYY-MM-DD.jsonl`) - Maintenance operations

#### Safety Rails

- **Locking**: Single-run enforcement with TTL-based stale lock cleanup
- **Completion Markers**: Hash-verified idempotency (`.nh_status_*.json`)
- **Dry Run**: Preview mode for all commands
- **Force Flags**: Selective rerun capabilities
- **Exit Codes**: Standardized for CI/CD integration

## Configuration

### Prompt Registry Format

TSV file with tab-separated columns:

```tsv
prompt_id	title	wave	category	model	tools	temperature	token_budget	timeout_sec	max_retries	concurrency_class	expected_outputs	notes
ai_ecosystem_watch	AI Ecosystem Watch	search	Research	gemini-2.5-pro		0.7	32000	120	3	high	ai_ecosystem_watch.md	Track AI announcements
```

### Environment Variables

```bash
# Default Gemini model
export NH_DEFAULT_MODEL=gemini-2.5-pro

# Cloudflare API token
export CLOUDFLARE_API_TOKEN=your_token

# Repository root (optional, auto-detected)
export NH_REPO_ROOT=/path/to/neurohelix
```

### Configuration File

Optional `.nh.toml` in repo root:

```toml
[settings]
default_model = "gemini-2.5-pro"
max_parallel_jobs = 4
enable_static_site_publishing = true
cloudflare_project_name = "neurohelix-site"
lock_ttl_seconds = 7200
cleanup_keep_days = 90
```

## Development

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov

# Run specific test file
poetry run pytest tests/unit/test_registry.py
```

### Code Quality

```bash
# Format with Black
poetry run black .

# Lint with Ruff
poetry run ruff check .

# Type check with mypy
poetry run mypy .
```

### Adding a New Command

1. Create module in `nh_cli/commands/`
2. Define Typer app and command functions
3. Register in `nh_cli/main.py`
4. Write tests in `tests/unit/`

Example:

```python
# nh_cli/commands/mycommand.py
import typer
app = typer.Typer()

@app.command()
def main():
    """Command description."""
    pass

# nh_cli/main.py
from nh_cli.commands import mycommand
app.add_typer(mycommand.app, name="mycommand")
```

## Telemetry Outputs

### Run Manifest

`data/manifests/YYYY-MM-DD.json`:

```json
{
  "run_id": "uuid",
  "date": "2025-11-14",
  "started_at": "2025-11-14T07:00:00",
  "ended_at": "2025-11-14T07:15:00",
  "completed_prompts": ["prompt1", "prompt2"],
  "failed_prompts": [],
  "dry_run": false
}
```

### Completion Marker

`.nh_status_prompt_name.json`:

```json
{
  "prompt_id": "ai_ecosystem_watch",
  "started_at": "2025-11-14T07:00:00",
  "ended_at": "2025-11-14T07:02:00",
  "exit_code": 0,
  "retries": 0,
  "sha256": "abc123..."
}
```

### Ledger Entry

`logs/ledger/YYYY-MM-DD.jsonl` (one line per prompt):

```json
{"run_id": "uuid", "prompt_id": "ai_ecosystem_watch", "started_at": "...", "success": true, ...}
```

## Migration from Bash

The Python orchestrator maintains compatibility with existing data structures:

- Same directory layouts (`data/outputs/daily/`, etc.)
- Same file naming conventions
- Same manifest formats for downstream consumers
- Backward-compatible with existing scripts

### Comparison

| Feature | Bash | Python |
|---------|------|--------|
| Execution | Shell scripts | Typer CLI |
| Concurrency | Parallel jobs | ThreadPoolExecutor |
| Retry Logic | Basic | Exponential backoff |
| Logging | Text files | Structured JSONL + text |
| Locking | flock | fcntl with TTL |
| Validation | None | Pydantic schemas |
| Testing | Manual | Automated unit/integration |
| Telemetry | Basic | Comprehensive |

## Troubleshooting

### Lock Errors

If you get "Lock already held" errors:

```bash
# Check lock status
ls -la var/locks/

# Remove stale lock (careful!)
rm var/locks/nh-run.lock

# Or use force flag (not recommended during active runs)
nh run --force
```

### Registry Validation Failures

```bash
# Validate registry
nh registry validate

# Check for common issues:
# - Duplicate prompt_id values
# - Missing required columns
# - Invalid wave names
# - Temperature > 1.0 with tools enabled
```

### Missing Dependencies

```bash
# Check diagnostics
nh diag

# Install missing binaries
# - gemini: Install from Google
# - pnpm: brew install pnpm
# - wrangler: npm install -g wrangler
```

## Exit Codes

- `0` - Success
- `10` - Configuration/validation error
- `20` - Dependency missing or lock held
- `30` - External tool failure

## Contributing

1. Work on feature branches
2. Follow TDD: write tests before implementation
3. Use Black for formatting
4. Ensure mypy passes
5. Update documentation

## License

Part of the NeuroHelix project.
