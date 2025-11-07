# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

**NeuroHelix** is a production-ready AI-driven research automation system that runs daily cycles of discovery, synthesis, and ideation. Built entirely in Bash, it orchestrates 20 curated research prompts via Gemini CLI, performs intelligent cross-domain synthesis, and generates beautiful HTML dashboards.

**Key characteristics:**
- Fully automated via LaunchD (macOS) or cron (Linux)
- Context-aware prompts that reference historical data
- Idempotent execution (re-runs complete in <1 second)
- 4-stage pipeline: Execute → Aggregate → Render → Notify

## Essential Commands

### Project Initialization

```bash
# Initialize a new NeuroHelix project (creates directory structure)
./init_project.sh
```

**Note:** This script is only needed for fresh installations or recreating the directory structure. The system is already initialized if the directories exist.

### Running the Pipeline

```bash
# Run the complete daily pipeline
./scripts/orchestrator.sh

# Test with 3 prompts only (for development)
./tests/test_single_prompt.sh

# Test context-aware prompt setup
./tests/test_context_aware_prompts.sh
```

### Automation Management

```bash
# Install daily automation (7 AM by default)
./install_automation.sh

# Uninstall automation
./uninstall_automation.sh

# Check automation status
launchctl list | grep neurohelix

# Manually trigger the automation (runs immediately)
launchctl start com.neurohelix.daily

# View LaunchD logs
tail -f logs/launchd_stdout.log
tail -f logs/launchd_stderr.log
```

### Viewing Results

```bash
# Open today's dashboard
open dashboards/dashboard_$(date +%Y-%m-%d).html

# Open latest dashboard (symlink)
open dashboards/latest.html

# View today's report
cat data/reports/daily_report_$(date +%Y-%m-%d).md

# List today's raw outputs
ls -lh data/outputs/daily/$(date +%Y-%m-%d)/
```

### Monitoring & Debugging

```bash
# View orchestrator logs
tail -100 logs/orchestrator_*.log

# View most recent log
tail -f $(ls -t logs/orchestrator_*.log | head -1)

# Test Gemini CLI directly
gemini --model gemini-2.5-flash "test prompt"

# Enable debug mode (edit config/env.sh)
export GEMINI_DEBUG="true"
```

### Configuration

```bash
# Edit research prompts
nano config/searches.tsv

# Edit environment settings
nano config/env.sh

# Change LaunchD schedule (edit Hour/Minute)
nano launchd/com.neurohelix.daily.plist
```

## High-Level Architecture

### 4-Stage Pipeline

The orchestrator (`scripts/orchestrator.sh`) coordinates four sequential stages:

1. **Execute** (`scripts/executors/run_prompts.sh`)
   - Reads `config/searches.tsv` (TSV format: domain, category, prompt, priority, enabled)
   - Executes enabled prompts in parallel (up to `MAX_PARALLEL_JOBS`)
   - Injects historical context for specific domains (Novelty Filter, Continuity Builder, Meta-Project Explorer)
   - Outputs to `data/outputs/daily/YYYY-MM-DD/{domain}.md`
   - Creates completion marker: `data/outputs/daily/YYYY-MM-DD/.execution_complete`

2. **Aggregate** (`scripts/aggregators/aggregate_daily.sh`)
   - Combines all domain outputs into single document
   - Sends to Gemini CLI with sophisticated synthesis prompt
   - Generates AI-powered cross-domain analysis
   - Creates `data/reports/daily_report_YYYY-MM-DD.md`
   - Skipped if report exists and contains "## End of Report"

3. **Render** (`scripts/renderers/generate_dashboard.sh`)
   - Converts markdown report to HTML with embedded CSS
   - Uses awk-based markdown parser (not sed, due to multiline issues)
   - Generates `dashboards/dashboard_YYYY-MM-DD.html`
   - Creates/updates symlink: `dashboards/latest.html`
   - Skipped if dashboard exists and contains `</html>`

