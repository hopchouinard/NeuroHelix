#!/bin/bash
# Telemetry logging library for NeuroHelix
# Provides structured execution tracking and monitoring

# Global variables for current execution context
TELEMETRY_LOG_FILE=""
EXECUTION_LEDGER_FILE=""
TELEMETRY_TEMP_FILE=""

# Initialize daily telemetry log file
# Creates log file at logs/prompt_execution_YYYY-MM-DD.log
init_telemetry_log() {
    local date="${1:-$(date +%Y-%m-%d)}"
    TELEMETRY_LOG_FILE="${LOGS_DIR}/prompt_execution_${date}.log"
    
    # Create log file with header if it doesn't exist
    if [ ! -f "$TELEMETRY_LOG_FILE" ]; then
        cat > "$TELEMETRY_LOG_FILE" << 'LOG_HEADER'
# NeuroHelix Prompt Execution Telemetry Log
# Format: [ISO8601_TIMESTAMP] EVENT_TYPE | Prompt_Name | Category | Stage | [Status] | [Duration] | [Error]
# 
# EVENT_TYPE: START, END
# Status: success, failure
# Duration: execution time in seconds (only for END events)
# Error: error message (only for END events with failure status)
#
---

LOG_HEADER
        echo "[$(format_iso8601)] LOG_INITIALIZED | Telemetry logging started" >> "$TELEMETRY_LOG_FILE" 2>/dev/null || true
    fi
}

# Initialize execution ledger JSON file
# Creates ledger at data/runtime/execution_ledger_YYYY-MM-DD.json
init_execution_ledger() {
    local date="${1:-$(date +%Y-%m-%d)}"
    EXECUTION_LEDGER_FILE="${RUNTIME_DIR}/execution_ledger_${date}.json"
    TELEMETRY_TEMP_FILE="${RUNTIME_DIR}/.telemetry_temp_${date}.txt"
    
    # Create runtime directory if needed
    mkdir -p "${RUNTIME_DIR}" 2>/dev/null || true
    
    # Initialize JSON structure if file doesn't exist
    if [ ! -f "$EXECUTION_LEDGER_FILE" ]; then
        cat > "$EXECUTION_LEDGER_FILE" << LEDGER_INIT
{
  "date": "${date}",
  "initialized_at": "$(format_iso8601)",
  "executions": [
  ],
  "summary": {
    "total": 0,
    "successful": 0,
    "failed": 0,
    "total_duration_seconds": 0
  }
}
LEDGER_INIT
    fi
    
    # Initialize temp file for tracking start times
    : > "$TELEMETRY_TEMP_FILE"
}

# Format current timestamp in ISO8601 format (compatible with macOS BSD date)
format_iso8601() {
    # Use BSD date command format for macOS
    date -u +"%Y-%m-%dT%H:%M:%S%z" 2>/dev/null || date -u +"%Y-%m-%dT%H:%M:%SZ"
}

# Calculate duration in seconds between two ISO8601 timestamps
calculate_duration() {
    local start_time="$1"
    local end_time="$2"
    
    # Convert ISO8601 to epoch seconds (macOS compatible)
    local start_epoch=$(date -j -f "%Y-%m-%dT%H:%M:%S%z" "$start_time" +%s 2>/dev/null || echo 0)
    local end_epoch=$(date -j -f "%Y-%m-%dT%H:%M:%S%z" "$end_time" +%s 2>/dev/null || echo 0)
    
    if [ "$start_epoch" -eq 0 ] || [ "$end_epoch" -eq 0 ]; then
        # Fallback: try simpler parsing
        start_epoch=$(date -jf "%Y-%m-%dT%H:%M:%S" "${start_time:0:19}" +%s 2>/dev/null || echo 0)
        end_epoch=$(date -jf "%Y-%m-%dT%H:%M:%S" "${end_time:0:19}" +%s 2>/dev/null || echo 0)
    fi
    
    local duration=$((end_epoch - start_epoch))
    echo "$duration"
}

# Log prompt execution start
# Usage: log_prompt_start <prompt_name> <category> <stage>
log_prompt_start() {
    local prompt_name="$1"
    local category="$2"
    local stage="${3:-Research}"
    local timestamp=$(format_iso8601)
    
    # Safe prompt ID (lowercase, underscores)
    local prompt_id=$(echo "$prompt_name" | tr ' ' '_' | tr '[:upper:]' '[:lower:]')
    
    # Log to telemetry file
    echo "[$timestamp] START | $prompt_name | $category | $stage" >> "$TELEMETRY_LOG_FILE" 2>/dev/null || true
    
    # Store start time in temp file for duration calculation
    echo "${prompt_id}|${timestamp}" >> "$TELEMETRY_TEMP_FILE" 2>/dev/null || true
}

