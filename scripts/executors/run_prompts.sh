#!/bin/bash
# Execute all research prompts from manifest

# Note: set -e removed to allow non-blocking failures
set -uo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../config/env.sh"
source "${SCRIPTS_DIR}/lib/telemetry.sh"

DATE=$(date +%Y-%m-%d)
OUTPUT_DIR="${DATA_DIR}/outputs/daily/${DATE}"
mkdir -p "$OUTPUT_DIR"

SEARCHES_FILE="${CONFIG_DIR}/searches.tsv"
COMPLETION_MARKER="${OUTPUT_DIR}/.execution_complete"

if [ ! -f "$SEARCHES_FILE" ]; then
    echo "Error: searches.tsv not found"
    exit 1
fi

# Initialize telemetry system
init_telemetry_log "$DATE"
init_execution_ledger "$DATE"

echo "📊 Telemetry logging enabled"
echo "   Log file: ${TELEMETRY_LOG_FILE}"
echo "   Ledger file: ${EXECUTION_LEDGER_FILE}"
echo ""

# Idempotency check: Skip if already completed today
if [ -f "$COMPLETION_MARKER" ]; then
    echo "✅ Research prompts already executed for ${DATE}"
    echo "   Completion time: $(cat "$COMPLETION_MARKER")"
    echo "   To re-run, delete: $COMPLETION_MARKER"
    exit 0
fi

execute_prompt() {
    local domain="$1"
    local category="$2"
    local prompt="$3"
    local priority="$4"
    
    local safe_domain=$(echo "$domain" | tr ' ' '_' | tr '[:upper:]' '[:lower:]')
    local output_file="${OUTPUT_DIR}/${safe_domain}.md"
    
    # Log execution start
    log_prompt_start "$domain" "$category" "Research"
    local start_time=$(format_iso8601)
    
    echo "Executing: $domain"
    
    # Build context-aware prompt with file paths
    local enhanced_prompt="$prompt"
    
    # Add context for specific domains that need historical data
    case "$domain" in
        "Novelty Filter")
            # Provide yesterday's concept synthesizer output if it exists
            YESTERDAY=$(date -v-1d +%Y-%m-%d 2>/dev/null || date -d "yesterday" +%Y-%m-%d 2>/dev/null)
            YESTERDAY_CONCEPTS="${DATA_DIR}/outputs/daily/${YESTERDAY}/concept_synthesizer.md"
            if [ -f "$YESTERDAY_CONCEPTS" ]; then
                enhanced_prompt="${prompt}\n\nYESTERDAY'S IDEAS (from ${YESTERDAY}):\n$(cat "$YESTERDAY_CONCEPTS")"
            else
                enhanced_prompt="${prompt}\n\nNote: Yesterday's ideas file not found at ${YESTERDAY_CONCEPTS}"
            fi
            ;;
        "Continuity Builder")
            # Provide last 7 days of reports
            enhanced_prompt="${prompt}\n\nAVAILABLE REPORTS:"
            for i in {1..7}; do
                PAST_DATE=$(date -v-${i}d +%Y-%m-%d 2>/dev/null || date -d "${i} days ago" +%Y-%m-%d 2>/dev/null)
                PAST_REPORT="${DATA_DIR}/reports/daily_report_${PAST_DATE}.md"
                if [ -f "$PAST_REPORT" ]; then
                    enhanced_prompt+="\n\n=== Report from ${PAST_DATE} ===\n$(head -200 "$PAST_REPORT")"
                fi
            done
            ;;
        "Meta-Project Explorer")
            # Provide system structure info
            enhanced_prompt="${prompt}\n\nSYSTEM STRUCTURE:\n"
            enhanced_prompt+="- Output directory: ${DATA_DIR}/outputs/daily/\n"
            enhanced_prompt+="- Reports directory: ${DATA_DIR}/reports/\n"
            enhanced_prompt+="- Recent reports available: $(ls -1 ${DATA_DIR}/reports/*.md 2>/dev/null | tail -5 | xargs -n1 basename)\n"
            enhanced_prompt+="\nCURRENT SEARCH DOMAINS:\n$(tail -n +2 ${CONFIG_DIR}/searches.tsv | cut -f1,2 | head -10)"
            ;;
    esac
    
    # Create markdown with YAML front-matter
    cat > "$output_file" << YAML
---
domain: ${domain}
date: ${DATE}
priority: ${priority}
---

# ${domain} - ${DATE}

