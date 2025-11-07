# NeuroHelix Pipeline Flow - Analysis

## Flow Summary
The NeuroHelix pipeline implements an automated research and ideation ecosystem that runs on a daily schedule. The system uses a four-stage pipeline orchestrated by bash scripts and powered by the Gemini CLI for AI processing. The pipeline begins with parallel execution of research prompts, aggregates the results into a unified report, generates an interactive dashboard, and optionally sends notifications.

## Step-by-Step Walkthrough

### 1. Trigger Mechanisms
- The pipeline can be triggered in two ways:
  - Automatically via launchd at 7:00 AM daily (configured in com.neurohelix.daily.plist)
  - Manually by running `./scripts/orchestrator.sh`
- The orchestrator script logs all operations to `logs/orchestrator_TIMESTAMP.log`

### 2. Execution Stage (Step 1)
- Reads research prompts from `config/searches.tsv`
- Each prompt represents a research domain with priority and enabled status
- `run_prompts.sh` executes enabled prompts in parallel up to MAX_PARALLEL_JOBS
- Outputs are stored as Markdown files in `data/outputs/daily/YYYY-MM-DD/`
- Creates `.execution_complete` marker when all prompts finish

### 3. Aggregation Stage (Step 2)
- `aggregate_daily.sh` combines all domain outputs into a single document
- Sends combined content to Gemini CLI for intelligent synthesis
- Generates cross-domain analysis and insights
- Creates daily report in `data/reports/daily_report_YYYY-MM-DD.md`
- Implements idempotency check to avoid re-processing

### 4. Visualization Stage (Step 3)
- `generate_dashboard.sh` converts daily report into interactive HTML
- Creates dashboard at `dashboards/dashboard_YYYY-MM-DD.html`
- Maintains `dashboards/latest.html` symlink for easy access
- Includes styling and interactive features

### 5. Notification Stage (Step 4 - Optional)
- Only runs if ENABLE_NOTIFICATIONS=true in env.sh
- Can be configured for email or Discord notifications
- Sends links to the daily dashboard and report
- Logs notification status in the orchestrator log

## Decision Logic

### Execution Stage Decisions
1. **Prompt Selection**
   - Only enabled=true prompts from searches.tsv are executed
   - Prompts are prioritized (high/medium/low)

2. **Parallel Processing**
   - Limited by MAX_PARALLEL_JOBS setting
   - Jobs are queued if limit is reached

### Aggregation Stage Decisions
1. **Idempotency Check**
   - Skips if report exists and contains "## End of Report"
   - Can be forced by deleting existing report

2. **AI Synthesis**
   - Only processes new outputs
   - Maintains context across domains

### Dashboard Generation Decisions
1. **File Management**
   - Creates new dashboard file for each date
   - Updates latest.html symlink
   - Preserves historical dashboards

### Notification Decisions
1. **Feature Flag**
   - Only sends if ENABLE_NOTIFICATIONS=true
   - Configurable notification channels

## Error Handling

### Execution Stage
- Logs individual prompt failures
- Continues processing other prompts
- Marks failed prompts in output

### Aggregation Stage
- Validates input directory exists
- Checks for minimum required outputs
- Handles missing or incomplete files

### Dashboard Stage
- Verifies report file exists
- Maintains consistent styling
- Handles missing data gracefully

### General Error Handling
- All scripts use set -euo pipefail
- Comprehensive logging
- Preserves partial results
- Clean exit status reporting

## Recommendations & Ideas

1. **Resilience Improvements**
   - Add retry logic for failed prompts
   - Implement timeout handling
   - Add progress tracking for long runs

2. **Performance Optimizations**
   - Dynamic MAX_PARALLEL_JOBS based on system load
   - Caching of common prompt contexts
   - Incremental dashboard updates

3. **Feature Enhancements**
   - Add real-time progress dashboard
   - Implement prompt result validation
   - Add historical trend analysis
   - Create API endpoints for remote monitoring

4. **Monitoring & Debugging**
   - Add structured logging format
   - Create monitoring dashboard
   - Implement alert thresholds
   - Add performance metrics

5. **Data Management**
   - Implement data retention policies
   - Add backup/restore functionality
   - Create data exploration tools
   - Add export/import capabilities
