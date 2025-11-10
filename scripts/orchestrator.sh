#!/bin/bash
# Main orchestration script - runs daily via cron or manually with maintenance flags
#
# Usage:
#   ./scripts/orchestrator.sh                          # Normal daily run
#   ./scripts/orchestrator.sh --cleanup-all            # Full workspace cleanup
#   ./scripts/orchestrator.sh --reprocess-today        # Force reprocess today
#   ./scripts/orchestrator.sh --cleanup-all --dry-run  # Preview cleanup without executing
#   ./scripts/orchestrator.sh --reprocess-today --yes  # Skip confirmation prompt
#
# Flags:
#   --cleanup-all, --reset-workspace    Perform full cleanup of all generated content
#   --reprocess-today, --force-today    Force reprocess current day's pipeline
#   --dry-run                           Preview actions without executing
#   --yes                               Skip confirmation prompts
#   --allow-dirty                       Bypass git working tree cleanliness check
#   --allow-abort                       Terminate running pipeline if needed

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${PROJECT_ROOT}/config/env.sh"

# Load helper libraries
source "${PROJECT_ROOT}/scripts/lib/audit.sh"
source "${PROJECT_ROOT}/scripts/lib/git_safety.sh"
source "${PROJECT_ROOT}/scripts/lib/cloudflare.sh"
source "${PROJECT_ROOT}/scripts/lib/cleanup.sh"
source "${PROJECT_ROOT}/scripts/lib/reprocess.sh"

# Parse command-line flags
MODE="normal"
DRY_RUN="false"
AUTO_YES="false"
ALLOW_DIRTY="false"
ALLOW_ABORT="false"

while [[ $# -gt 0 ]]; do
    case $1 in
        --cleanup-all|--reset-workspace)
            if [ "${MODE}" != "normal" ]; then
                echo "❌ Error: Cannot combine --cleanup-all with --reprocess-today"
                exit 1
            fi
            MODE="cleanup"
            shift
            ;;
        --reprocess-today|--force-today)
            if [ "${MODE}" != "normal" ]; then
                echo "❌ Error: Cannot combine --reprocess-today with --cleanup-all"
                exit 1
            fi
            MODE="reprocess"
            shift
            ;;
        --dry-run)
            DRY_RUN="true"
            shift
            ;;
        --yes)
            AUTO_YES="true"
            shift
            ;;
        --allow-dirty)
            ALLOW_DIRTY="true"
            shift
            ;;
        --allow-abort)
            ALLOW_ABORT="true"
            shift
            ;;
        *)
            echo "❌ Error: Unknown option: $1"
            echo ""
            echo "Usage: $0 [--cleanup-all|--reprocess-today] [--dry-run] [--yes] [--allow-dirty] [--allow-abort]"
            exit 1
            ;;
    esac
done

# Guard against LaunchD invoking maintenance modes
if [ "${MODE}" != "normal" ] && [ -n "${LAUNCHED_BY_LAUNCHD:-}" ]; then
    echo "❌ Error: Maintenance modes (--cleanup-all, --reprocess-today) cannot be invoked by LaunchD"
    echo "   These are operator-only commands"
    exit 1
fi

