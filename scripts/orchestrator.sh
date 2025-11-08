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

# Step 2.5: Extract tags and categories
log "🏷️  Step 2.5: Extracting tags and categories..."
"${PROJECT_ROOT}/scripts/aggregators/extract_tags.sh" 2>&1 | tee -a "$LOG_FILE"

# Step 2.75: Check for failures and send notifications
if [ "${ENABLE_FAILURE_NOTIFICATIONS:-false}" = "true" ]; then
    log "📧 Step 2.75: Checking for prompt failures and sending notifications..."
    "${PROJECT_ROOT}/scripts/notifiers/notify_failures.sh" 2>&1 | tee -a "$LOG_FILE" || true
else
    log "⏭️  Step 2.75: Failure notifications disabled"
fi

# Step 3: Generate dashboard
log "🎨 Step 3: Generating dashboard..."
"${PROJECT_ROOT}/scripts/renderers/generate_dashboard.sh" 2>&1 | tee -a "$LOG_FILE"

# Step 4: Export static site payload
log "📦 Step 4: Exporting static site payload..."
"${PROJECT_ROOT}/scripts/renderers/export_site_payload.sh" 2>&1 | tee -a "$LOG_FILE"

# Step 5: Publish static site (if enabled)
if [ "${ENABLE_STATIC_SITE_PUBLISHING:-false}" = "true" ]; then
    log "🌐 Step 5: Publishing static site..."
    "${PROJECT_ROOT}/scripts/publish/static_site.sh" 2>&1 | tee -a "$LOG_FILE"
else
    log "⏭️  Step 5: Static site publishing disabled"
fi

# Step 6: Send notification (optional)
if [ "${ENABLE_NOTIFICATIONS:-false}" = "true" ]; then
    log "📧 Step 6: Sending notification..."
    "${PROJECT_ROOT}/scripts/notifiers/notify.sh" 2>&1 | tee -a "$LOG_FILE"
fi

log "✅ Pipeline completed successfully for ${DATE}"
