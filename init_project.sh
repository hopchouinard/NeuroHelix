#!/bin/bash
# NeuroHelix Project Initialization Script

echo "🧠 Initializing NeuroHelix - Automated Research & Ideation Ecosystem..."

# Create directory structure
mkdir -p {config,scripts,data/{prompts,outputs,corpus,reports},templates,logs,dashboards,docs}
mkdir -p data/outputs/{daily,archive}
mkdir -p scripts/{executors,aggregators,renderers,notifiers,meta}

echo "✅ Directory structure created"

# Create sample searches manifest
cat > config/searches.tsv << 'TSV'
domain	prompt	priority	enabled
AI Research	"What are the most significant breakthroughs in AI research published in the last 24 hours?"	high	true
Tech Trends	"Analyze emerging technology trends in cloud computing and edge AI"	medium	true
Market Analysis	"Identify new AI-powered SaaS products launched this week"	medium	true
Academic Papers	"Summarize top-cited AI/ML papers from arxiv.org in the last week"	low	true
TSV

echo "✅ Sample searches manifest created"

# Create main orchestrator script
cat > scripts/orchestrator.sh << 'ORCH'
#!/bin/bash
# Main orchestration script - runs daily via cron

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${PROJECT_ROOT}/config/env.sh"

DATE=$(date +%Y-%m-%d)
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)
LOG_FILE="${PROJECT_ROOT}/logs/orchestrator_${TIMESTAMP}.log"

log() {
    echo "[$(date +%Y-%m-%d\ %H:%M:%S)] $*" | tee -a "$LOG_FILE"
}

log "🚀 Starting NeuroHelix daily pipeline for ${DATE}"

# Step 1: Execute research prompts
log "📊 Step 1: Executing research prompts..."
"${PROJECT_ROOT}/scripts/executors/run_prompts.sh" 2>&1 | tee -a "$LOG_FILE"

# Step 2: Aggregate results
log "📝 Step 2: Aggregating results..."
"${PROJECT_ROOT}/scripts/aggregators/aggregate_daily.sh" 2>&1 | tee -a "$LOG_FILE"

# Step 3: Generate dashboard
log "🎨 Step 3: Generating dashboard..."
"${PROJECT_ROOT}/scripts/renderers/generate_dashboard.sh" 2>&1 | tee -a "$LOG_FILE"

# Step 4: Send notification (optional)
if [ "${ENABLE_NOTIFICATIONS:-false}" = "true" ]; then
    log "📧 Step 4: Sending notification..."
    "${PROJECT_ROOT}/scripts/notifiers/notify.sh" 2>&1 | tee -a "$LOG_FILE"
fi

log "✅ Pipeline completed successfully for ${DATE}"
ORCH

chmod +x scripts/orchestrator.sh

echo "✅ Main orchestrator created"

# Create environment config
cat > config/env.sh << 'ENV'
#!/bin/bash
# Environment configuration

# Project paths
export PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export CONFIG_DIR="${PROJECT_ROOT}/config"
export DATA_DIR="${PROJECT_ROOT}/data"
export LOGS_DIR="${PROJECT_ROOT}/logs"
export DASHBOARD_DIR="${PROJECT_ROOT}/dashboards"

# CLI tools (adjust paths as needed)
export GEMINI_CLI="gemini"  # Adjust if needed
export COPILOT_CLI="gh copilot"  # GitHub Copilot CLI

# Model settings
export DEFAULT_MODEL="gemini-2.0-flash-exp"
export MAX_TOKENS="8192"
export TEMPERATURE="0.7"

# Feature flags
export ENABLE_NOTIFICATIONS="false"
export ENABLE_META_AUTOMATION="false"
export PARALLEL_EXECUTION="true"
export MAX_PARALLEL_JOBS="4"

# Notification settings (if enabled)
export NOTIFICATION_EMAIL=""
export DISCORD_WEBHOOK_URL=""
ENV

echo "✅ Environment config created"