# ============================================================================
# CLEANUP MODE
# ============================================================================
if [ "${MODE}" = "cleanup" ]; then
    CLEANUP_LOG=$(create_maintenance_log "cleanup")

    log_maintenance "${CLEANUP_LOG}" "🧹 NeuroHelix Workspace Cleanup"
    log_maintenance "${CLEANUP_LOG}" "================================"
    log_maintenance "${CLEANUP_LOG}" ""
    log_maintenance "${CLEANUP_LOG}" "Operator: ${USER}"
    log_maintenance "${CLEANUP_LOG}" "Timestamp: $(date)"
    log_maintenance "${CLEANUP_LOG}" "Dry run: ${DRY_RUN}"
    log_maintenance "${CLEANUP_LOG}" ""

    # Git safety check
    if ! check_git_safety "${ALLOW_DIRTY}" "${CLEANUP_LOG}"; then
        exit 1
    fi
    log_maintenance "${CLEANUP_LOG}" ""

    # Print cleanup plan
    print_cleanup_plan "${CLEANUP_LOG}"

    # Cloudflare retraction preview
    if [ -n "${CLOUDFLARE_API_TOKEN:-}" ]; then
        DEPLOY_ID=$(get_latest_deployment_id "${CLOUDFLARE_PROJECT_NAME}")
        if [ -n "${DEPLOY_ID}" ]; then
            log_maintenance "${CLEANUP_LOG}" "Cloudflare deployment to retract: ${DEPLOY_ID}"
        else
            log_maintenance "${CLEANUP_LOG}" "Cloudflare deployment: No active deployment found"
        fi
    else
        log_maintenance "${CLEANUP_LOG}" "Cloudflare deployment: Skipped (no API token)"
    fi
    log_maintenance "${CLEANUP_LOG}" ""

    # Confirmation prompt
    if [ "${AUTO_YES}" = "false" ] && [ "${DRY_RUN}" = "false" ]; then
        log_maintenance "${CLEANUP_LOG}" "⚠️  WARNING: This will permanently delete all generated artifacts!"
        log_maintenance "${CLEANUP_LOG}" ""
        read -p "Do you want to proceed with cleanup? [y/N] " -n 1 -r
        echo ""

        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_maintenance "${CLEANUP_LOG}" "❌ Cleanup cancelled by user"
            exit 0
        fi
        log_maintenance "${CLEANUP_LOG}" ""
    fi

    # Execute cleanup
    if ! execute_cleanup "${CLEANUP_LOG}" "${DRY_RUN}"; then
        log_maintenance "${CLEANUP_LOG}" ""
        log_maintenance "${CLEANUP_LOG}" "❌ Cleanup completed with errors"
        audit_log "$(create_cleanup_audit_entry "${USER}" "${DRY_RUN}" "$(get_git_status)" "$(get_cleanup_paths_json)" "")"
        exit 1
    fi

    log_maintenance "${CLEANUP_LOG}" ""

    # Cloudflare retraction
    RETRACT_DEPLOY_ID=$(retract_deployment "${CLOUDFLARE_PROJECT_NAME}" "${CLEANUP_LOG}" "${DRY_RUN}")

    # Audit logging
    audit_log "$(create_cleanup_audit_entry "${USER}" "${DRY_RUN}" "$(get_git_status)" "$(get_cleanup_paths_json)" "${RETRACT_DEPLOY_ID}")"

    log_maintenance "${CLEANUP_LOG}" ""
    log_maintenance "${CLEANUP_LOG}" "✅ Cleanup completed successfully!"
    log_maintenance "${CLEANUP_LOG}" ""
    log_maintenance "${CLEANUP_LOG}" "Next steps:"
    log_maintenance "${CLEANUP_LOG}" "  Run ./scripts/orchestrator.sh to generate a fresh report"
    log_maintenance "${CLEANUP_LOG}" ""
    log_maintenance "${CLEANUP_LOG}" "Log file: ${CLEANUP_LOG}"

    exit 0
fi

