# NeuroHelix AI Agent Instructions

## System Overview

NeuroHelix is a **dual-orchestrator AI research automation pipeline** that executes 22 curated research prompts daily, synthesizes findings with Gemini, and publishes interactive dashboards + raw source archives to Cloudflare Pages.

**Core Architecture:**

- **Execution Layer:** Bash orchestrator (`scripts/orchestrator.sh`) OR modern Python CLI (`orchestrator/`, Typer + Poetry)
- **Intelligence:** Google Gemini API via `gemini` CLI
- **Publishing:** Astro 5 static site with MiniSearch, dual-view dashboards (processed + raw source explorer)
- **Automation:** LaunchD (macOS) for daily 7 AM runs

## Critical Development Workflows

### Running the Pipeline

**Bash orchestrator (legacy, still primary):**

```bash
./scripts/orchestrator.sh                          # Normal daily run (6-step pipeline)
./scripts/orchestrator.sh --reprocess-today        # Force rerun today's data with operator audit trail
./scripts/orchestrator.sh --cleanup-all --dry-run  # Preview full workspace reset
```

**Python orchestrator (modern alternative, production-ready):**

```bash
cd orchestrator
poetry install && poetry shell                     # First-time setup
nh run                                             # Run daily pipeline
nh run --date 2025-11-15 --wave search             # Run specific date/wave
nh registry validate                               # Check prompt registry
nh config show                                     # Display merged configuration
```

### Static Site Development

```bash
cd site
pnpm install                                       # Install dependencies
pnpm prebuild                                      # Run ingestion + search index manually
pnpm dev                                           # Local dev server (localhost:4321)
pnpm build                                         # Production build (triggers prebuild)
pnpm astro check                                   # Validate content collections
```

### Testing Changes

```bash
# Bash pipeline smoke tests
bash tests/test_telemetry.sh
bash tests/test_context_aware_prompts.sh

# Python orchestrator unit tests
cd orchestrator && poetry run pytest -v --cov

# Site validation
cd site && pnpm astro check
```

## Project-Specific Conventions

### Bash Scripts (`scripts/`)

- **ALWAYS** start with `#!/usr/bin/env bash` and `set -euo pipefail`
- Use `snake_case` for functions and variables
- Source `config/env.sh` and helper libs (`scripts/lib/*.sh`) at top
- Shared utilities live in `scripts/lib/` (audit, telemetry, git safety, cleanup)
- **Never hardcode paths** – use `${PROJECT_ROOT}`, `${DATA_DIR}`, etc.

**Example pattern:**

```bash
#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${PROJECT_ROOT}/config/env.sh"
source "${PROJECT_ROOT}/scripts/lib/telemetry.sh"

TODAY=$(date +%Y-%m-%d)
OUTPUT_DIR="${DATA_DIR}/outputs/daily/${TODAY}"
mkdir -p "${OUTPUT_DIR}"
```

### Python Code (`orchestrator/`)

- **Type hints everywhere** – use Pydantic models for configuration, registry schemas, and telemetry
- **Line length:** 100 characters max
- **Code quality:** Black (formatter), Ruff (linter), mypy `--strict` (type checker)
- **Naming:** `snake_case` for functions/variables, `PascalCase` for classes/services
- **Typer commands:** File names match verbs (`run.py`, `registry.py`, `config.py`)
- **Error handling:** Exit codes: 0 (success), 10 (validation), 20 (dependency/lock), 30 (external tool failure)

**Example pattern:**

```python
from pydantic import BaseModel, Field
from pathlib import Path
from typing import Literal

class PromptConfig(BaseModel):
    """Prompt registry entry with execution policy."""
    prompt_id: str = Field(..., min_length=1)
    wave: Literal["search", "aggregator", "tagger", "render", "export", "publish"]
    model: str = "gemini-2.5-pro"
    timeout_sec: int = Field(120, ge=30)
```

### Astro/TypeScript Site (`site/`)