# Create prompt executor
cat > scripts/executors/run_prompts.sh << 'EXEC'
#!/bin/bash
# Execute all research prompts from manifest

set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../config/env.sh"

DATE=$(date +%Y-%m-%d)
OUTPUT_DIR="${DATA_DIR}/outputs/daily/${DATE}"
mkdir -p "$OUTPUT_DIR"

SEARCHES_FILE="${CONFIG_DIR}/searches.tsv"

if [ ! -f "$SEARCHES_FILE" ]; then
    echo "Error: searches.tsv not found"
    exit 1
fi

execute_prompt() {
    local domain="$1"
    local prompt="$2"
    local priority="$3"
    
    local safe_domain=$(echo "$domain" | tr ' ' '_' | tr '[:upper:]' '[:lower:]')
    local output_file="${OUTPUT_DIR}/${safe_domain}.md"
    
    echo "Executing: $domain"
    
    # Create markdown with YAML front-matter
    cat > "$output_file" << YAML
---
domain: ${domain}
date: ${DATE}
priority: ${priority}
---

# ${domain} - ${DATE}

YAML
    
    # Execute prompt using Gemini CLI (placeholder - adjust for actual CLI)
    echo "$prompt" | ${GEMINI_CLI} chat --model "${DEFAULT_MODEL}" >> "$output_file" 2>&1 || {
        echo "Error executing prompt for $domain" >&2
        echo "Error: Failed to execute research prompt" >> "$output_file"
    }
    
    echo "✅ Completed: $domain"
}

export -f execute_prompt
export GEMINI_CLI DEFAULT_MODEL DATE OUTPUT_DIR

# Parse TSV and execute prompts
tail -n +2 "$SEARCHES_FILE" | while IFS=$'\t' read -r domain prompt priority enabled; do
    if [ "$enabled" = "true" ]; then
        if [ "${PARALLEL_EXECUTION}" = "true" ]; then
            execute_prompt "$domain" "$prompt" "$priority" &
            
            # Limit parallel jobs
            while [ $(jobs -r | wc -l) -ge "${MAX_PARALLEL_JOBS}" ]; do
                sleep 1
            done
        else
            execute_prompt "$domain" "$prompt" "$priority"
        fi
    fi
done

# Wait for all background jobs to complete
wait

echo "✅ All prompts executed for ${DATE}"
EXEC

chmod +x scripts/executors/run_prompts.sh

echo "✅ Prompt executor created"

# Create aggregator
cat > scripts/aggregators/aggregate_daily.sh << 'AGG'
#!/bin/bash
# Aggregate daily results into unified report

set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../config/env.sh"

DATE=$(date +%Y-%m-%d)
INPUT_DIR="${DATA_DIR}/outputs/daily/${DATE}"
REPORT_DIR="${DATA_DIR}/reports"
REPORT_FILE="${REPORT_DIR}/daily_report_${DATE}.md"

mkdir -p "$REPORT_DIR"

if [ ! -d "$INPUT_DIR" ]; then
    echo "Error: No output directory for ${DATE}"
    exit 1
fi

echo "Aggregating results for ${DATE}..."

# Create report header
cat > "$REPORT_FILE" << HEADER
# NeuroHelix Daily Report - ${DATE}

Generated: $(date +"%Y-%m-%d %H:%M:%S")

---

## Executive Summary

HEADER

# Collect all findings
cat >> "$REPORT_FILE" << 'SUMMARY'
[This section will be populated by AI summarization]

---

## Detailed Findings

SUMMARY

