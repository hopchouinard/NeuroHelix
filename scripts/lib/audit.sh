#!/bin/bash
# Audit logging library for maintenance operations
# Provides structured logging to both text logs and JSONL audit trail

# Initialize audit log paths
AUDIT_JSONL="${PROJECT_ROOT}/data/runtime/audit.jsonl"
MAINTENANCE_LOG_DIR="${PROJECT_ROOT}/logs/maintenance"

# Ensure directories exist
mkdir -p "${MAINTENANCE_LOG_DIR}"
mkdir -p "$(dirname "${AUDIT_JSONL}")"

# Create maintenance log file with timestamp
# Usage: create_maintenance_log <action_name>
# Returns: log file path
create_maintenance_log() {
    local action_name="$1"
    local timestamp=$(date +%Y-%m-%dT%H%M%S)
    local log_file="${MAINTENANCE_LOG_DIR}/${action_name}_${timestamp}.log"
    touch "${log_file}"
    echo "${log_file}"
}

# Log to maintenance file
# Usage: log_maintenance <log_file> <message>
log_maintenance() {
    local log_file="$1"
    shift
    echo "[$(date +%Y-%m-%d\ %H:%M:%S)] $*" | tee -a "${log_file}"
}

# Append structured entry to audit.jsonl
# Usage: audit_log <json_object>
audit_log() {
    local json_object="$1"
    echo "${json_object}" >> "${AUDIT_JSONL}"
}

# Create cleanup audit entry
# Usage: create_cleanup_audit_entry <operator> <dry_run> <git_status> <target_paths_json> <cloudflare_deploy_id>
create_cleanup_audit_entry() {
    local operator="$1"
    local dry_run="$2"
    local git_status="$3"
    local target_paths="$4"
    local cloudflare_deploy_id="${5:-null}"

    cat <<EOF
{"action":"cleanup_all","operator":"${operator}","timestamp":"$(date -u +"%Y-%m-%dT%H:%M:%SZ")","dry_run":${dry_run},"git_status":"${git_status}","target_paths":${target_paths},"cloudflare_deploy_id":"${cloudflare_deploy_id}"}
EOF
}

# Create reprocess audit entry
# Usage: create_reprocess_audit_entry <operator> <date> <dry_run> <lock_behavior> <pipeline_duration> <deploy_id>
create_reprocess_audit_entry() {
    local operator="$1"
    local date="$2"
    local dry_run="$3"
    local lock_behavior="$4"
    local pipeline_duration="${5:-0}"
    local deploy_id="${6:-null}"

    cat <<EOF
{"action":"reprocess_today","operator":"${operator}","date":"${date}","timestamp":"$(date -u +"%Y-%m-%dT%H:%M:%SZ")","dry_run":${dry_run},"manual_override":true,"lock_behavior":"${lock_behavior}","pipeline_duration_seconds":${pipeline_duration},"deploy_id":"${deploy_id}"}
EOF
}

# Get git status description
# Returns: "clean" or "dirty"
get_git_status() {
    if [ -z "$(git status --porcelain)" ]; then
        echo "clean"
    else
        echo "dirty"
    fi
}

# Export functions
export -f create_maintenance_log
export -f log_maintenance
export -f audit_log
export -f create_cleanup_audit_entry
export -f create_reprocess_audit_entry
export -f get_git_status
