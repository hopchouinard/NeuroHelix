#!/bin/bash
# Environment configuration

# Project paths
export PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export CONFIG_DIR="${PROJECT_ROOT}/config"
export SCRIPTS_DIR="${PROJECT_ROOT}/scripts"
export DATA_DIR="${PROJECT_ROOT}/data"
export LOGS_DIR="${PROJECT_ROOT}/logs"
export DASHBOARD_DIR="${PROJECT_ROOT}/dashboards"
export RUNTIME_DIR="${DATA_DIR}/runtime"

# CLI tools
export GEMINI_CLI="gemini"
export COPILOT_CLI="gh copilot"

# Gemini CLI settings
export GEMINI_MODEL="gemini-2.5-flash"  # Default model
export GEMINI_OUTPUT_FORMAT="text"  # Options: text, json, stream-json
export GEMINI_APPROVAL_MODE="yolo"  # Options: default, auto_edit, yolo
export GEMINI_YOLO_MODE="true"  # Auto-approve all actions
export GEMINI_DEBUG="false"  # Debug mode

# Feature flags
export ENABLE_NOTIFICATIONS="false"
export ENABLE_META_AUTOMATION="false"
export PARALLEL_EXECUTION="true"
export MAX_PARALLEL_JOBS="4"

# Notification settings (if enabled)
export NOTIFICATION_EMAIL=""
export DISCORD_WEBHOOK_URL=""

# Failure notification settings
export FAILURE_NOTIFICATION_EMAIL="chouinpa@gmail.com"
export ENABLE_FAILURE_NOTIFICATIONS="true"

# Static Site Publishing
export PUBLISHING_DIR="${DATA_DIR}/publishing"
export ENABLE_STATIC_SITE_PUBLISHING="true"
export CLOUDFLARE_PROJECT_NAME="neurohelix-site"
export CLOUDFLARE_PRODUCTION_DOMAIN="neurohelix.patchoutech.com"