4. **Notify** (`scripts/notifiers/notify.sh`)
   - Optional stage (controlled by `ENABLE_NOTIFICATIONS` in `config/env.sh`)
   - Currently disabled by default
   - Can send email or webhook notifications

### Context-Aware Intelligence

Three prompts have special historical context injection in `scripts/executors/run_prompts.sh`:

- **Novelty Filter**: Reads yesterday's `concept_synthesizer.md` to re-evaluate ideas with today's research
- **Continuity Builder**: Analyzes last 7 days of reports from `data/reports/` to identify persistent themes
- **Meta-Project Explorer**: Gets system structure info (config, recent reports) to suggest improvements

Context is injected by appending data to the prompt before sending to Gemini CLI.

### Data Flow

```
config/searches.tsv
    ↓
scripts/executors/run_prompts.sh
    ↓
data/outputs/daily/YYYY-MM-DD/*.md
    ↓
scripts/aggregators/aggregate_daily.sh
    ↓
data/reports/daily_report_YYYY-MM-DD.md
    ↓
scripts/renderers/generate_dashboard.sh
    ↓
dashboards/dashboard_YYYY-MM-DD.html
```

### Idempotency Implementation

Each stage checks for completion before running:
- **Executors**: Check `.execution_complete` marker file
- **Aggregators**: Check if report exists and contains "## End of Report"
- **Renderers**: Check if dashboard exists and contains `</html>` with >100 lines

To force re-run: Delete the completion marker or output file.

## Key Implementation Details

### TSV Format (config/searches.tsv)

```
domain	category	prompt	priority	enabled
AI Ecosystem Watch	Research	Summarize the most...	high	true
```

**Important:**
- Use actual TAB characters (not spaces) between columns
- Column order: domain, category, prompt, priority, enabled
- priority values: `high`, `medium`, `low` (informational only)
- enabled values: `true` or `false`
- Currently configured with 20 research prompts across 5 categories:
  - **Research (5):** Latest developments, breakthroughs, papers, methodologies, applications
  - **Market (5):** Funding trends, startup analysis, competitive intelligence, market dynamics
  - **Ideation (4):** Concept synthesis, novelty filtering, continuity building, opportunity mapping
  - **Analysis (4):** Impact assessment, risk analysis, strategic evaluation, trend correlation
  - **Meta (2):** Project reflection, system optimization (disabled by default)

### Gemini CLI Configuration

Environment variables in `config/env.sh`:
- `GEMINI_CLI="gemini"` - CLI command name
- `GEMINI_MODEL="gemini-2.5-flash"` - Model to use (can be `gemini-2.0-flash-exp`, `gemini-pro`, etc.)
- `GEMINI_OUTPUT_FORMAT="text"` - Output format (text/json/stream-json)
- `GEMINI_APPROVAL_MODE="yolo"` - Auto-approve all actions (options: default, auto_edit, yolo)
- `GEMINI_YOLO_MODE="true"` - Shortcut for auto-approve all
- `GEMINI_DEBUG="false"` - Enable debug output

**Additional environment variables:**
- `COPILOT_CLI="gh copilot"` - GitHub Copilot CLI (for future extensions)
- `PARALLEL_EXECUTION="true"` - Enable/disable parallel prompt execution
- `MAX_PARALLEL_JOBS="4"` - Max concurrent jobs
- `ENABLE_NOTIFICATIONS="false"` - Enable/disable email/webhook notifications
- `NOTIFICATION_EMAIL=""` - Email for notifications (if enabled)
- `DISCORD_WEBHOOK_URL=""` - Discord webhook for notifications (if enabled)

### Timeout Protection

Each prompt execution has 120-second timeout implemented in `scripts/executors/run_prompts.sh`:
- Uses bash background processes with `kill -0` polling
- Kills hung processes with `kill -9`
- Appends timeout error message to output file

### Parallel Execution

Controlled by `config/env.sh`:
- `PARALLEL_EXECUTION="true"` - Enable/disable parallel mode
- `MAX_PARALLEL_JOBS="4"` - Max concurrent Gemini CLI processes

