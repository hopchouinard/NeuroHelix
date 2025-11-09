# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

NeuroHelix is an automated AI research system that runs daily cycles of discovery, synthesis, and ideation. The system executes 22 curated research prompts, synthesizes findings using AI, and publishes results to a static website via Cloudflare Pages.

**Tech Stack:**
- **Execution:** Bash scripts orchestrating Gemini CLI
- **Intelligence:** Google Gemini API (gemini-2.5-pro model)
- **Frontend:** Astro 5 + Tailwind CSS 4 static site
- **Search:** MiniSearch client-side search with fuzzy matching
- **Deployment:** Cloudflare Pages via Wrangler
- **Automation:** LaunchD (macOS) for daily scheduling

## Development Commands

### Running the Pipeline

```bash
# Run full pipeline (6-step process)
./scripts/orchestrator.sh

# Run individual steps
./scripts/executors/run_prompts.sh          # Step 1: Execute 22 research prompts
./scripts/aggregators/aggregate_daily.sh    # Step 2: Aggregate into daily report
./scripts/aggregators/extract_tags.sh       # Step 2.5: AI tag extraction
./scripts/renderers/generate_dashboard.sh   # Step 3: Generate HTML dashboard
./scripts/renderers/export_site_payload.sh  # Step 4: Export JSON for static site
./scripts/publish/static_site.sh            # Step 5: Build & deploy to Cloudflare
```

### Static Site Development

```bash
cd site

# Install dependencies
pnpm install

# Run data ingestion (reads ../data/publishing/*.json)
node scripts/ingest.mjs
node scripts/build-search-index.mjs

# Local development server
pnpm run dev                # Visit http://localhost:4321

# Production build
pnpm run build             # Triggers prebuild: ingest + search index
pnpm run preview           # Preview production build locally

# Deploy to Cloudflare Pages
cd ..
./scripts/publish/static_site.sh  # Requires CLOUDFLARE_API_TOKEN in .env.local
```

### LaunchD Automation Management

```bash
# Install daily automation (runs at 7 AM)
./install_automation.sh

# Check automation status
launchctl list | grep neurohelix

# Manual trigger
launchctl start com.neurohelix.daily

# View logs
tail -f logs/launchd_stdout.log
tail -f logs/launchd_stderr.log
tail -f logs/publishing/publish_*.log

# Uninstall automation
./uninstall_automation.sh
```

### Viewing Outputs

```bash
# Today's outputs
TODAY=$(date +%Y-%m-%d)
cat data/reports/daily_report_${TODAY}.md
open dashboards/dashboard_${TODAY}.html
cat data/publishing/${TODAY}.json

# Execution telemetry
cat data/runtime/execution_ledger_${TODAY}.json
cat logs/prompt_execution_${TODAY}.log
```

## Architecture

### Pipeline Flow (orchestrator.sh)

The system follows a 6-step pipeline:

1. **Prompt Execution** (`scripts/executors/run_prompts.sh`)
   - Reads 22 prompts from `config/searches.tsv`
   - Supports parallel execution (4 jobs default) or sequential
   - Context-aware prompts inject historical data for specific domains:
     - **Novelty Filter:** Gets yesterday's Concept Synthesizer output
     - **Continuity Builder:** Gets last 7 days of daily reports
     - **Meta-Project Explorer:** Gets system structure info
   - Non-blocking failures with telemetry tracking
   - Outputs: `data/outputs/daily/YYYY-MM-DD/*.md`

2. **Aggregation** (`scripts/aggregators/aggregate_daily.sh`)
   - Combines all domain outputs into single document
   - Creates synthesis prompt with detailed requirements
   - Uses Gemini CLI to generate cross-domain analysis
   - Outputs: `data/reports/daily_report_YYYY-MM-DD.md`

3. **Tag Extraction** (`scripts/aggregators/extract_tags.sh`)
   - Reads daily report and extracts metadata using AI
   - Generates tags (5-8 keywords) and categories
   - Outputs: `data/publishing/tags_YYYY-MM-DD.json`

4. **Dashboard Generation** (`scripts/renderers/generate_dashboard.sh`)
   - Creates self-contained HTML with embedded CSS
   - Outputs: `dashboards/dashboard_YYYY-MM-DD.html`

5. **Site Payload Export** (`scripts/renderers/export_site_payload.sh`)
   - Parses markdown report into structured sections
   - Merges with tags and categories
   - Outputs: `data/publishing/YYYY-MM-DD.json`

