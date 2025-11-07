# 🧠 NeuroHelix

## Automated Research & Ideation Ecosystem

NeuroHelix is a **production-ready** AI-driven research automation system that runs daily cycles of discovery, synthesis, and ideation—orchestrated by Bash scripts and powered by Gemini CLI.

### 🎯 Core Concept

A self-contained, automated AI research lab where:
- **LaunchD provides scheduling** (macOS automation)
- **Gemini CLI provides intelligence** (research, analysis, synthesis)
- **You provide direction** (research domains, iterative refinement)

Every morning, wake up to an intelligent synthesis dashboard with cross-domain insights, thematic analysis, and actionable recommendations.

### ✨ Key Features

✅ **20 Curated Research Prompts** - 5 categories (Research, Market, Ideation, Analysis, Meta)  
✅ **Intelligent Synthesis** - Cross-domain analysis, not simple concatenation  
✅ **Full Idempotency** - Re-runs complete in <1 second, safe for repeated execution  
✅ **Context-Aware Prompts** - Historical analysis, temporal awareness, structured references  
✅ **LaunchD Automation** - Daily scheduling at 7 AM (or custom times)  
✅ **Beautiful Dashboards** - Self-contained HTML with responsive design  
✅ **Comprehensive Logging** - Detailed execution traces for debugging  

### 📁 Project Structure

```
NeuroHelix/
├── config/
│   ├── env.sh              # Gemini CLI configuration
│   └── searches.tsv        # 20 research prompts (5 categories)
├── scripts/
│   ├── orchestrator.sh     # Main pipeline coordinator
│   ├── executors/          # Prompt execution with context injection
│   ├── aggregators/        # Intelligent synthesis engine
│   ├── renderers/          # Dashboard HTML generation
│   ├── notifiers/          # Notification hooks
│   ├── install_automation.sh    # LaunchD setup
│   └── uninstall_automation.sh  # LaunchD cleanup
├── launchd/
│   └── com.neurohelix.daily.plist  # Scheduling template
├── data/
│   ├── outputs/daily/      # Raw prompt outputs (organized by date)
│   └── reports/            # Daily synthesized reports
├── dashboards/             # HTML dashboards (one per day)
├── logs/                   # Execution logs
├── templates/              # Reusable templates
└── docs/                   # Comprehensive documentation
```

### 🚀 Quick Start

1. **Prerequisites:**
   - macOS system
   - [Gemini CLI](https://github.com/replit/gemini-cli) installed and configured
   - Bash 4.0+ (standard on macOS)

2. **Test the system:**
   ```bash
   ./scripts/orchestrator.sh
   ```
   
   This runs all 20 prompts, generates synthesis report, and creates dashboard.

3. **Install daily automation:**
   ```bash
   ./install_automation.sh
   ```
   
   Sets up launchd job to run daily at 7:00 AM.

4. **View results:**
   ```bash
   # Today's dashboard
   open dashboards/dashboard_$(date +%Y-%m-%d).html
   
   # Today's report
   cat data/reports/daily_report_$(date +%Y-%m-%d).md
   ```

5. **Check automation status:**
   ```bash
   launchctl list | grep neurohelix
   ```

### 🔧 Configuration

#### Research Prompts (`config/searches.tsv`)

**20 pre-configured prompts across 5 categories:**

- **Research (5):** Latest developments, breakthroughs, papers, methodologies, applications
- **Market (5):** Funding trends, startup analysis, competitive intelligence, market dynamics
- **Ideation (4):** Concept synthesis, novelty filtering, continuity building, opportunity mapping
- **Analysis (4):** Impact assessment, risk analysis, strategic evaluation, trend correlation
- **Meta (2):** Project reflection, system optimization

```tsv
domain	category	prompt	priority	enabled
Concept Synthesizer	Ideation	"Generate 5-10 innovative project ideas..."	9	true
Novelty Filter	Ideation	"Evaluate yesterday's top 5 ideas against..."	8	true
```

#### Environment (`config/env.sh`)

```bash
# Gemini CLI Configuration
export GEMINI_CLI="gemini"
export GEMINI_MODEL="gemini-2.0-flash-exp"
export GEMINI_OUTPUT_FORMAT="text"
export GEMINI_APPROVAL_MODE="false"
export GEMINI_YOLO_MODE="true"
export GEMINI_DEBUG="false"

# Execution settings
export MAX_PARALLEL_JOBS=5
export PROMPT_TIMEOUT=120  # seconds
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

### 🎨 Dashboard Features

- **Intelligent Synthesis** - Cross-domain thematic analysis, not simple concatenation
- **Executive Summary** - 200-300 word strategic overview
- **Key Themes** - Organized by insight clusters, not source domains
- **Strategic Implications** - Actionable business and technical recommendations
- **Self-contained HTML** - Single file with embedded CSS, works offline
- **Date-specific URLs** - `dashboard_YYYY-MM-DD.html` for historical browsing
- **Responsive Design** - Mobile-friendly layout

### 🔄 Daily Workflow

1. **LaunchD Trigger** - Runs at 7:00 AM (configurable)
2. **Context-Aware Execution** - 20 prompts with temporal context injection
3. **Structured Output** - Organized by date in `data/outputs/daily/YYYY-MM-DD/`
4. **Intelligent Aggregation** - Cross-domain synthesis with thematic grouping
5. **Dashboard Generation** - Beautiful HTML with embedded analytics
6. **Idempotent Re-runs** - Safe to execute multiple times (completes in <1s)

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
- **[STATUS.md](ai_dev_logs/STATUS.md)** - Complete implementation details

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

#### Dashboard (`dashboards/dashboard_YYYY-MM-DD.html`)
Responsive HTML with embedded CSS featuring:
- Executive summary cards
- Thematic insight sections  
- Strategic recommendations
- Historical trend indicators

### 🛠️ Requirements

- **macOS** (tested on Monterey+)
- **Bash** 4.0+ (standard on macOS)
- **[Gemini CLI](https://github.com/replit/gemini-cli)** - Google's Gemini CLI tool
- **LaunchD** (built into macOS)
- Optional: **curl** (for webhook notifications)

### 📎 Management Commands

```bash
# Check automation status
launchctl list | grep neurohelix

# Manual execution
launchctl start com.neurohelix.daily

# View logs  
tail -f logs/launchd_stdout.log
tail -f logs/launchd_stderr.log

# Uninstall automation
./uninstall_automation.sh

# Check today's outputs
ls -lh data/reports/daily_report_$(date +%Y-%m-%d).md
ls -lh dashboards/dashboard_$(date +%Y-%m-%d).html
```

### 🔍 System Status

✅ **Production Ready** - All major features implemented and tested  
✅ **Fully Automated** - Daily execution via launchd  
✅ **Intelligent Pipeline** - Context-aware prompts with synthesis  
✅ **Comprehensive Documentation** - Setup, management, troubleshooting guides  

See [STATUS.md](ai_dev_logs/STATUS.md) for complete implementation details.

### 📝 License

Use freely for personal and commercial projects.

---

**Built with ❤️ for autonomous research intelligence**
