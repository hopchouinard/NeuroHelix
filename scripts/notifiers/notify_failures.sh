#!/bin/bash
# Send email notifications for prompt failures
# Non-fatal: continues even if email delivery fails

set -uo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../config/env.sh"

DATE=$(date +%Y-%m-%d)
LEDGER_FILE="${1:-${RUNTIME_DIR}/execution_ledger_${DATE}.json}"

# Check if failure notifications are enabled
if [ "${ENABLE_FAILURE_NOTIFICATIONS:-false}" != "true" ]; then
    echo "⏭️  Failure notifications disabled (ENABLE_FAILURE_NOTIFICATIONS=false)"
    exit 0
fi

# Check if ledger file exists
if [ ! -f "$LEDGER_FILE" ]; then
    echo "⚠️  No execution ledger found at: $LEDGER_FILE"
    echo "   Skipping failure notification"
    exit 0
fi

# Extract failure count from ledger
FAILURE_COUNT=$(grep -c '"status": "failure"' "$LEDGER_FILE" 2>/dev/null || echo 0)

if [ "$FAILURE_COUNT" -eq 0 ]; then
    echo "✅ No failures detected - skipping notification"
    exit 0
fi

echo "📧 Sending failure notification email..."
echo "   Failed prompts: $FAILURE_COUNT"
echo "   Recipient: ${FAILURE_NOTIFICATION_EMAIL}"

# Build email content
EMAIL_SUBJECT="NeuroHelix Pipeline Failures - ${DATE}"
EMAIL_BODY_FILE="/tmp/neurohelix_failure_email_${DATE}.txt"

# Create email body
cat > "$EMAIL_BODY_FILE" << EMAIL_HEADER
NeuroHelix Prompt Execution Failures
=====================================

Date: ${DATE}
Failed Prompts: ${FAILURE_COUNT}

The following prompts failed during today's execution:

EMAIL_HEADER

# Extract failed prompts from ledger and format as table
echo "Prompt Name                      | Category    | Error" >> "$EMAIL_BODY_FILE"
echo "--------------------------------|-------------|-------------------------------------------------------" >> "$EMAIL_BODY_FILE"

# Parse JSON ledger for failures (using grep and sed for portability)
grep -A 10 '"status": "failure"' "$LEDGER_FILE" | while read -r line; do
    if echo "$line" | grep -q '"prompt_name":'; then
        PROMPT_NAME=$(echo "$line" | sed 's/.*"prompt_name": "\([^"]*\)".*/\1/')
        printf "%-32s" "$PROMPT_NAME" >> "$EMAIL_BODY_FILE"
    elif echo "$line" | grep -q '"category":'; then
        CATEGORY=$(echo "$line" | sed 's/.*"category": "\([^"]*\)".*/\1/')
        printf "| %-11s " "$CATEGORY" >> "$EMAIL_BODY_FILE"
    elif echo "$line" | grep -q '"error":' && ! echo "$line" | grep -q '"error": null'; then
        ERROR=$(echo "$line" | sed 's/.*"error": "\([^"]*\)".*/\1/' | head -c 50)
        printf "| %-50s\n" "$ERROR" >> "$EMAIL_BODY_FILE"
    fi
done

# Add detailed information section
cat >> "$EMAIL_BODY_FILE" << EMAIL_FOOTER

=====================================

TELEMETRY DETAILS:
- Execution Ledger: ${LEDGER_FILE}
- Telemetry Log: ${LOGS_DIR}/prompt_execution_${DATE}.log
- Daily Report: ${DATA_DIR}/reports/daily_report_${DATE}.md

HOW TO TROUBLESHOOT:
1. Review the telemetry log for detailed error messages:
   cat ${LOGS_DIR}/prompt_execution_${DATE}.log

2. Check the execution ledger for full error payloads:
   cat ${LEDGER_FILE}

3. Review individual prompt outputs in:
   ${DATA_DIR}/outputs/daily/${DATE}/

HOW TO RERUN FAILED PROMPTS:
1. Delete the completion marker to allow re-execution:
   rm ${DATA_DIR}/outputs/daily/${DATE}/.execution_complete

2. Rerun the orchestrator:
   cd /Users/pchouinard/Dev/NeuroHelix && ./scripts/orchestrator.sh

HOW TO DISABLE A FAILING PROMPT:
1. Edit the configuration file:
   nano /Users/pchouinard/Dev/NeuroHelix/config/searches.tsv

2. Change 'enabled' column from 'true' to 'false' for the problematic prompt

3. Save and rerun the pipeline

=====================================

This is an automated notification from NeuroHelix.
To disable failure notifications, set ENABLE_FAILURE_NOTIFICATIONS=false in config/env.sh

EMAIL_FOOTER

# Send email with retry logic
send_email() {
    local subject="$1"
    local body_file="$2"
    local recipient="$3"
    
    # Use mail command (macOS compatible)
    if command -v mail &> /dev/null; then
        mail -s "$subject" "$recipient" < "$body_file" 2>&1
        return $?
    elif command -v mailx &> /dev/null; then
        mailx -s "$subject" "$recipient" < "$body_file" 2>&1
        return $?
    else
        echo "Error: No mail command available (tried 'mail' and 'mailx')" >&2
        return 1
    fi
}

# Attempt to send email with retries
MAX_RETRIES=3
RETRY_DELAY=5
RETRY_COUNT=0
EMAIL_SENT=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if send_email "$EMAIL_SUBJECT" "$EMAIL_BODY_FILE" "$FAILURE_NOTIFICATION_EMAIL"; then
        EMAIL_SENT=true
        echo "✅ Failure notification sent successfully to ${FAILURE_NOTIFICATION_EMAIL}"
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
            echo "⚠️  Email send failed (attempt $RETRY_COUNT/$MAX_RETRIES). Retrying in ${RETRY_DELAY}s..."
            sleep $RETRY_DELAY
        fi
    fi
done

# Clean up temporary email file
rm -f "$EMAIL_BODY_FILE" 2>/dev/null || true

# Log final status (non-fatal)
if [ "$EMAIL_SENT" = true ]; then
    echo "📬 Notification delivery confirmed"
    exit 0
else
    echo "❌ Failed to send notification email after $MAX_RETRIES attempts" >&2
    echo "   Check that 'mail' command is configured correctly" >&2
    echo "   Email body was saved to: $EMAIL_BODY_FILE" >&2
    # Return 0 to prevent blocking the pipeline
    exit 0
fi