6. **Static Site Publishing** (`scripts/publish/static_site.sh`)
   - Runs ingestion scripts to convert JSON to Astro content
   - Builds Astro site with search index
   - Deploys to Cloudflare Pages via Wrangler
   - Logs: `logs/publishing/publish_*.log`

### Idempotency Design

The pipeline is designed to be safely re-run multiple times:

- **Prompt Execution:** Creates `.execution_complete` marker in `data/outputs/daily/YYYY-MM-DD/`. Re-runs skip if marker exists (completes in <1s).
- **Aggregation:** Checks if report exists and contains "## End of Report" marker.
- **Publishing:** Always rebuilds site with latest data.

To force re-execution, delete the completion markers.

### Telemetry System (`scripts/lib/telemetry.sh`)

Comprehensive execution tracking:

- **Telemetry Log:** Human-readable text log at `logs/prompt_execution_YYYY-MM-DD.log`
- **Execution Ledger:** Structured JSON at `data/runtime/execution_ledger_YYYY-MM-DD.json`
- **Metrics Tracked:** Start time, end time, duration, status (success/failure), error messages
- **Summary Statistics:** Total prompts, successful count, failed count, total duration

Functions available:
- `init_telemetry_log <date>` - Initialize log file
- `init_execution_ledger <date>` - Initialize JSON ledger
- `log_prompt_start <name> <category> <stage>` - Log execution start
- `log_prompt_end <name> <category> <stage> <status> [error]` - Log completion
- `add_to_ledger <name> <category> <stage> <start> <end> <status> <file> [error]` - Add JSON entry
- `finalize_ledger_summary` - Calculate and update summary statistics

### Static Site Architecture

**Data Flow:**
```
data/publishing/*.json → ingestion → src/content/dashboards/*.md → Astro build → dist/
```

**Key Components:**

1. **Ingestion** (`site/scripts/ingest.mjs`)
   - Reads JSON payloads from `../data/publishing/`
   - Converts to Astro content collection format (frontmatter + markdown)
   - Generates tag frequencies and category mappings
   - Outputs: `src/content/dashboards/*.md`, `src/data/{tags,tag-frequencies,categories,stats}.json`
   - Cleanup: Removes stale markdown files with no corresponding JSON

2. **Search Index** (`site/scripts/build-search-index.mjs`)
   - Builds MiniSearch index from all dashboard content
   - Indexes: title, summary, sections, tags, categories
   - Outputs: `public/search-index.json`

3. **Content Collection** (`src/content/dashboards/`)
   - Astro content collection with schema validation
   - Each dashboard has: date, title, summary, tags, categories, sections, notable_developments, strategic_implications, recommendations

4. **Search Component** (`src/components/Search.astro`)
   - Client-side full-text search with MiniSearch
   - Fuzzy matching enabled
   - Instant results as you type

### Configuration Files

**`config/env.sh`** - Environment variables and feature flags:
```bash
GEMINI_MODEL="gemini-2.5-pro"           # AI model for research
GEMINI_APPROVAL_MODE="yolo"             # Auto-approve all actions
PARALLEL_EXECUTION="true"               # Parallel prompt execution
MAX_PARALLEL_JOBS="4"                   # Concurrency limit
ENABLE_STATIC_SITE_PUBLISHING="true"    # Enable Cloudflare deployment
CLOUDFLARE_PROJECT_NAME="neurohelix-site"
```

**`config/searches.tsv`** - Research prompts configuration:
- 22 prompts across 5 categories (Research, Market, Ideation, Analysis, Meta)
- Tab-separated format: `domain \t category \t prompt \t priority \t enabled`
- Context-aware prompts reference file paths for dynamic data injection

**`.env.local`** - Cloudflare credentials (not in git):
```bash
CLOUDFLARE_API_TOKEN=your_token_here
```

## Important Development Notes

### Gemini CLI Integration

The system uses Google's Gemini CLI (`gemini` command) with specific flags:
- **Non-interactive mode:** Prompts passed as positional arguments
- **stdin closed:** `< /dev/null` prevents hanging on input
- **Timeout handling:** 120-second timeout with graceful kill
- **Error handling:** Non-zero exit codes logged to telemetry

### Context-Aware Prompts

Three prompts have special context injection in `run_prompts.sh`:

1. **Novelty Filter** - Appends yesterday's `concept_synthesizer.md` to prompt
2. **Continuity Builder** - Appends last 7 days of reports (first 200 lines each)
3. **Meta-Project Explorer** - Appends system structure and recent report filenames

