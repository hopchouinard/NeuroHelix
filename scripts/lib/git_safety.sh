#!/bin/bash
# Git safety checks for maintenance operations
# Ensures git working tree is clean before destructive operations

# Check if git working tree is clean
# Returns: 0 if clean, 1 if dirty
is_git_clean() {
    [ -z "$(git status --porcelain 2>/dev/null)" ]
}

# Enforce git safety check
# Usage: check_git_safety <allow_dirty_flag> <log_file>
# Exits with code 1 if git is dirty and allow_dirty is false
check_git_safety() {
    local allow_dirty="$1"
    local log_file="$2"

    if ! is_git_clean; then
        if [ "${allow_dirty}" = "false" ]; then
            log_maintenance "${log_file}" "❌ Error: Git working tree is dirty"
            log_maintenance "${log_file}" ""
            log_maintenance "${log_file}" "Uncommitted changes detected:"
            git status --short 2>&1 | while IFS= read -r line; do
                log_maintenance "${log_file}" "   $line"
            done
            log_maintenance "${log_file}" ""
            log_maintenance "${log_file}" "Please commit or stash your changes before running this command."
            log_maintenance "${log_file}" "Or use --allow-dirty to bypass this check."
            return 1
        else
            log_maintenance "${log_file}" "⚠️  Warning: Git working tree is dirty (--allow-dirty enabled)"
            git status --short 2>&1 | while IFS= read -r line; do
                log_maintenance "${log_file}" "   $line"
            done
        fi
    else
        log_maintenance "${log_file}" "✅ Git working tree is clean"
    fi
    return 0
}

# Export functions
export -f is_git_clean
export -f check_git_safety