# ============================================================================
# REPROCESS MODE
# ============================================================================
if [ "${MODE}" = "reprocess" ]; then
    TODAY=$(get_today)
    REPROCESS_LOG=$(create_maintenance_log "reprocess")

    log_maintenance "${REPROCESS_LOG}" "🔄 NeuroHelix Force Reprocess"
    log_maintenance "${REPROCESS_LOG}" "=============================="
    log_maintenance "${REPROCESS_LOG}" ""
    log_maintenance "${REPROCESS_LOG}" "Operator: ${USER}"
    log_maintenance "${REPROCESS_LOG}" "Date: ${TODAY}"
    log_maintenance "${REPROCESS_LOG}" "Timestamp: $(date)"
    log_maintenance "${REPROCESS_LOG}" "Dry run: ${DRY_RUN}"
    log_maintenance "${REPROCESS_LOG}" ""

    # Git safety check
    if ! check_git_safety "${ALLOW_DIRTY}" "${REPROCESS_LOG}"; then
        exit 1
    fi
    log_maintenance "${REPROCESS_LOG}" ""

    # Check for running pipeline
    LOCK_BEHAVIOR="clean"
    if is_pipeline_running; then
        LOCK_BEHAVIOR="blocked"
        PIPELINE_PID=$(get_pipeline_pid)

        log_maintenance "${REPROCESS_LOG}" "⚠️  Pipeline is currently running (PID: ${PIPELINE_PID})"

        if [ "${ALLOW_ABORT}" = "false" ]; then
            log_maintenance "${REPROCESS_LOG}" "❌ Cannot proceed while pipeline is active"
            log_maintenance "${REPROCESS_LOG}" "   Use --allow-abort to terminate the running pipeline"
            audit_log "$(create_reprocess_audit_entry "${USER}" "${TODAY}" "${DRY_RUN}" "${LOCK_BEHAVIOR}" "0" "")"
            exit 1
        fi

        if [ "${DRY_RUN}" = "false" ]; then
            if ! terminate_pipeline "${REPROCESS_LOG}"; then
                log_maintenance "${REPROCESS_LOG}" "❌ Failed to terminate running pipeline"
                exit 1
            fi
            LOCK_BEHAVIOR="aborted"
        else
            log_maintenance "${REPROCESS_LOG}" "   [DRY RUN] Would terminate running pipeline"
            LOCK_BEHAVIOR="would_abort"
        fi
        log_maintenance "${REPROCESS_LOG}" ""
    fi

    # Print reprocess plan
    print_reprocess_plan "${TODAY}" "${REPROCESS_LOG}"

    # Confirmation prompt
    if [ "${AUTO_YES}" = "false" ] && [ "${DRY_RUN}" = "false" ]; then
        log_maintenance "${REPROCESS_LOG}" "⚠️  WARNING: This will delete today's data and rerun the entire pipeline!"
        log_maintenance "${REPROCESS_LOG}" ""
        read -p "Do you want to proceed with reprocessing ${TODAY}? [y/N] " -n 1 -r
        echo ""

        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_maintenance "${REPROCESS_LOG}" "❌ Reprocess cancelled by user"
            exit 0
        fi
        log_maintenance "${REPROCESS_LOG}" ""
    fi

    # Cleanup today's artifacts
    if ! cleanup_today "${TODAY}" "${REPROCESS_LOG}" "${DRY_RUN}"; then
        log_maintenance "${REPROCESS_LOG}" ""
        log_maintenance "${REPROCESS_LOG}" "❌ Cleanup failed"
        audit_log "$(create_reprocess_audit_entry "${USER}" "${TODAY}" "${DRY_RUN}" "${LOCK_BEHAVIOR}" "0" "")"
        exit 1
    fi

    log_maintenance "${REPROCESS_LOG}" ""

    if [ "${DRY_RUN}" = "true" ]; then
        log_maintenance "${REPROCESS_LOG}" "✅ Dry run completed successfully!"
        log_maintenance "${REPROCESS_LOG}" ""
        log_maintenance "${REPROCESS_LOG}" "To execute, run without --dry-run flag"
        log_maintenance "${REPROCESS_LOG}" ""
        log_maintenance "${REPROCESS_LOG}" "Log file: ${REPROCESS_LOG}"
        audit_log "$(create_reprocess_audit_entry "${USER}" "${TODAY}" "${DRY_RUN}" "${LOCK_BEHAVIOR}" "0" "")"
        exit 0
    fi

    # Execute pipeline with manual override flag
    log_maintenance "${REPROCESS_LOG}" "🚀 Starting pipeline with manual override tag..."
    log_maintenance "${REPROCESS_LOG}" ""

    export RUN_MODE="manual_override"
    export MANUAL_OVERRIDE_OPERATOR="${USER}"
    export MANUAL_OVERRIDE_REASON="force reprocess"

    PIPELINE_START=$(date +%s)

    # Run the normal pipeline (continue to normal execution below)
    MODE="normal"
