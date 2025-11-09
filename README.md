# 🧠 NeuroHelix

## Automated Research & Ideation Ecosystem

NeuroHelix is a **production-ready** AI-driven research automation system that runs daily cycles of discovery, synthesis, and ideation—orchestrated by Bash scripts and powered by Gemini CLI. Results are published to a modern static website via Cloudflare Pages.

### 🎯 Core Concept

A self-contained, automated AI research lab where:
- **LaunchD provides scheduling** (macOS automation)
- **Gemini CLI provides intelligence** (research, analysis, synthesis)
- **Astro + Cloudflare provides publishing** (modern static site with search)
- **You provide direction** (research domains, iterative refinement)

Every morning, wake up to an intelligent synthesis dashboard published to your custom domain with cross-domain insights, thematic analysis, and actionable recommendations.

### ✨ Key Features

✅ **22 Curated Research Prompts** - 5 categories (Research, Market, Ideation, Analysis, Meta)
✅ **Intelligent Synthesis** - Cross-domain thematic analysis with AI-powered insights
✅ **Full Idempotency** - Re-runs complete in <1 second, safe for repeated execution
✅ **Context-Aware Prompts** - Historical analysis, temporal awareness, structured references
✅ **LaunchD Automation** - Daily scheduling at 7 AM (customizable)
✅ **Static Site Publishing** - Modern Astro-based site deployed to Cloudflare Pages
✅ **Full-Text Search** - MiniSearch-powered client-side search with fuzzy matching
✅ **Tag & Category Filtering** - Smart filtering with tag cloud and category pills
✅ **Automated Tag Extraction** - AI-generated tags and categories from daily reports
✅ **Beautiful Design** - Dark theme with electric violet accents, GitHub-style markdown
✅ **Comprehensive Logging** - Detailed execution traces and deployment logs
✅ **Maintenance Operations** - Workspace cleanup and force reprocess with audit trail
✅ **Pipeline Locking** - Safe concurrent execution prevention with graceful termination
✅ **Git Safety Checks** - Prevents destructive operations on dirty working trees  

### 📁 Project Structure

```
NeuroHelix/
├── config/
│   ├── env.sh              # Configuration & feature flags
│   └── searches.tsv        # 22 research prompts (5 categories)
├── scripts/
│   ├── orchestrator.sh     # Main pipeline coordinator (6-step process)
│   ├── lib/                # Shared libraries (audit, cleanup, git safety, etc.)
│   ├── executors/          # Prompt execution with context injection
│   ├── aggregators/        # Intelligent synthesis + tag extraction
│   ├── renderers/          # Dashboard generation + JSON export
│   ├── publish/            # Cloudflare Pages deployment
│   └── notifiers/          # Email notifications
├── site/                   # Astro static site (published to web)
│   ├── src/                # Components, layouts, pages
│   ├── scripts/            # Data ingestion + search index generation
│   └── public/             # Static assets (logo, search index)
├── launchd/
│   └── com.neurohelix.daily.plist  # Scheduling template
├── data/
│   ├── outputs/daily/      # Raw prompt outputs (by date)
│   ├── reports/            # Daily synthesized markdown reports
│   ├── publishing/         # JSON payloads for static site
│   └── runtime/            # Execution ledgers + audit trail (audit.jsonl)
├── dashboards/             # Legacy HTML dashboards
├── logs/
│   ├── maintenance/        # Cleanup & reprocess operation logs
│   ├── publishing/         # Cloudflare deployment logs
│   └── *.log               # Execution logs (orchestrator, prompt execution)
├── docs/                   # Setup guides and documentation
└── install_automation.sh   # LaunchD installer script
```

### 🚀 Quick Start

