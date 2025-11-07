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