When adding new context-aware prompts, add case statement in `run_prompts.sh` around line 58.

### Failure Handling

- **Non-blocking failures:** Individual prompt failures don't stop pipeline
- **Telemetry tracking:** All failures logged with error messages
- **Email notifications:** Optional failure notifications (`scripts/notifiers/notify_failures.sh`)
- **Partial completion:** Pipeline marks as complete even with failures

### Markdown Structure Constraints

**Critical:** The synthesis prompt in `aggregate_daily.sh` enforces a strict markdown structure to ensure consistent parsing by downstream scripts.

**Required structure:**
```markdown
### Executive Summary
### Key Themes & Insights
### Model & Technology Advances
### Market Dynamics & Business Strategy
### Regulatory & Policy Developments
### Developer Tools & Ecosystem
### Hardware & Compute Landscape
### Notable Developments
### Strategic Implications
### Actionable Recommendations
```

**Key constraints:**
- All main sections MUST use h3 (`###`) headings - never h2 (`##`) or h4 (`####`)
- Section names must match exactly as shown above
- Notable Developments must be a bullet list (`*`)
- Actionable Recommendations must be a numbered list (`1.`)

**Why this matters:** The export script (`scripts/renderers/export_site_payload.sh`) parses the markdown to extract structured JSON for the static site. It uses an associative array to skip metadata sections (Executive Summary, Key Themes, etc.) and extracts only the thematic sections (Model & Technology Advances, Market Dynamics, etc.). Inconsistent heading levels or names break the site rendering.

**If synthesis produces wrong structure:**
1. Check the synthesis prompt template (line 212-292 in `aggregate_daily.sh`)
2. Verify the Gemini model is following instructions (try `gemini-2.5-pro` instead of `gemini-2.5-flash`)
3. Review the export script's skip logic (lines 70-77 in `export_site_payload.sh`)

### Testing Changes

**After modifying prompts:**
```bash
# Delete completion marker to force re-execution
rm data/outputs/daily/$(date +%Y-%m-%d)/.execution_complete
./scripts/executors/run_prompts.sh
```

**After modifying aggregation:**
```bash
# Delete report to force regeneration
rm data/reports/daily_report_$(date +%Y-%m-%d).md
./scripts/aggregators/aggregate_daily.sh
```

**After modifying site code:**
```bash
cd site
pnpm run build  # Test build locally
cd ..
./scripts/publish/static_site.sh  # Full deployment
```

### Working with Historical Data

Reports and outputs are organized by date:
```
data/
├── outputs/daily/YYYY-MM-DD/  # 22 individual prompt outputs
├── reports/                    # Synthesized daily reports
└── publishing/                 # JSON payloads for static site
```

To analyze patterns across days, use `grep` with date ranges or process multiple files in sequence.

## Common Tasks

### Add a new research prompt

1. Edit `config/searches.tsv` and add new row (tab-separated)
2. Test execution: `./scripts/executors/run_prompts.sh`
3. Verify output in `data/outputs/daily/YYYY-MM-DD/`

### Modify synthesis prompt

1. Edit synthesis template in `scripts/aggregators/aggregate_daily.sh` (line 212-292)
2. Delete existing report to force regeneration
3. Run: `./scripts/aggregators/aggregate_daily.sh`

**Important:** The synthesis prompt enforces a strict markdown structure with h3 (###) headings to ensure consistent parsing by the export script. If changing the structure, also update `scripts/renderers/export_site_payload.sh` section extraction logic (lines 60-115).

### Change LaunchD schedule

1. Edit `launchd/com.neurohelix.daily.plist` (Hour/Minute in StartCalendarInterval)
2. Reinstall: `./install_automation.sh`
3. Verify: `launchctl list | grep neurohelix`

### Customize site theme

Edit `site/src/styles/`:
- `global.css` - Base styles and Tailwind utilities
- Theme colors defined in Tailwind config (electric violet `#8b5cf6`)

### Debug failures

1. Check telemetry log: `cat logs/prompt_execution_$(date +%Y-%m-%d).log`
2. Check execution ledger: `cat data/runtime/execution_ledger_$(date +%Y-%m-%d).json`
3. Check LaunchD logs: `tail -f logs/launchd_stderr.log`
4. Check individual output files for error markers: `grep -r "Error:" data/outputs/daily/$(date +%Y-%m-%d)/`