# Append all domain reports
for file in "$INPUT_DIR"/*.md; do
    if [ -f "$file" ]; then
        echo "" >> "$REPORT_FILE"
        cat "$file" >> "$REPORT_FILE"
        echo "" >> "$REPORT_FILE"
        echo "---" >> "$REPORT_FILE"
        echo "" >> "$REPORT_FILE"
    fi
done

# Use Gemini to create executive summary
SUMMARY_PROMPT="Read the following research findings and create a concise executive summary highlighting key insights, trends, and actionable recommendations:\n\n$(cat "$REPORT_FILE")"

SUMMARY_OUTPUT=$(echo "$SUMMARY_PROMPT" | ${GEMINI_CLI} chat --model "${DEFAULT_MODEL}" 2>/dev/null || echo "Summary generation failed")

# Insert summary into report (replace placeholder)
sed -i.bak "s/\[This section will be populated by AI summarization\]/${SUMMARY_OUTPUT}/" "$REPORT_FILE"
rm "${REPORT_FILE}.bak" 2>/dev/null || true

echo "✅ Daily report created: $REPORT_FILE"
AGG

chmod +x scripts/aggregators/aggregate_daily.sh

echo "✅ Aggregator created"

# Create dashboard renderer
cat > scripts/renderers/generate_dashboard.sh << 'RENDER'
#!/bin/bash
# Generate interactive HTML dashboard

set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../config/env.sh"

DATE=$(date +%Y-%m-%d)
REPORT_FILE="${DATA_DIR}/reports/daily_report_${DATE}.md"
DASHBOARD_FILE="${DASHBOARD_DIR}/dashboard_${DATE}.html"

mkdir -p "$DASHBOARD_DIR"

if [ ! -f "$REPORT_FILE" ]; then
    echo "Error: Report file not found"
    exit 1
fi

echo "Generating dashboard for ${DATE}..."

# Create HTML template
cat > "$DASHBOARD_FILE" << 'HTML'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NeuroHelix Dashboard - DATE_PLACEHOLDER</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            line-height: 1.6;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 40px;
        }
        h1 {
            color: #667eea;
            margin-bottom: 10px;
            font-size: 2.5em;
        }
        .meta {
            color: #666;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #e0e0e0;
        }
        .section {
            margin: 30px 0;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }
        h2 {
            color: #764ba2;
            margin-bottom: 15px;
        }
        code {
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }
        pre {
            background: #2d2d2d;
            color: #f8f8f2;
            padding: 15px;
            border-radius: 6px;
            overflow-x: auto;
        }
        .highlight {
            background: #fff3cd;
            padding: 15px;
            border-left: 4px solid #ffc107;
            margin: 15px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🧠 NeuroHelix Dashboard</h1>
        <div class="meta">
            <strong>Date:</strong> DATE_PLACEHOLDER<br>
            <strong>Status:</strong> ✅ Pipeline Completed<br>
            <strong>Generated:</strong> TIMESTAMP_PLACEHOLDER
        </div>
        <div id="content">
CONTENT_PLACEHOLDER
        </div>
    </div>
</body>
</html>
HTML

# Convert markdown to HTML content (basic conversion)
MARKDOWN_CONTENT=$(cat "$REPORT_FILE")

# Simple markdown to HTML conversion (can be enhanced with pandoc or similar)
HTML_CONTENT=$(echo "$MARKDOWN_CONTENT" | sed 's/^# \(.*\)/<h2>\1<\/h2>/g' | \
                                          sed 's/^## \(.*\)/<h3>\1<\/h3>/g' | \
                                          sed 's/^### \(.*\)/<h4>\1<\/h4>/g' | \
                                          sed 's/^\* \(.*\)/<li>\1<\/li>/g' | \
                                          sed 's/^---$/<hr>/g')

# Replace placeholders
sed -i.bak "s/DATE_PLACEHOLDER/${DATE}/g" "$DASHBOARD_FILE"
sed -i.bak "s/TIMESTAMP_PLACEHOLDER/$(date +"%Y-%m-%d %H:%M:%S")/g" "$DASHBOARD_FILE"
sed -i.bak "s|CONTENT_PLACEHOLDER|${HTML_CONTENT}|g" "$DASHBOARD_FILE"
rm "${DASHBOARD_FILE}.bak" 2>/dev/null || true

# Create symlink to latest dashboard
ln -sf "dashboard_${DATE}.html" "${DASHBOARD_DIR}/latest.html"

echo "✅ Dashboard created: $DASHBOARD_FILE"
echo "🌐 View at: file://${DASHBOARD_FILE}"
RENDER

chmod +x scripts/renderers/generate_dashboard.sh

echo "✅ Dashboard renderer created"

# Create notifier stub
cat > scripts/notifiers/notify.sh << 'NOTIFY'
#!/bin/bash
# Send notifications (email, Discord, etc.)

set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../config/env.sh"

DATE=$(date +%Y-%m-%d)
DASHBOARD_FILE="${DASHBOARD_DIR}/dashboard_${DATE}.html"

echo "Sending notification for ${DATE}..."

# Email notification (requires mail command)
if [ -n "${NOTIFICATION_EMAIL}" ]; then
    echo "Your NeuroHelix daily report is ready: file://${DASHBOARD_FILE}" | \
        mail -s "NeuroHelix Daily Report - ${DATE}" "${NOTIFICATION_EMAIL}" || \
        echo "Failed to send email notification"
fi

# Discord webhook notification
if [ -n "${DISCORD_WEBHOOK_URL}" ]; then
    curl -X POST "${DISCORD_WEBHOOK_URL}" \
        -H "Content-Type: application/json" \
        -d "{\"content\": \"🧠 NeuroHelix Daily Report Ready - ${DATE}\n\nView dashboard: file://${DASHBOARD_FILE}\"}" || \
        echo "Failed to send Discord notification"
fi

echo "✅ Notifications sent"
NOTIFY

chmod +x scripts/notifiers/notify.sh

echo "✅ Notifier created"

# Create README
cat > README.md << 'README'
# 🧠 NeuroHelix

## Automated Research & Ideation Ecosystem

NeuroHelix is an AI-driven research automation system that runs daily cycles of discovery, synthesis, and ideation—orchestrated by simple Bash scripts and powered by LLM CLI tools.

### 🎯 Core Concept

A self-contained, model-agnostic AI lab where:
- **Bash provides time** (cron scheduling)
- **Gemini provides thought** (research, analysis, synthesis)
- **You provide judgment** (final approval and direction)

Every morning, wake up to a dashboard of new insights, refined ideas, and actionable recommendations.

### 📁 Project Structure

```
NeuroHelix/
├── config/              # Configuration files
│   ├── env.sh          # Environment variables
│   └── searches.tsv    # Research prompts manifest
├── scripts/            # Automation scripts
│   ├── orchestrator.sh         # Main pipeline coordinator
│   ├── executors/              # Prompt execution
│   ├── aggregators/            # Result aggregation
│   ├── renderers/              # Dashboard generation
│   ├── notifiers/              # Notification delivery
│   └── meta/                   # Self-improvement automation
├── data/               # Data storage
│   ├── prompts/        # Prompt templates
│   ├── outputs/        # Raw execution outputs
│   ├── corpus/         # Historical knowledge base
│   └── reports/        # Aggregated reports
├── dashboards/         # HTML dashboards
├── logs/               # Execution logs
├── templates/          # Reusable templates
└── docs/               # Documentation

```

### 🚀 Quick Start

1. **Configure your environment:**
   ```bash
   # Edit config/env.sh to set your CLI paths and preferences
   nano config/env.sh
   ```

2. **Customize research domains:**
   ```bash
   # Edit config/searches.tsv to define your research areas
   nano config/searches.tsv
   ```

3. **Run manually (test):**
   ```bash
   ./scripts/orchestrator.sh
   ```

4. **Set up daily automation:**
   ```bash
   # Add to crontab (runs daily at 7 AM)
   echo "0 7 * * * cd $(pwd) && ./scripts/orchestrator.sh" | crontab -
   ```

5. **View the dashboard:**
   ```bash
   open dashboards/latest.html
   ```

### 🔧 Configuration

#### Research Domains (`config/searches.tsv`)

Define research areas with priorities:

```tsv
domain	prompt	priority	enabled
AI Research	"What are the most significant breakthroughs in AI research published in the last 24 hours?"	high	true
Tech Trends	"Analyze emerging technology trends in cloud computing"	medium	true
```

#### Environment (`config/env.sh`)

Configure CLI tools, models, and feature flags:

```bash
export GEMINI_CLI="gemini"
export DEFAULT_MODEL="gemini-2.0-flash-exp"
export ENABLE_NOTIFICATIONS="false"
export PARALLEL_EXECUTION="true"
```

### 🎨 Dashboard Features

- **Self-contained HTML** - Single file with embedded styles
- **Executive Summary** - AI-generated key insights
- **Detailed Findings** - Full research results by domain
- **Date Navigation** - Browse historical reports
- **Responsive Design** - Works on desktop and mobile

### 🔄 Daily Workflow

1. **Cron Trigger** - Runs at scheduled time
2. **Prompt Execution** - Parallel execution of research queries
3. **Output Storage** - Structured Markdown with YAML front-matter
4. **Aggregation** - Unified daily report with AI summarization
5. **Visualization** - Interactive HTML dashboard
6. **Notification** - Optional email/Discord alerts

### 🌟 Evolutionary Features

#### Idea Loop (Future)
- Daily summaries feed growing corpus
- Generate new project ideas from patterns
- Validate against market data
- Rank by novelty and potential

#### Recursive Reasoning (Future)
- Cross-reference new ideas with history
- Prune duplicates automatically
- Enrich promising leads

#### Autonomous R&D Flow (Future)
- High-novelty ideas → Auto-generate PRD
- PRD → Project specification (Copilot CLI)
- Spec → Proof-of-concept (Cloud Code)

### 📊 Output Examples

#### Daily Report (`data/reports/daily_report_YYYY-MM-DD.md`)
```markdown
# NeuroHelix Daily Report - 2025-11-07

## Executive Summary
[AI-generated synthesis of key findings]

## Detailed Findings

### AI Research
[Latest breakthroughs and papers]

### Tech Trends
[Emerging patterns and technologies]
```

#### Dashboard (`dashboards/dashboard_YYYY-MM-DD.html`)
Beautiful, self-contained HTML visualization of all findings.

### 🛠️ Requirements

- **Bash** (4.0+)
- **Gemini CLI** or compatible LLM CLI tool
- **cron** (for scheduling)
- Optional: **mail** command (for email notifications)
- Optional: **curl** (for webhook notifications)

### 📝 License

Use freely for personal and commercial projects.

### 🤝 Contributing

This is a personal automation framework, but feel free to fork and adapt to your needs!

---

**Built with ❤️ for autonomous research and continuous ideation**
README

echo "✅ README created"

# Create .gitignore
cat > .gitignore << 'GITIGNORE'
# Logs
logs/
*.log

# Data outputs (exclude from git, too large)
data/outputs/
data/corpus/
data/reports/

# Dashboards (generated, can be excluded)
dashboards/*.html
!dashboards/.gitkeep

# Environment secrets
config/env.local.sh
.env

# System files
.DS_Store
Thumbs.db

# Temporary files
*.tmp
*.bak
*.swp
*~
GITIGNORE

echo "✅ .gitignore created"

# Create placeholder files
touch data/prompts/.gitkeep
touch data/corpus/.gitkeep
touch logs/.gitkeep
touch templates/.gitkeep
touch docs/.gitkeep
touch scripts/meta/.gitkeep
touch dashboards/.gitkeep

echo "✅ Placeholder files created"

echo ""
echo "🎉 NeuroHelix initialization complete!"
echo ""
echo "📋 Next steps:"
echo "1. Review and edit config/env.sh"
echo "2. Customize config/searches.tsv with your research domains"
echo "3. Test the pipeline: ./scripts/orchestrator.sh"
echo "4. Set up cron job: crontab -e"
echo "5. Add: 0 7 * * * cd $(pwd) && ./scripts/orchestrator.sh"
echo ""
echo "📖 See README.md for full documentation"