Pipeline waits for all background jobs with `wait` before proceeding.

### Synthesis Architecture

The aggregator uses a sophisticated multi-step prompt that instructs Gemini to:
1. Create executive summary (200-300 words)
2. Group findings by theme (not by source domain)
3. Identify cross-domain patterns
4. Surface contradictions and non-obvious connections
5. Generate 3-5 actionable recommendations

This is **not** simple concatenation—it's AI-powered synthesis.

### LaunchD vs Cron

**macOS (LaunchD):**
- Config: `launchd/com.neurohelix.daily.plist`
- Installed to: `~/Library/LaunchAgents/`
- Schedule format: XML with Hour/Minute keys
- Logs: Automatically redirected to `logs/launchd_*.log`

**Linux (Cron):**
- Alternative: Add to `crontab -e`
- Example: `0 7 * * * cd /path/to/NeuroHelix && ./scripts/orchestrator.sh`

## Testing & Development

### Test Scripts

The `tests/` directory contains two testing scripts:

**1. Simple Gemini CLI Test (`tests/test_single_prompt.sh`):**
- Tests basic Gemini CLI connectivity
- Runs single prompt: "What is 2+2?"
- 30-second timeout
- Useful for verifying authentication and CLI installation

**2. Context-Aware Prompt Test (`tests/test_context_aware_prompts.sh`):**
- Creates mock yesterday's concept synthesizer output
- Verifies file access for Novelty Filter
- Checks historical reports for Continuity Builder
- Validates system structure for Meta-Project Explorer
- Does NOT execute actual prompts (setup validation only)

### Development Workflow

```bash
# 1. Verify Gemini CLI works
./tests/test_single_prompt.sh

# 2. Check context-aware setup
./tests/test_context_aware_prompts.sh

# 3. Run partial pipeline (edit config/searches.tsv to enable only 3-5 prompts)
nano config/searches.tsv  # Set most prompts to enabled=false
./scripts/orchestrator.sh

# 4. Review outputs
ls -lh data/outputs/daily/$(date +%Y-%m-%d)/
cat data/reports/daily_report_$(date +%Y-%m-%d).md

# 5. Re-enable all prompts and run full pipeline
nano config/searches.tsv  # Set prompts back to enabled=true
./scripts/orchestrator.sh
```

### Notification System

The notification stage (Step 4 of pipeline) is **disabled by default**. To enable:

**Email Notifications:**
1. Ensure `mail` command is configured on your system
2. Edit `config/env.sh`:
   ```bash
   export ENABLE_NOTIFICATIONS="true"
   export NOTIFICATION_EMAIL="your@email.com"
   ```

**Discord Webhook Notifications:**
1. Create Discord webhook in your server settings
2. Edit `config/env.sh`:
   ```bash
   export ENABLE_NOTIFICATIONS="true"
   export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
   ```

**Implementation:** `scripts/notifiers/notify.sh`
- Sends notification with dashboard file path
- Runs only if `ENABLE_NOTIFICATIONS="true"`
- Failures are non-fatal (pipeline completes regardless)

## Troubleshooting

### Pipeline Doesn't Execute

1. Check Gemini CLI is installed: `which gemini`
2. Verify authentication: `gemini "test"`
3. Check TSV format: `cat config/searches.tsv | cat -A` (should show `^I` for tabs)
4. Review logs: `tail -100 logs/orchestrator_*.log`

### Prompts Timeout

1. Increase timeout in `scripts/executors/run_prompts.sh` (line ~101: `timeout_seconds=120`)
2. Check network connectivity
3. Verify API quotas/limits aren't exceeded
4. Enable debug: `GEMINI_DEBUG="true"` in `config/env.sh`

### Dashboard Not Generated

1. Check if report exists: `ls -lh data/reports/daily_report_*.md`
2. Look for errors in aggregator step
3. Verify awk is installed: `which awk`
4. Check renderer logs in orchestrator output