- **Component files:** `PascalCase.astro` (e.g., `DashboardCard.astro`)
- **Helper modules:** Named exports in `.ts` files, `camelCase` functions
- **Styles:** Co-locate tokens in `src/styles/`, leverage Tailwind 4 utilities
- **Client scripts:** Use `.client.ts` suffix for browser-only code (search, filters)

## Data Flow & Integration Points

### Pipeline Stages (6-Step Flow)

1. **Prompt Execution** → `data/outputs/daily/YYYY-MM-DD/*.md`
   - Reads `config/searches.tsv` (22 prompts)
   - Context-aware prompts inject historical data (Novelty Filter, Continuity Builder)
   - Telemetry: `logs/prompt_execution_*.log` + `data/runtime/execution_ledger_*.json`
2. **Aggregation** → `data/reports/daily_report_YYYY-MM-DD.md`
   - Synthesizes cross-domain findings via Gemini
   - **Critical:** Enforces strict h3 (`###`) section structure for downstream parsing
3. **Tag Extraction** → `data/publishing/tags_YYYY-MM-DD.json`
   - AI-powered keyword + category extraction
4. **Dashboard Generation** → `dashboards/dashboard_YYYY-MM-DD.html`
   - Self-contained HTML (legacy output)
5. **Site Payload Export** → `data/publishing/YYYY-MM-DD.json`
   - Structured JSON consumed by Astro ingestion
   - Source manifest → `data/publishing/source_manifests/*.json`
6. **Static Site Publishing** → Cloudflare Pages
   - `site/scripts/ingest.mjs` → Astro content collections
   - `site/scripts/build-search-index.mjs` → MiniSearch index
   - Deploys via Wrangler CLI

### Critical File Contracts

**DO NOT break these data structures:**

- **Completion markers:** `.execution_complete` in daily output dirs enables idempotency
- **Ledger format:** `execution_ledger_*.json` must have `summary` object with counts/durations
- **Synthesis sections:** Daily reports MUST use h3 (`###`) headings with exact names:
  - `### Executive Summary`, `### Key Themes & Insights`, `### Notable Developments`, etc.
  - Export script parses these to build JSON payloads; h2/h4 breaks site rendering
- **Manifest schema:** Source manifests require `artifactType`, `displayGroup`, `checksum`, `preview`, `toc`

## Configuration & Secrets

### Bash Orchestrator

- **Main config:** `config/env.sh` (gitignored)
- **Template:** `config/env.EXAMPLE.sh` (committed)
- **Prompts:** `config/searches.tsv` (tab-separated, human-editable)
- **Secrets:** `CLOUDFLARE_API_TOKEN` in `.env.local` (gitignored)

### Python Orchestrator

- **Primary config:** `.nh.toml` in `orchestrator/` directory (optional, gitignored)
- **Precedence:** CLI flags > .nh.toml > Environment variables > Defaults
- **Registry backends:** TSV (`config/prompts.tsv`) OR SQLite (`config/prompts.db`)
- **Sample generation:** `nh config init` creates `.nh.toml` template

**Never commit:**

- `config/env.sh`
- `.env.local`
- `.nh.toml`
- `config/prompts.db` (if using SQLite)

## Maintenance & Safety Rails

### Idempotency Design

- **Prompt execution:** Creates `.execution_complete` marker; re-runs skip if exists (<1s completion)
- **Aggregation:** Checks for `## End of Report` marker in existing reports
- **Force rerun:** `--reprocess-today` deletes today's markers + data, then reruns with audit trail

### Git Safety

- Maintenance modes (`--cleanup-all`, `--reprocess-today`) **require clean working tree** by default
- Override with `--allow-dirty` flag
- LaunchD **cannot invoke** maintenance modes (operator-only)

### Pipeline Locking

- Bash: Uses `flock` on `var/locks/nh-run.lock`
- Python: Uses `fcntl` with TTL-based stale lock cleanup
- `--allow-abort` terminates running pipeline gracefully (SIGTERM → SIGKILL)

### Audit Trail

All maintenance operations log to:

- **Text logs:** `logs/maintenance/{cleanup,reprocess}_*.log`
- **JSONL audit:** `data/runtime/audit.jsonl` (structured, timestamped, operator-tagged)

## Testing Patterns

