#!/bin/bash
# Reprocess operations for NeuroHelix
# Handles force reprocessing of today's pipeline

# Lock file for pipeline execution
PIPELINE_LOCK_FILE="${PROJECT_ROOT}/data/runtime/pipeline.lock"

# Check if pipeline is currently running
# Returns: 0 if not running, 1 if running
is_pipeline_running() {
    if [ -f "${PIPELINE_LOCK_FILE}" ]; then
        local lock_pid=$(cat "${PIPELINE_LOCK_FILE}" 2>/dev/null || echo "")
        if [ -n "${lock_pid}" ] && kill -0 "${lock_pid}" 2>/dev/null; then
            return 0  # Running
        else
            # Stale lock file
            rm -f "${PIPELINE_LOCK_FILE}"
            return 1  # Not running
        fi
    fi
    return 1  # Not running
}

# Get PID from lock file
# Returns: PID or empty string
get_pipeline_pid() {
    if [ -f "${PIPELINE_LOCK_FILE}" ]; then
        cat "${PIPELINE_LOCK_FILE}" 2>/dev/null || echo ""
    else
        echo ""
    fi
}

# Create pipeline lock
# Usage: create_pipeline_lock
create_pipeline_lock() {
    echo "$$" > "${PIPELINE_LOCK_FILE}"
}

# Remove pipeline lock
# Usage: remove_pipeline_lock
remove_pipeline_lock() {
    rm -f "${PIPELINE_LOCK_FILE}"
}

# Terminate running pipeline
# Usage: terminate_pipeline <log_file>
# Returns: 0 on success, 1 on failure
terminate_pipeline() {
    local log_file="$1"
    local pid=$(get_pipeline_pid)

    if [ -z "${pid}" ]; then
        log_maintenance "${log_file}" "⚠️  No pipeline PID found"
        return 0
    fi

    log_maintenance "${log_file}" "🛑 Terminating pipeline (PID: ${pid})..."

    # Send SIGTERM
    if kill -TERM "${pid}" 2>/dev/null; then
        log_maintenance "${log_file}" "   Sent SIGTERM to process ${pid}"

        # Wait up to 10 seconds for graceful shutdown
        local wait_count=0
        while kill -0 "${pid}" 2>/dev/null && [ ${wait_count} -lt 10 ]; do
            sleep 1
            wait_count=$((wait_count + 1))
        done

        if kill -0 "${pid}" 2>/dev/null; then
            # Still running, send SIGKILL
            log_maintenance "${log_file}" "   Process still running, sending SIGKILL..."
            kill -KILL "${pid}" 2>/dev/null || true
            sleep 1
        fi

        if kill -0 "${pid}" 2>/dev/null; then
            log_maintenance "${log_file}" "❌ Failed to terminate process ${pid}"
            return 1
        else
            log_maintenance "${log_file}" "✅ Pipeline terminated successfully"
            remove_pipeline_lock
            return 0
        fi
    else
        log_maintenance "${log_file}" "⚠️  Process ${pid} not found (may have already exited)"
        remove_pipeline_lock
        return 0
    fi
}

# Get today's date
# Returns: YYYY-MM-DD
get_today() {
    date +%Y-%m-%d
}

# Define paths for today's artifacts
get_today_cleanup_paths() {
    local today="$1"

    cat <<EOF
data/outputs/daily/${today}
data/reports/daily_report_${today}.md
data/publishing/${today}.json
data/publishing/tags_${today}.json
dashboards/dashboard_${today}.html
logs/prompt_execution_${today}.log
logs/orchestrator_*${today}*.log
data/runtime/execution_ledger_${today}.json
EOF
}

