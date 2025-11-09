#!/bin/bash
# Cleanup operations for NeuroHelix workspace
# Handles deletion of generated artifacts

# Define paths to clean up
CLEANUP_PATHS=(
    "data/outputs/daily"
    "data/reports"
    "data/publishing"
    "data/runtime"
    "dashboards"
    "logs/prompt_execution_*.log"
    "logs/orchestrator_*.log"
    "logs/publishing"
    "site/public/search-index.json"
    "site/src/content/dashboards"
    "site/src/data/tags.json"
    "site/src/data/tag-frequencies.json"
    "site/src/data/categories.json"
    "site/src/data/stats.json"
)

# Paths to preserve (never delete)
PRESERVE_PATHS=(
    "config"
    "data/config"
    "ai_docs"
    "site/src/layouts"
    "site/src/pages"
    "site/src/components"
    ".git"
    "launchd"
)

# Print cleanup plan
# Usage: print_cleanup_plan <log_file>
print_cleanup_plan() {
    local log_file="$1"

    log_maintenance "${log_file}" "📋 Cleanup Plan:"
    log_maintenance "${log_file}" ""
    log_maintenance "${log_file}" "The following paths will be removed:"

    local path_count=0
    local total_size=0

    for path in "${CLEANUP_PATHS[@]}"; do
        local full_path="${PROJECT_ROOT}/${path}"

        # Check if path exists (handle globs)
        if [[ "$path" == *"*"* ]]; then
            # Glob pattern
            local matches=$(find "${PROJECT_ROOT}" -path "${full_path}" 2>/dev/null | wc -l | tr -d ' ')
            if [ "${matches}" -gt 0 ]; then
                log_maintenance "${log_file}" "   ✓ ${path} (${matches} files)"
                path_count=$((path_count + matches))
            fi
        else
            # Regular path
            if [ -e "${full_path}" ]; then
                local size=$(du -sh "${full_path}" 2>/dev/null | cut -f1 || echo "0")
                log_maintenance "${log_file}" "   ✓ ${path} (${size})"
                path_count=$((path_count + 1))
            fi
        fi
    done

    log_maintenance "${log_file}" ""
    log_maintenance "${log_file}" "Total paths/files to remove: ${path_count}"
    log_maintenance "${log_file}" ""
    log_maintenance "${log_file}" "Preserved paths (will NOT be touched):"

    for path in "${PRESERVE_PATHS[@]}"; do
        log_maintenance "${log_file}" "   🔒 ${path}"
    done

    log_maintenance "${log_file}" ""
}

# Execute cleanup
# Usage: execute_cleanup <log_file> <dry_run>
# Returns: 0 on success, 1 on failure
execute_cleanup() {
    local log_file="$1"
    local dry_run="${2:-false}"

    local success_count=0
    local fail_count=0
    local skip_count=0

    log_maintenance "${log_file}" "🗑️  Executing cleanup..."
    log_maintenance "${log_file}" ""

    for path in "${CLEANUP_PATHS[@]}"; do
        local full_path="${PROJECT_ROOT}/${path}"

        # Handle glob patterns
        if [[ "$path" == *"*"* ]]; then
            # Glob pattern - find and remove matching files
            local matches=($(find "$(dirname "${full_path}")" -name "$(basename "${path}")" 2>/dev/null || true))

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
            # Regular path
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
    done

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

# Get cleanup paths as JSON array
# Usage: get_cleanup_paths_json
get_cleanup_paths_json() {
    local json="["
    local first=true

    for path in "${CLEANUP_PATHS[@]}"; do
        if [ "$first" = true ]; then
            first=false
        else
            json="${json},"
        fi
        json="${json}\"${path}\""
    done

    json="${json}]"
    echo "${json}"
}

# Export functions
export -f print_cleanup_plan
export -f execute_cleanup
export -f get_cleanup_paths_json
