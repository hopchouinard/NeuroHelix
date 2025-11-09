#!/bin/bash
# Cloudflare Pages API helpers for deployment management

# Get the most recent successful deployment ID
# Usage: get_latest_deployment_id <project_name>
# Returns: deployment_id or empty string
get_latest_deployment_id() {
    local project_name="$1"

    if [ -z "${CLOUDFLARE_API_TOKEN:-}" ]; then
        echo ""
        return 1
    fi

    # Use wrangler to get deployment list (easier than REST API)
    local deploy_output
    deploy_output=$(npx wrangler pages deployment list \
        --project-name="${project_name}" \
        2>/dev/null | head -20 || echo "")

    # Extract the most recent deployment ID from wrangler output
    # Wrangler output format varies, so we'll try to parse it
    # Format is typically: ID | Created | Source | Status
    local deploy_id
    deploy_id=$(echo "$deploy_output" | grep -E "ACTIVE|Success" | head -1 | awk '{print $1}' || echo "")

    echo "${deploy_id}"
}

# Retract (delete) a Cloudflare Pages deployment
# Usage: retract_deployment <project_name> <log_file> <dry_run>
# Prints: deployment_id to stdout for capture
# Returns: 0 on success, 1 on failure
retract_deployment() {
    local project_name="$1"
    local log_file="$2"
    local dry_run="${3:-false}"

    log_maintenance "${log_file}" "🌐 Cloudflare Pages deployment retraction..." >&2

    if [ -z "${CLOUDFLARE_API_TOKEN:-}" ]; then
        log_maintenance "${log_file}" "⚠️  Warning: CLOUDFLARE_API_TOKEN not set" >&2
        log_maintenance "${log_file}" "   Skipping Cloudflare deployment retraction" >&2
        echo ""
        return 0
    fi

    # Get latest deployment ID
    log_maintenance "${log_file}" "   Fetching latest deployment ID..." >&2
    local deploy_id
    deploy_id=$(get_latest_deployment_id "${project_name}")

    if [ -z "${deploy_id}" ]; then
        log_maintenance "${log_file}" "⚠️  Warning: Could not find latest deployment ID" >&2
        log_maintenance "${log_file}" "   Skipping Cloudflare deployment retraction" >&2
        echo ""
        return 0
    fi

    log_maintenance "${log_file}" "   Latest deployment ID: ${deploy_id}" >&2

    if [ "${dry_run}" = "true" ]; then
        log_maintenance "${log_file}" "   [DRY RUN] Would delete deployment: ${deploy_id}" >&2
        echo "${deploy_id}"
        return 0
    fi

    # Note: Cloudflare Pages doesn't actually support deleting deployments via API
    # Deployments are immutable and auto-expire after 30 days
    # We can, however, create a new blank deployment or rollback
    # For now, we'll just log this limitation
    log_maintenance "${log_file}" "⚠️  Note: Cloudflare Pages deployments cannot be deleted via API" >&2
    log_maintenance "${log_file}" "   Deployments auto-expire after 30 days" >&2
    log_maintenance "${log_file}" "   Latest deployment: ${deploy_id}" >&2
    log_maintenance "${log_file}" "   To rollback, deploy a previous version manually" >&2

    # Return the deployment ID for audit logging
    echo "${deploy_id}"
    return 0
}

# Create a rollback deployment to previous version
# This is an alternative to deleting deployments
# Usage: rollback_to_empty <project_name> <log_file> <dry_run>
rollback_to_empty() {
    local project_name="$1"
    local log_file="$2"
    local dry_run="${3:-false}"

    log_maintenance "${log_file}" "🌐 Creating empty rollback deployment..."

    if [ "${dry_run}" = "true" ]; then
        log_maintenance "${log_file}" "   [DRY RUN] Would deploy empty site to Cloudflare Pages"
        return 0
    fi

    # Create a temporary empty directory for deployment
    local temp_dir=$(mktemp -d)
    echo "<html><body><h1>Site Temporarily Unavailable</h1></body></html>" > "${temp_dir}/index.html"

    log_maintenance "${log_file}" "   Deploying empty site..."

    local deploy_output
    deploy_output=$(npx wrangler pages deploy "${temp_dir}" \
        --project-name="${project_name}" \
        --branch=rollback \
        2>&1 || echo "FAILED")

    rm -rf "${temp_dir}"

    if echo "$deploy_output" | grep -q "FAILED"; then
        log_maintenance "${log_file}" "❌ Rollback deployment failed"
        return 1
    fi

    log_maintenance "${log_file}" "✅ Rolled back to empty site"
    return 0
}

# Export functions
export -f get_latest_deployment_id
export -f retract_deployment
export -f rollback_to_empty