1. **Prerequisites:**
   - macOS system (for LaunchD automation)
   - [Gemini CLI](https://github.com/google-gemini/gemini-cli) installed and configured
   - [pnpm](https://pnpm.io/) installed (`npm install -g pnpm`)
   - [Node.js](https://nodejs.org/) 18+ installed
   - Bash 4.0+ (standard on macOS)

2. **Test the system:**
   ```bash
   ./scripts/orchestrator.sh
   ```

   This runs the full 6-step pipeline:
   - Execute 22 research prompts
   - Aggregate results into daily report
   - Extract tags and categories with AI
   - Generate HTML dashboard
   - Export JSON payload
   - Publish to Cloudflare Pages (if configured)

   **Maintenance operations:**
   ```bash
   ./scripts/orchestrator.sh --cleanup-all --dry-run      # Preview workspace cleanup
   ./scripts/orchestrator.sh --reprocess-today --dry-run  # Preview force reprocess
   ```

   See [Maintenance Operations](#-maintenance-operations) for details.

3. **View local results:**
   ```bash
   # Today's markdown report
   cat data/reports/daily_report_$(date +%Y-%m-%d).md
   
   # Today's HTML dashboard
   open dashboards/dashboard_$(date +%Y-%m-%d).html
   
   # Today's JSON payload (for static site)
   cat data/publishing/$(date +%Y-%m-%d).json
   ```

4. **Install daily automation:**
   ```bash
   ./install_automation.sh
   ```
   
   Sets up LaunchD job to run daily at 7:00 AM.

5. **Configure Cloudflare deployment (optional):**
   ```bash
   # Create .env.local with your Cloudflare API token
   cp .env.local.example .env.local
   nano .env.local  # Add: CLOUDFLARE_API_TOKEN=your_token_here
   
   # Reinstall automation to inject token
   ./install_automation.sh
   ```

6. **Check automation status:**
   ```bash
   launchctl list | grep neurohelix
   ```

### 🌐 Static Site & Publishing

NeuroHelix includes a modern static website built with Astro that showcases all your research dashboards with advanced features.

#### Features

- **Built with Astro 5** - Modern static site generator with optimal performance
- **Tailwind CSS 4** - Utility-first styling with custom dark theme
- **MiniSearch Integration** - Client-side full-text search with fuzzy matching
- **Tag Cloud** - Visual representation of all tags with frequency weighting
- **Category Filters** - Multi-select filtering by research categories
- **Responsive Design** - Mobile-first, works beautifully on all devices
- **GitHub-Style Markdown** - Beautiful typography with Fira Code and Inter fonts
- **Deep Linking** - Direct links to report sections via heading anchors
- **Accessibility** - WCAG AA compliant with keyboard navigation

#### Architecture

1. **Data Export** (`scripts/renderers/export_site_payload.sh`)
   - Parses daily markdown reports
   - Extracts structured sections (executive summary, themes, recommendations)
   - Merges with AI-generated tags and categories
   - Outputs JSON to `data/publishing/YYYY-MM-DD.json`

2. **Ingestion** (`site/scripts/ingest.mjs`)
   - Reads JSON payloads from `../data/publishing/`
   - Converts to Astro content collection format
   - Generates tag frequencies and category mappings
   - Creates site statistics (total dashboards, insights, etc.)

3. **Search Index** (`site/scripts/build-search-index.mjs`)
   - Builds MiniSearch index from all dashboard content
   - Outputs to `site/public/search-index.json`
   - Enables instant client-side search

4. **Deployment** (`scripts/publish/static_site.sh`)
   - Runs Astro build (triggers prebuild: ingest + search index)
   - Deploys to Cloudflare Pages via Wrangler
   - Verifies deployment status
   - Logs metrics (build time, bundle size, deploy URL)

#### Setup Cloudflare Publishing

1. **Get Cloudflare API Token**
   - Visit [Cloudflare Dashboard](https://dash.cloudflare.com/profile/api-tokens)
   - Create token with: `Account.Cloudflare Pages:Edit`

2. **Configure Token**
   ```bash
   cp .env.local.example .env.local
   nano .env.local
   # Add: CLOUDFLARE_API_TOKEN=your_token_here
   ```

3. **Create Cloudflare Pages Project**
   ```bash
   cd site
   npx wrangler pages project create neurohelix-site
   # Or create via Cloudflare Dashboard
   ```

4. **Configure Custom Domain (Optional)**
   - In Cloudflare Dashboard: Pages → Your Project → Custom Domains
   - Add your domain (e.g., `neurohelix.yourdomain.com`)

5. **Enable Publishing**
   ```bash
   # Already enabled by default in config/env.sh
   export ENABLE_STATIC_SITE_PUBLISHING="true"
   ```

6. **Test Deployment**
   ```bash
   ./scripts/publish/static_site.sh
   # Check logs/publishing/publish_*.log for details
   ```

#### Local Development

```bash
cd site

# Install dependencies
pnpm install

# Run ingestion scripts
node scripts/ingest.mjs
node scripts/build-search-index.mjs

# Start dev server
pnpm run dev
# Visit http://localhost:4321

# Build for production
pnpm run build

# Preview production build
pnpm run preview
```

### 🔧 Configuration

#### Research Prompts (`config/searches.tsv`)

**22 pre-configured prompts across 5 categories:**

- **Research (5):** AI ecosystem watch, tech regulation, open-source activity, hardware landscape, ethics & alignment
- **Market (5):** Model comparisons, corporate strategy, startup radar, developer tools, prompt engineering
- **Ideation (5):** Concept synthesis, novelty filtering, continuity building, meta-project exploration, keyword tagging
- **Analysis (4):** Cross-domain insights, market implications, visualization, narrative summaries
- **Meta (2):** Prompt health checking, new topic detection

Sample format (spaces shown for readability, actual file uses tabs):
```
domain              category  prompt                                     priority  enabled
Concept Synthesizer Ideation  "Generate 5-10 innovative project ideas..." high      true
Novelty Filter      Ideation  "Evaluate yesterday's top 5 ideas..."      high      true
```

#### Environment (`config/env.sh`)

```bash
# Gemini CLI Configuration
export GEMINI_CLI="gemini"
export GEMINI_MODEL="gemini-2.5-flash"
export GEMINI_OUTPUT_FORMAT="text"
export GEMINI_APPROVAL_MODE="yolo"
export GEMINI_YOLO_MODE="true"
export GEMINI_DEBUG="false"

# Execution settings
export MAX_PARALLEL_JOBS="4"
export PARALLEL_EXECUTION="true"

# Feature flags
export ENABLE_NOTIFICATIONS="false"
export ENABLE_FAILURE_NOTIFICATIONS="true"
export ENABLE_STATIC_SITE_PUBLISHING="true"

# Static Site Publishing
export CLOUDFLARE_PROJECT_NAME="neurohelix-site"
export CLOUDFLARE_PRODUCTION_DOMAIN="neurohelix.patchoutech.com"
```

#### Automation Schedule (`launchd/com.neurohelix.daily.plist`)

```xml
<key>StartCalendarInterval</key>
<dict>
    <key>Hour</key>
    <integer>7</integer>  <!-- 7:00 AM daily -->
    <key>Minute</key>
    <integer>0</integer>
</dict>
```

### 🛠️ Maintenance Operations

NeuroHelix includes powerful maintenance commands for workspace management and data reprocessing. These are **operator-only** commands (not invoked by LaunchD) designed for development, debugging, and recovery scenarios.

#### Cleanup Mode (`--cleanup-all`)

Performs a complete workspace reset by removing all generated artifacts while preserving configuration and source code.

**What gets deleted:**
- All daily outputs (`data/outputs/daily/`)
- All reports (`data/reports/`)
- All publishing data (`data/publishing/`)
- All runtime ledgers (`data/runtime/`)
- All dashboards (`dashboards/`)
- All logs (`logs/*.log`, `logs/publishing/`)
- Static site artifacts (`site/public/search-index.json`, `site/src/content/dashboards/`, etc.)

**What gets preserved:**
- All configuration (`config/`, `data/config/`)
- All source code (`scripts/`, `site/src/`)
- Documentation (`ai_docs/`, `docs/`)
- LaunchD configurations (`launchd/`)
- Git repository (`.git/`)

**Usage:**

```bash
# Preview cleanup (dry-run mode)
./scripts/orchestrator.sh --cleanup-all --dry-run

# Execute cleanup with confirmation prompt
./scripts/orchestrator.sh --cleanup-all

# Skip confirmation (dangerous!)
./scripts/orchestrator.sh --cleanup-all --yes

# Allow cleanup with uncommitted git changes
./scripts/orchestrator.sh --cleanup-all --allow-dirty

# Alias syntax (same behavior)
./scripts/orchestrator.sh --reset-workspace --dry-run
```

**Safety Features:**
- ✅ **Git cleanliness check** - Requires clean working tree (bypass with `--allow-dirty`)
- ✅ **Interactive confirmation** - Default "No" prompt (skip with `--yes`)
- ✅ **Dry-run preview** - See exactly what will be deleted before execution
- ✅ **Audit trail** - All operations logged to `logs/maintenance/cleanup_*.log` and `data/runtime/audit.jsonl`
- ✅ **Cloudflare awareness** - Tracks latest deployment ID (note: Pages API doesn't support deletion)

**After cleanup:**
```bash
# Generate fresh data
./scripts/orchestrator.sh
```

#### Reprocess Mode (`--reprocess-today`)

Force reprocessing of the current day's pipeline by deleting today's data and rerunning all 6 steps with manual override tagging.

**What gets deleted (today only):**
- Today's prompt outputs (`data/outputs/daily/YYYY-MM-DD/`)
- Today's daily report (`data/reports/daily_report_YYYY-MM-DD.md`)
- Today's publishing data (`data/publishing/YYYY-MM-DD.json`, tags)
- Today's dashboard (`dashboards/dashboard_YYYY-MM-DD.html`)
- Today's logs (`logs/*YYYY-MM-DD*.log`)
- Today's execution ledger (`data/runtime/execution_ledger_YYYY-MM-DD.json`)

**Pipeline steps executed:**
1. Execute research prompts (22 prompts with context injection)
2. Aggregate results (AI-powered synthesis)
3. Extract tags and categories
4. Generate dashboard (HTML)
5. Export static site payload (JSON)
6. Publish static site (Cloudflare Pages deployment)

**Usage:**

```bash
# Preview reprocess (dry-run mode)
./scripts/orchestrator.sh --reprocess-today --dry-run

# Execute reprocess with confirmation prompt
./scripts/orchestrator.sh --reprocess-today

# Skip confirmation
./scripts/orchestrator.sh --reprocess-today --yes

# Terminate running pipeline if needed
./scripts/orchestrator.sh --reprocess-today --allow-abort

# Combine flags
./scripts/orchestrator.sh --reprocess-today --yes --allow-dirty

# Alias syntax (same behavior)
./scripts/orchestrator.sh --force-today --dry-run
```

**Safety Features:**
- ✅ **Pipeline locking** - Detects and blocks concurrent pipeline executions
- ✅ **Safe termination** - `--allow-abort` gracefully terminates running pipeline (SIGTERM → SIGKILL)
- ✅ **Git cleanliness check** - Requires clean working tree (bypass with `--allow-dirty`)
- ✅ **Interactive confirmation** - Default "No" prompt (skip with `--yes`)
- ✅ **Manual override tagging** - All logs/ledgers marked with operator and reason
- ✅ **Audit trail** - Complete operation history in maintenance logs and audit.jsonl
- ✅ **Idempotent** - Safe to run multiple times in one day

**Manual override tagging:**
```bash
# Execution logs show:
RUN_MODE=manual_override
MANUAL_OVERRIDE_OPERATOR=username
MANUAL_OVERRIDE_REASON=force reprocess
```

#### Available Flags

| Flag | Description | Modes |
|------|-------------|-------|
| `--cleanup-all` | Full workspace cleanup | Cleanup |
| `--reset-workspace` | Alias for `--cleanup-all` | Cleanup |
| `--reprocess-today` | Force reprocess current day | Reprocess |
| `--force-today` | Alias for `--reprocess-today` | Reprocess |
| `--dry-run` | Preview without executing | Both |
| `--yes` | Skip confirmation prompts | Both |
| `--allow-dirty` | Bypass git cleanliness check | Both |
| `--allow-abort` | Terminate running pipeline | Reprocess |

**Flag combinations:**
- ✅ `--cleanup-all --dry-run --allow-dirty` - Preview cleanup with dirty git tree
- ✅ `--reprocess-today --yes --allow-abort` - Force reprocess, terminate existing run
- ❌ `--cleanup-all --reprocess-today` - **ERROR:** Mutually exclusive

#### Audit Trail

All maintenance operations create comprehensive audit records:

**Text Logs:** `logs/maintenance/{cleanup,reprocess}_YYYY-MM-DDTHHMMSS.log`
```
[2025-11-09 10:29:04] 🧹 NeuroHelix Workspace Cleanup
[2025-11-09 10:29:04] ================================
[2025-11-09 10:29:04] Operator: username
[2025-11-09 10:29:04] Timestamp: Sun Nov  9 10:29:04 EST 2025
[2025-11-09 10:29:04] Dry run: false
[2025-11-09 10:29:04] ✅ Git working tree is clean
...
```

**JSONL Audit:** `data/runtime/audit.jsonl`
```json
{"action":"cleanup_all","operator":"username","timestamp":"2025-11-09T15:29:05Z","dry_run":false,"git_status":"clean","target_paths":[...],"cloudflare_deploy_id":"abc123"}
{"action":"reprocess_today","operator":"username","date":"2025-11-09","timestamp":"2025-11-09T15:45:12Z","dry_run":false,"manual_override":true,"lock_behavior":"clean","pipeline_duration_seconds":324,"deploy_id":"xyz789"}
```

#### LaunchD Protection

Maintenance modes are **explicitly blocked** from LaunchD automation:

```bash
if [ "${MODE}" != "normal" ] && [ -n "${LAUNCHED_BY_LAUNCHD:-}" ]; then
    echo "❌ Error: Maintenance modes cannot be invoked by LaunchD"
    exit 1
fi
```

These commands are **operator-only** and require manual terminal invocation.

### 🎨 Dashboard & Site Features

#### Static Website (Primary)
- **Modern Framework** - Built with Astro 5 + Tailwind CSS 4
- **Full-Text Search** - MiniSearch-powered client-side search with fuzzy matching
- **Smart Filtering** - Filter by tags and categories with instant updates
- **Tag Cloud** - Weighted visualization of all tags with frequency-based sizing
- **Category Pills** - Multi-select filtering by research categories
- **GitHub-Style Markdown** - Beautiful typography with Fira Code + Inter fonts
- **Heading Anchors** - Deep linking to specific sections (#executive-summary)
- **Dark Theme** - Charcoal background (#1a1a1a) with electric violet (#8b5cf6) accents
- **Responsive Design** - Mobile-first with smooth transitions
- **Accessibility** - WCAG AA compliant with keyboard navigation
- **Cloudflare Deployment** - Automated publishing via Wrangler CLI

#### Legacy HTML Dashboards
- **Self-contained HTML** - Single file with embedded CSS, works offline
- **Executive Summary** - 200-300 word strategic overview
- **Key Themes** - Organized by insight clusters
- **Strategic Implications** - Actionable recommendations
- **Date-specific URLs** - `dashboard_YYYY-MM-DD.html` for historical browsing

### 🔄 Daily Workflow

1. **LaunchD Trigger** - Runs at 7:00 AM (configurable)
2. **Context-Aware Execution** - 22 prompts with temporal context injection
3. **Structured Output** - Organized by date in `data/outputs/daily/YYYY-MM-DD/`
4. **Intelligent Aggregation** - Cross-domain synthesis with thematic grouping
5. **Tag Extraction** - AI-powered tag and category extraction from reports
6. **Dashboard Generation** - Beautiful HTML with embedded analytics
7. **JSON Export** - Structured payload for static site consumption
8. **Static Site Build** - Astro ingestion, search index generation, and build
9. **Cloudflare Deployment** - Automated publishing to production domain
10. **Idempotent Re-runs** - Safe to execute multiple times (completes in <1s)

**Manual Interventions:**
- **Force Reprocess** - Use `--reprocess-today` to delete and regenerate today's data
- **Workspace Cleanup** - Use `--cleanup-all` to reset entire workspace to clean state
- **Pipeline Lock** - Automatic prevention of concurrent executions with safe termination
- **Audit Trail** - All operations logged to `data/runtime/audit.jsonl` for accountability

### 🤖 Context-Aware Intelligence

- **Novelty Filter** - Automatically references yesterday's top 5 ideas
- **Continuity Builder** - Analyzes last 7 days of reports for patterns
- **Meta-Project Explorer** - Self-aware of system structure and outputs
- **Temporal Analysis** - Historical context injection for deeper insights

### 🌟 Synthesis Architecture

**Multi-level Analysis Pipeline:**

1. **Thematic Synthesis** - AI groups findings by insight (not domain)
2. **Signal-to-Noise Filtering** - Prioritizes novel + actionable over volume
3. **Strategic Implication Mapping** - Connects insights to business impact
4. **Recommendation Generation** - Outputs 3-5 specific next actions
5. **Historical Correlation** - Compares to previous 7 days for trend detection

**Example Output Structure:**
- Executive Summary (200-300 words)
- Key Themes & Insights (4-6 thematic sections)
- Notable Developments (5-10 specific items)
- Strategic Implications
- Actionable Recommendations (3-5 items)

### 📋 Documentation

Comprehensive guides in `docs/`:

- **[Automation Setup](docs/automation-setup.md)** - LaunchD installation, management, scheduling
- **[Gemini CLI Config](docs/gemini-cli-config.md)** - CLI setup and troubleshooting
- **[Context-Aware Prompts](docs/context-aware-prompts.md)** - How temporal context injection works

Development logs in `ai_dev_logs/`:

- **[IMPLEMENTATION_STATUS.md](ai_dev_logs/IMPLEMENTATION_STATUS.md)** - Site look & feel implementation progress
- **[STATIC_SITE_IMPLEMENTATION.md](ai_dev_logs/STATIC_SITE_IMPLEMENTATION.md)** - Complete static site publishing guide
- **[IMPLEMENTATION_SUMMARY.md](ai_dev_logs/IMPLEMENTATION_SUMMARY.md)** - Site features implementation summary
- **[STATUS.md](ai_dev_logs/STATUS.md)** - Overall system health and component status

### 📊 Output Examples

#### Daily Report (`data/reports/daily_report_YYYY-MM-DD.md`)
```markdown
# NeuroHelix Intelligence Report - 2025-11-07

## Executive Summary

Today's research reveals three major technological shifts:
[200-300 word strategic synthesis]

## Key Themes & Insights

### 🎆 Emerging AI Infrastructure Trends
[Cross-domain analysis of infrastructure developments]

### 💰 Market Dynamics & Funding Patterns  
[Investment trends correlated with technical developments]

### 🚀 Strategic Opportunities
[Actionable insights from pattern analysis]

## Strategic Implications
[Business and technical impacts]

## Actionable Recommendations
1. [Specific next action based on analysis]
2. [Investment or research priority]
3. [Strategic positioning recommendation]

## End of Report
```

#### Static Site ([neurohelix.userdomain.com](https://neurohelix.userdomain.com))
- Interactive dashboard gallery with search
- Tag cloud with frequency-based weighting
- Category filtering (Research, Market, Ideation, Analysis, Meta)
- Full-text search across all reports
- Mobile-responsive design
- Deep linking to report sections

#### Legacy HTML Dashboard (`dashboards/dashboard_YYYY-MM-DD.html`)
Self-contained HTML with embedded CSS featuring:
- Executive summary cards
- Thematic insight sections  
- Strategic recommendations
- Historical trend indicators

### 🛠️ Requirements

- **macOS** (tested on Monterey+) - for LaunchD automation
- **Bash** 4.0+ (standard on macOS)
- **[Gemini CLI](https://github.com/replit/gemini-cli)** - Google's Gemini CLI tool
- **[Node.js](https://nodejs.org/)** 18+ - for static site build
- **[pnpm](https://pnpm.io/)** - Fast, disk space efficient package manager
- **[Wrangler](https://developers.cloudflare.com/workers/wrangler/)** - Cloudflare CLI (installed via pnpm)
- **LaunchD** (built into macOS)
- Optional: **curl** (for webhook notifications)

For Linux users: Use cron instead of LaunchD. See `docs/automation-setup.md` for details.

### 📎 Management Commands

```bash
# ============================================================================
# Normal Pipeline Execution
# ============================================================================

# Manual execution (runs all 6 steps)
./scripts/orchestrator.sh

# Or via LaunchD
launchctl start com.neurohelix.daily

# ============================================================================
# Maintenance Operations (Operator-Only)
# ============================================================================

# Cleanup - Remove all generated artifacts
./scripts/orchestrator.sh --cleanup-all --dry-run      # Preview
./scripts/orchestrator.sh --cleanup-all                # Execute with prompt
./scripts/orchestrator.sh --cleanup-all --yes          # Execute without prompt

# Reprocess - Force rerun today's pipeline
./scripts/orchestrator.sh --reprocess-today --dry-run  # Preview
./scripts/orchestrator.sh --reprocess-today            # Execute with prompt
./scripts/orchestrator.sh --reprocess-today --yes      # Execute without prompt

# Advanced flags
./scripts/orchestrator.sh --cleanup-all --allow-dirty  # Bypass git check
./scripts/orchestrator.sh --reprocess-today --allow-abort  # Terminate running pipeline

# ============================================================================
# Automation Management
# ============================================================================

# Check automation status
launchctl list | grep neurohelix

# Install/reinstall automation
./install_automation.sh

# Uninstall automation
./uninstall_automation.sh

# ============================================================================
# Logs & Monitoring
# ============================================================================

# View real-time logs
tail -f logs/launchd_stdout.log
tail -f logs/launchd_stderr.log
tail -f logs/publishing/publish_*.log

# Check maintenance logs
ls -lh logs/maintenance/
cat logs/maintenance/cleanup_*.log
cat logs/maintenance/reprocess_*.log

# View audit trail
cat data/runtime/audit.jsonl | jq '.'  # Pretty-print JSONL

# Check execution telemetry
cat data/runtime/execution_ledger_$(date +%Y-%m-%d).json | jq '.'

# ============================================================================
# Output Inspection
# ============================================================================

# Check today's outputs
ls -lh data/reports/daily_report_$(date +%Y-%m-%d).md
ls -lh dashboards/dashboard_$(date +%Y-%m-%d).html
ls -lh data/publishing/$(date +%Y-%m-%d).json

# View today's report
cat data/reports/daily_report_$(date +%Y-%m-%d).md
open dashboards/dashboard_$(date +%Y-%m-%d).html

# ============================================================================
# Static Site Development
# ============================================================================

# Test static site locally
cd site
pnpm install
pnpm run build
pnpm run preview  # Visit http://localhost:4321

# Force rebuild site data
node scripts/ingest.mjs
node scripts/build-search-index.mjs
```

### 🔍 System Status

✅ **Production Ready** - All major features implemented and tested
✅ **Fully Automated** - Daily execution via LaunchD
✅ **Intelligent Pipeline** - Context-aware prompts with AI synthesis
✅ **Static Site Publishing** - Automated Cloudflare Pages deployment
✅ **Full-Text Search** - Client-side search with MiniSearch
✅ **Smart Filtering** - Tags, categories, and temporal navigation
✅ **Maintenance Tools** - Workspace cleanup and force reprocess operations
✅ **Audit Trail** - Complete operation history in JSONL format
✅ **Pipeline Safety** - Git checks, locking, and graceful termination
✅ **Comprehensive Documentation** - Setup, management, troubleshooting guides  

See implementation logs in `ai_dev_logs/` for complete feature details:
- [STATIC_SITE_IMPLEMENTATION.md](ai_dev_logs/STATIC_SITE_IMPLEMENTATION.md) - Publishing pipeline
- [IMPLEMENTATION_SUMMARY.md](ai_dev_logs/IMPLEMENTATION_SUMMARY.md) - Site features
- [STATUS.md](ai_dev_logs/STATUS.md) - System health

### 📝 License

Use freely for personal and commercial projects.

---

**Built with ❤️ for autonomous research intelligence**