# Print reprocess plan
# Usage: print_reprocess_plan <today> <log_file>
print_reprocess_plan() {
    local today="$1"
    local log_file="$2"

    log_maintenance "${log_file}" "📋 Reprocess Plan for ${today}:"
    log_maintenance "${log_file}" ""
    log_maintenance "${log_file}" "The following paths will be removed:"

    local paths=$(get_today_cleanup_paths "${today}")
    local path_count=0

    while IFS= read -r path; do
        local full_path="${PROJECT_ROOT}/${path}"

        # Handle glob patterns
        if [[ "$path" == *"*"* ]]; then
            local matches=$(ls -1 "${PROJECT_ROOT}/$(dirname "${path}")/$(basename "${path}")" 2>/dev/null | wc -l | tr -d ' ')
            if [ "${matches}" -gt 0 ]; then
                log_maintenance "${log_file}" "   ✓ ${path} (${matches} files)"
                path_count=$((path_count + matches))
            fi
        else
            if [ -e "${full_path}" ]; then
                local size=$(du -sh "${full_path}" 2>/dev/null | cut -f1 || echo "0")
                log_maintenance "${log_file}" "   ✓ ${path} (${size})"
                path_count=$((path_count + 1))
            fi
        fi
    done <<< "$paths"

    log_maintenance "${log_file}" ""
    log_maintenance "${log_file}" "Total paths/files to remove: ${path_count}"
    log_maintenance "${log_file}" ""
    log_maintenance "${log_file}" "Pipeline steps that will be executed:"
    log_maintenance "${log_file}" "   1. Execute research prompts"
    log_maintenance "${log_file}" "   2. Aggregate results"
    log_maintenance "${log_file}" "   3. Extract tags and categories"
    log_maintenance "${log_file}" "   4. Generate dashboard"
    log_maintenance "${log_file}" "   5. Export static site payload"
    log_maintenance "${log_file}" "   6. Publish static site (if enabled)"
    log_maintenance "${log_file}" ""
}

# Execute cleanup for today's artifacts
# Usage: cleanup_today <today> <log_file> <dry_run>
# Returns: 0 on success, 1 on failure
cleanup_today() {
    local today="$1"
    local log_file="$2"
    local dry_run="${3:-false}"

    log_maintenance "${log_file}" "🗑️  Cleaning up today's artifacts (${today})..."
    log_maintenance "${log_file}" ""

    local success_count=0
    local fail_count=0
    local skip_count=0

    local paths=$(get_today_cleanup_paths "${today}")

    while IFS= read -r path; do
        local full_path="${PROJECT_ROOT}/${path}"

        # Handle glob patterns
        if [[ "$path" == *"*"* ]]; then
            local pattern_dir=$(dirname "${path}")
            local pattern_file=$(basename "${path}")
            local matches=($(ls -1 "${PROJECT_ROOT}/${pattern_dir}/${pattern_file}" 2>/dev/null || true))

            if [ ${#matches[@]} -eq 0 ]; then
                skip_count=$((skip_count + 1))
                continue
            fi

            for match in "${matches[@]}"; do
                if [ "${dry_run}" = "true" ]; then
                    log_maintenance "${log_file}" "   [DRY RUN] Would remove: ${match}"
                    success_count=$((success_count + 1))
                else
                    if rm -f "${match}" 2>/dev/null; then
                        log_maintenance "${log_file}" "   ✓ Removed: ${match}"
                        success_count=$((success_count + 1))
                    else
                        log_maintenance "${log_file}" "   ✗ Failed to remove: ${match}"
                        fail_count=$((fail_count + 1))
                    fi
                fi
            done
        else
            if [ ! -e "${full_path}" ]; then
                skip_count=$((skip_count + 1))
                continue
            fi

            if [ "${dry_run}" = "true" ]; then
                log_maintenance "${log_file}" "   [DRY RUN] Would remove: ${path}"
                success_count=$((success_count + 1))
            else
                if rm -rf "${full_path}" 2>/dev/null; then
                    log_maintenance "${log_file}" "   ✓ Removed: ${path}"
                    success_count=$((success_count + 1))
                else
                    log_maintenance "${log_file}" "   ✗ Failed to remove: ${path}"
                    fail_count=$((fail_count + 1))
                fi
            fi
        fi
    done <<< "$paths"

    log_maintenance "${log_file}" ""
    log_maintenance "${log_file}" "Cleanup summary:"
    log_maintenance "${log_file}" "   Removed: ${success_count}"
    log_maintenance "${log_file}" "   Failed: ${fail_count}"
    log_maintenance "${log_file}" "   Skipped (not found): ${skip_count}"

    if [ ${fail_count} -gt 0 ]; then
        return 1
    fi

    return 0
}

# Export functions
export -f is_pipeline_running
export -f get_pipeline_pid
export -f create_pipeline_lock
export -f remove_pipeline_lock
export -f terminate_pipeline
export -f get_today
export -f get_today_cleanup_paths
export -f print_reprocess_plan
export -f cleanup_today