### Context-Aware Prompts Not Working

1. Verify yesterday's concepts exist: `ls data/outputs/daily/$(date -v-1d +%Y-%m-%d 2>/dev/null || date -d "yesterday" +%Y-%m-%d)/concept_synthesizer.md`
2. Check historical reports: `ls -lh data/reports/daily_report_*.md`
3. Run test script: `./tests/test_context_aware_prompts.sh`

### LaunchD Job Not Running

1. Check job is loaded: `launchctl list | grep neurohelix`
2. View LaunchD errors: `tail -f logs/launchd_stderr.log`
3. Manually test: `launchctl start com.neurohelix.daily`
4. Verify plist permissions: `ls -l ~/Library/LaunchAgents/com.neurohelix.daily.plist`

## Project Structure

```
NeuroHelix/
├── config/               # Configuration files
│   ├── env.sh           # Environment variables and settings
│   └── searches.tsv     # Research prompts (20 domains)
├── scripts/             # Pipeline scripts
│   ├── orchestrator.sh  # Main coordinator
│   ├── executors/       # Prompt execution (run_prompts.sh)
│   ├── aggregators/     # Synthesis (aggregate_daily.sh)
│   ├── renderers/       # Dashboard generation (generate_dashboard.sh)
│   ├── notifiers/       # Notifications (notify.sh)
│   └── meta/            # Future meta-automation scripts
├── data/                # Generated data
│   ├── outputs/daily/   # Raw prompt outputs (by date)
│   └── reports/         # Synthesized daily reports
├── dashboards/          # HTML dashboards
├── logs/                # Execution logs
├── launchd/             # LaunchD configuration template
├── templates/           # Reusable templates
├── tests/               # Test scripts
├── docs/                # Detailed documentation
├── ai_dev_logs/         # AI development session logs
├── ai_docs/             # Original project design docs
├── install_automation.sh   # LaunchD installer
├── uninstall_automation.sh # LaunchD uninstaller
└── init_project.sh      # Project initialization script
```

## Important Notes

### Prerequisites

- **macOS** (tested on Monterey+) or Linux
- **Bash** 4.0+
- **[Gemini CLI](https://github.com/replit/gemini-cli)** - Must be installed and authenticated
- **LaunchD** (macOS built-in) or **cron** (Linux)

### Re-running Behavior

The system is idempotent. If you run `./scripts/orchestrator.sh` multiple times on the same day:
- First run: Executes all prompts, takes 3-4 minutes
- Subsequent runs: Skips completed stages, completes in <1 second

To force re-run: Delete the completion markers or output files.

### Customization

**Adding new prompts:**
1. Edit `config/searches.tsv`
2. Add new line with: `domain`, `category`, `prompt`, `priority`, `enabled`
3. Use tabs (not spaces) between fields

**Changing schedule:**
1. Edit `launchd/com.neurohelix.daily.plist`
2. Modify `<key>Hour</key>` and `<key>Minute</key>`
3. Reinstall: `./uninstall_automation.sh && ./install_automation.sh`

**Adjusting parallelism:**
- Edit `config/env.sh`
- Change `MAX_PARALLEL_JOBS` (default: 4)
- Higher = faster but more API load

### Documentation

Additional documentation in `docs/`:
- `automation-setup.md` - LaunchD installation and management
- `context-aware-prompts.md` - How context injection works
- `gemini-cli-config.md` - CLI setup and troubleshooting

AI development logs in `ai_dev_logs/`:
- `STATUS.md` - Implementation status and test results
- `CONTEXT_AWARE_COMPLETE.md` - Context-aware prompt implementation details
- `SETUP_COMPLETE.md` - Initial setup documentation
- `SYNTHESIS_COMPLETE.md` - Synthesis pipeline documentation
- `DASHBOARD_FIXED.md` - Dashboard rendering fixes

Project documentation in `ai_docs/`:
- `MasterIdeaPlan.md` - Original project concept and design
- `prompts.md` - Prompt library and templates