### Bash Tests (`tests/`)

- **Smoke tests:** `test_telemetry.sh`, `test_context_aware_prompts.sh`
- Run before merging changes to `scripts/orchestrator.sh` or `scripts/lib/*.sh`

### Python Tests (`orchestrator/tests/`)

- **Target:** ≥90% coverage
- **Structure:** `unit/` and `integration/` subdirs
- **Naming:** `test_<subject>.py` (e.g., `test_registry.py`)
- **Fixtures:** Use `tests/fixtures/` to isolate registry/data dependencies

### Site Tests

- **Content validation:** `pnpm astro check` validates content collections
- **Manual QA:** `pnpm prebuild && pnpm dev` → spot-check dashboards/search/filters

## Common Pitfalls

### Markdown Structure Must Match Parser

**Problem:** Export script fails silently if synthesis uses wrong heading levels.

**Solution:** Synthesis prompt template (`scripts/aggregators/aggregate_daily.sh` lines 212-292) enforces h3 (`###`) headings. When adding new sections, update both the prompt AND `scripts/renderers/export_site_payload.sh` skip logic.

### Context-Aware Prompts Need Manual Wiring

**Problem:** Adding temporal context to a new prompt doesn't work automatically.

**Solution:** Edit `scripts/executors/run_prompts.sh` around line 58, add case statement for your prompt's domain, inject historical data via `cat` or heredoc.

### Python/Bash Orchestrators Have Different Flags

**Bash:** `--cleanup-all`, `--reprocess-today`, `--dry-run`, `--yes`, `--allow-dirty`  
**Python:** `--date`, `--wave`, `--force`, `--dry-run`, `--backend sqlite`

Check `nh --help` vs `./scripts/orchestrator.sh` usage comments for differences.

### Search Index Must Rebuild After Data Changes

**Problem:** New dashboards don't appear in search.

**Solution:** `cd site && pnpm prebuild` (or `node scripts/build-search-index.mjs`) before `pnpm dev`. Production builds auto-run prebuild via package.json script.

## Key Files to Reference

- **Pipeline orchestration:** `scripts/orchestrator.sh` (Bash), `orchestrator/nh_cli/commands/run.py` (Python)
- **Telemetry system:** `scripts/lib/telemetry.sh` (logging, ledgers, audit)
- **Synthesis logic:** `scripts/aggregators/aggregate_daily.sh` (prompt template + markdown structure)
- **Site ingestion:** `site/scripts/ingest.mjs` (JSON → Astro content collection converter)
- **Search indexing:** `site/scripts/build-search-index.mjs` (MiniSearch builder)
- **Config schemas:** `orchestrator/config/settings_schema.py` (Pydantic models)
- **Source explorer:** `site/src/components/source/FileTree.astro`, `RawViewer.astro`

## Quick Reference Commands

```bash
# Daily pipeline (Bash)
./scripts/orchestrator.sh

# Daily pipeline (Python)
cd orchestrator && poetry run nh run

# Force today's reprocess
./scripts/orchestrator.sh --reprocess-today

# Full workspace reset (preview)
./scripts/orchestrator.sh --cleanup-all --dry-run

# Migrate TSV registry to SQLite
cd orchestrator && poetry run nh registry migrate

# Validate prompt registry
cd orchestrator && poetry run nh registry validate

# Site development
cd site && pnpm prebuild && pnpm dev

# Deploy to Cloudflare
./scripts/publish/static_site.sh

# Check automation status
launchctl list | grep neurohelix

# View today's outputs
cat data/reports/daily_report_$(date +%Y-%m-%d).md
open dashboards/dashboard_$(date +%Y-%m-%d).html
```

## Need Help?

- **Bash orchestrator:** `CLAUDE.md` has detailed command reference and troubleshooting
- **Python orchestrator:** `orchestrator/README.md` has complete CLI documentation
- **Site architecture:** `site/README.md` explains dual-view system and data flow
- **Setup guides:** `docs/automation-setup.md`, `docs/context-aware-prompts.md`
- **Implementation logs:** `ai_dev_logs/*.md` capture feature development history