fi

# ============================================================================
# NORMAL PIPELINE EXECUTION
# ============================================================================

DATE=$(date +%Y-%m-%d)
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)

# Use reprocess log if in reprocess mode, otherwise create new log
if [ -n "${REPROCESS_LOG:-}" ]; then
    LOG_FILE="${REPROCESS_LOG}"
else
    LOG_FILE="${PROJECT_ROOT}/logs/orchestrator_${TIMESTAMP}.log"
fi

log() {
    echo "[$(date +%Y-%m-%d\ %H:%M:%S)] $*" | tee -a "$LOG_FILE"
}

# Create pipeline lock
if [ -z "${REPROCESS_LOG:-}" ]; then
    # Only create lock for normal runs, not reprocess (already handled)
    create_pipeline_lock
    trap remove_pipeline_lock EXIT
fi

# Tag run as manual override if applicable
if [ "${RUN_MODE:-normal}" = "manual_override" ]; then
    log "🏷️  RUN MODE: Manual Override"
    log "   Operator: ${MANUAL_OVERRIDE_OPERATOR}"
    log "   Reason: ${MANUAL_OVERRIDE_REASON}"
    log ""
fi

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

# Step 4.5: Export source manifests and raw artifacts
log "📂 Step 4.5: Exporting source manifests and raw artifacts..."
bash "${PROJECT_ROOT}/scripts/renderers/export_source_manifest.sh" 2>&1 | tee -a "$LOG_FILE"

# Step 5: Publish static site (if enabled)
DEPLOY_ID=""
if [ "${ENABLE_STATIC_SITE_PUBLISHING:-false}" = "true" ]; then
    log "🌐 Step 5: Publishing static site..."
    "${PROJECT_ROOT}/scripts/publish/static_site.sh" 2>&1 | tee -a "$LOG_FILE"

    # Try to extract deployment ID from latest.json
    if [ -f "${PROJECT_ROOT}/logs/publishing/latest.json" ]; then
        DEPLOY_ID=$(grep -o '"deploy_url":"[^"]*"' "${PROJECT_ROOT}/logs/publishing/latest.json" | cut -d'"' -f4 || echo "")
    fi
else
    log "⏭️  Step 5: Static site publishing disabled"
fi

# Step 6: Send notification (optional)
if [ "${ENABLE_NOTIFICATIONS:-false}" = "true" ]; then
    log "📧 Step 6: Sending notification..."
    "${PROJECT_ROOT}/scripts/notifiers/notify.sh" 2>&1 | tee -a "$LOG_FILE"
fi

log "✅ Pipeline completed successfully for ${DATE}"

# If this was a reprocess run, finalize the audit log
if [ -n "${REPROCESS_LOG:-}" ]; then
    PIPELINE_END=$(date +%s)
    PIPELINE_DURATION=$((PIPELINE_END - PIPELINE_START))

    log_maintenance "${REPROCESS_LOG}" ""
    log_maintenance "${REPROCESS_LOG}" "✅ Reprocess completed successfully!"
    log_maintenance "${REPROCESS_LOG}" "   Duration: ${PIPELINE_DURATION}s"
    log_maintenance "${REPROCESS_LOG}" ""
    log_maintenance "${REPROCESS_LOG}" "Log file: ${REPROCESS_LOG}"

    audit_log "$(create_reprocess_audit_entry "${USER}" "${DATE}" "false" "${LOCK_BEHAVIOR}" "${PIPELINE_DURATION}" "${DEPLOY_ID}")"
fi
