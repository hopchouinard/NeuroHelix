#!/bin/bash
# Send notifications (email, Discord, etc.)

set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../config/env.sh"

DATE=$(date +%Y-%m-%d)
DASHBOARD_FILE="${DASHBOARD_DIR}/dashboard_${DATE}.html"

echo "Sending notification for ${DATE}..."

# Email notification (requires mail command)
if [ -n "${NOTIFICATION_EMAIL}" ]; then
    echo "Your NeuroHelix daily report is ready: file://${DASHBOARD_FILE}" | \
        mail -s "NeuroHelix Daily Report - ${DATE}" "${NOTIFICATION_EMAIL}" || \
        echo "Failed to send email notification"
fi

# Discord webhook notification
if [ -n "${DISCORD_WEBHOOK_URL}" ]; then
    curl -X POST "${DISCORD_WEBHOOK_URL}" \
        -H "Content-Type: application/json" \
        -d "{\"content\": \"🧠 NeuroHelix Daily Report Ready - ${DATE}\n\nView dashboard: file://${DASHBOARD_FILE}\"}" || \
        echo "Failed to send Discord notification"
fi

echo "✅ Notifications sent"