# Log prompt execution end
# Usage: log_prompt_end <prompt_name> <category> <stage> <exec_status> [error_message]
log_prompt_end() {
    local prompt_name="$1"
    local category="$2"
    local stage="${3:-Research}"
    local exec_status="$4"
    local error_message="${5:-}"
    local end_timestamp=$(format_iso8601)
    
    # Safe prompt ID
    local prompt_id=$(echo "$prompt_name" | tr ' ' '_' | tr '[:upper:]' '[:lower:]')
    
    # Find start time from temp file
    local start_timestamp=""
    if [ -f "$TELEMETRY_TEMP_FILE" ]; then
        start_timestamp=$(grep "^${prompt_id}|" "$TELEMETRY_TEMP_FILE" 2>/dev/null | tail -1 | cut -d'|' -f2)
    fi
    
    # Calculate duration
    local duration=0
    if [ -n "$start_timestamp" ]; then
        duration=$(calculate_duration "$start_timestamp" "$end_timestamp")
    fi
    
    # Build log entry
    local log_entry="[$end_timestamp] END | $prompt_name | $category | $exec_status | ${duration}s"
    if [ "$exec_status" = "failure" ] && [ -n "$error_message" ]; then
        # Sanitize error message (single line, max 200 chars)
        local sanitized_error=$(echo "$error_message" | tr '\n' ' ' | head -c 200)
        log_entry="${log_entry} | Error: ${sanitized_error}"
    fi
    
    echo "$log_entry" >> "$TELEMETRY_LOG_FILE" 2>/dev/null || true
}

# Add entry to execution ledger JSON
# Usage: add_to_ledger <prompt_name> <category> <stage> <start_time> <end_time> <exec_status> <output_file> [error]
add_to_ledger() {
    local prompt_name="$1"
    local category="$2"
    local stage="${3:-Research}"
    local start_time="$4"
    local end_time="$5"
    local exec_status="$6"
    local output_file="${7:-}"
    local error="${8:-}"
    
    # Safe prompt ID
    local prompt_id=$(echo "$prompt_name" | tr ' ' '_' | tr '[:upper:]' '[:lower:]')
    
    # Calculate duration
    local duration=$(calculate_duration "$start_time" "$end_time")
    
    if [ ! -f "$EXECUTION_LEDGER_FILE" ]; then
        return 1
    fi
    
    # Use Python for reliable JSON manipulation
    python3 -c "
import json
import sys

try:
    # Read existing ledger
    with open('$EXECUTION_LEDGER_FILE', 'r') as f:
        ledger = json.load(f)
    
    # Create new entry
    error_value = None
    if '$exec_status' == 'failure' and '$error':
        error_value = '''$error'''.strip()[:200]
    
    entry = {
        'prompt_id': '$prompt_id',
        'prompt_name': '''$prompt_name''',
        'category': '$category',
        'stage': '$stage',
        'start_time': '$start_time',
        'end_time': '$end_time',
        'duration_seconds': $duration,
        'status': '$exec_status',
        'error': error_value,
        'output_file': '$output_file'
    }
    
    # Append to executions
    ledger['executions'].append(entry)
    
    # Write back with proper formatting
    with open('$EXECUTION_LEDGER_FILE', 'w') as f:
        json.dump(ledger, f, indent=2)
        f.write('\\n')
        
except Exception as e:
    sys.stderr.write(f'Error adding to ledger: {e}\\n')
    sys.exit(1)
" 2>/dev/null || true
}

# Finalize ledger with summary statistics
# Calculates totals and updates summary section
finalize_ledger_summary() {
    if [ ! -f "$EXECUTION_LEDGER_FILE" ]; then
        return 0
    fi
    
    # Count executions using grep and wc
    local total=$(grep -c '"prompt_id"' "$EXECUTION_LEDGER_FILE" 2>/dev/null || echo 0)
    local successful=$(grep -c '"status": "success"' "$EXECUTION_LEDGER_FILE" 2>/dev/null || echo 0)
    local failed=$(grep -c '"status": "failure"' "$EXECUTION_LEDGER_FILE" 2>/dev/null || echo 0)
    
    # Calculate total duration (sum all duration_seconds values)
    local total_duration=$(grep '"duration_seconds"' "$EXECUTION_LEDGER_FILE" 2>/dev/null | \
                          sed 's/.*"duration_seconds": \([0-9]*\).*/\1/' | \
                          awk '{s+=$1} END {print s+0}')
    
    # Update summary section using sed
    local temp_ledger="${EXECUTION_LEDGER_FILE}.tmp"
    sed -e "s/\"total\": [0-9]*/\"total\": $total/" \
        -e "s/\"successful\": [0-9]*/\"successful\": $successful/" \
        -e "s/\"failed\": [0-9]*/\"failed\": $failed/" \
        -e "s/\"total_duration_seconds\": [0-9]*/\"total_duration_seconds\": $total_duration/" \
        "$EXECUTION_LEDGER_FILE" > "$temp_ledger" 2>/dev/null || true
    
    mv "$temp_ledger" "$EXECUTION_LEDGER_FILE" 2>/dev/null || true
    
    # Log summary
    echo "[$(format_iso8601)] SUMMARY | Total: $total | Successful: $successful | Failed: $failed | Duration: ${total_duration}s" >> "$TELEMETRY_LOG_FILE" 2>/dev/null || true
}

# Format duration in human-readable format
# Usage: format_duration <seconds>
# Returns: "5s", "1m 23s", "2h 15m"
format_duration() {
    local total_seconds="$1"
    
    if [ "$total_seconds" -lt 60 ]; then
        echo "${total_seconds}s"
    elif [ "$total_seconds" -lt 3600 ]; then
        local minutes=$((total_seconds / 60))
        local seconds=$((total_seconds % 60))
        echo "${minutes}m ${seconds}s"
    else
        local hours=$((total_seconds / 3600))
        local minutes=$(((total_seconds % 3600) / 60))
        echo "${hours}h ${minutes}m"
    fi
}