YAML
    
    # Execute prompt using Gemini CLI with proper flags
    if [ "${GEMINI_DEBUG}" = "true" ]; then
        DEBUG_FLAG="--debug"
    else
        DEBUG_FLAG=""
    fi
    
    # Use positional prompt with non-interactive mode
    # Close stdin to prevent hanging
    ${GEMINI_CLI} ${DEBUG_FLAG} \
        --model "${GEMINI_MODEL}" \
        --output-format "${GEMINI_OUTPUT_FORMAT}" \
        "$enhanced_prompt" < /dev/null >> "$output_file" 2>&1 &
    
    local gemini_pid=$!
    local timeout_seconds=120
    local elapsed=0
    
    # Wait for process with timeout
    while kill -0 $gemini_pid 2>/dev/null; do
        if [ $elapsed -ge $timeout_seconds ]; then
            local end_time=$(format_iso8601)
            local timeout_error="Request timed out after ${timeout_seconds} seconds"
            
            echo "Error: Timeout after ${timeout_seconds}s for $domain" >&2
            kill -9 $gemini_pid 2>/dev/null
            echo "\n\n**Error: ${timeout_error}**" >> "$output_file"
            
            # Log timeout failure
            log_prompt_end "$domain" "$category" "Research" "failure" "$timeout_error"
            add_to_ledger "$domain" "$category" "Research" "$start_time" "$end_time" "failure" "$output_file" "$timeout_error"
            
            echo "❌ Failed (timeout): $domain"
            return 1
        fi
        sleep 1
        ((elapsed++))
    done
    
    # Check exit status
    wait $gemini_pid
    local exit_code=$?
    local end_time=$(format_iso8601)
    local error_message=""
    
    if [ $exit_code -ne 0 ]; then
        error_message="Failed to execute research prompt (exit code: $exit_code)"
        echo "Error executing prompt for $domain (exit code: $exit_code)" >&2
        echo "\n\n**Error: ${error_message}**" >> "$output_file"
        
        # Log failure and add to ledger
        log_prompt_end "$domain" "$category" "Research" "failure" "$error_message"
        add_to_ledger "$domain" "$category" "Research" "$start_time" "$end_time" "failure" "$output_file" "$error_message"
        
        echo "❌ Failed: $domain"
        return $exit_code
    fi
    
    # Log success and add to ledger
    log_prompt_end "$domain" "$category" "Research" "success"
    add_to_ledger "$domain" "$category" "Research" "$start_time" "$end_time" "success" "$output_file"
    
    echo "✅ Completed: $domain"
}

export -f execute_prompt
export -f log_prompt_start log_prompt_end add_to_ledger format_iso8601
export GEMINI_CLI GEMINI_MODEL GEMINI_OUTPUT_FORMAT GEMINI_DEBUG DATE OUTPUT_DIR
export TELEMETRY_LOG_FILE EXECUTION_LEDGER_FILE TELEMETRY_TEMP_FILE DATA_DIR CONFIG_DIR

# Parse TSV and execute prompts (5 columns: domain, category, prompt, priority, enabled)
# Note: Failures are non-blocking - execution continues with remaining prompts
tail -n +2 "$SEARCHES_FILE" | while IFS=$'\t' read -r domain category prompt priority enabled; do
    if [ "$enabled" = "true" ]; then
        if [ "${PARALLEL_EXECUTION}" = "true" ]; then
            # Execute in background with failure isolation
            execute_prompt "$domain" "$category" "$prompt" "$priority" || true &
            
            # Limit parallel jobs
            while [ $(jobs -r | wc -l) -ge "${MAX_PARALLEL_JOBS}" ]; do
                sleep 1
            done
        else
            # Execute sequentially with failure isolation
            execute_prompt "$domain" "$category" "$prompt" "$priority" || true
        fi
    fi
done

# Wait for all background jobs to complete
wait

# Finalize telemetry ledger with summary statistics
finalize_ledger_summary

echo ""
echo "📊 Telemetry Summary:"
if [ -f "$EXECUTION_LEDGER_FILE" ]; then
    # Extract summary from ledger (use tail to get last occurrence)
    SUMMARY_TOTAL=$(grep '"total":' "$EXECUTION_LEDGER_FILE" | tail -1 | sed 's/.*"total": \([0-9]*\).*/\1/')
    SUMMARY_SUCCESSFUL=$(grep '"successful":' "$EXECUTION_LEDGER_FILE" | tail -1 | sed 's/.*"successful": \([0-9]*\).*/\1/')
    SUMMARY_FAILED=$(grep '"failed":' "$EXECUTION_LEDGER_FILE" | tail -1 | sed 's/.*"failed": \([0-9]*\).*/\1/')
    SUMMARY_DURATION=$(grep '"total_duration_seconds":' "$EXECUTION_LEDGER_FILE" | tail -1 | sed 's/.*"total_duration_seconds": \([0-9]*\).*/\1/')
    
    echo "   Total prompts: ${SUMMARY_TOTAL}"
    echo "   Successful: ${SUMMARY_SUCCESSFUL}"
    echo "   Failed: ${SUMMARY_FAILED}"
    echo "   Total duration: $(format_duration ${SUMMARY_DURATION})"
    echo "   Log: ${TELEMETRY_LOG_FILE}"
    echo "   Ledger: ${EXECUTION_LEDGER_FILE}"
fi

# Mark execution as complete (even with partial failures)
date +"%Y-%m-%d %H:%M:%S" > "$COMPLETION_MARKER"

if [ "${SUMMARY_FAILED:-0}" -gt 0 ]; then
    echo ""
    echo "⚠️  Execution completed with ${SUMMARY_FAILED} failure(s)"
    echo "   Review telemetry log for details: ${TELEMETRY_LOG_FILE}"
    echo "   Email notification will be sent if configured"
else
    echo ""
    echo "✅ All prompts executed successfully for ${DATE}"
fi

echo "🔒 Execution marked complete (idempotent)"
