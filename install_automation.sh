#!/bin/bash
# NeuroHelix Automation Installer
# Installs launchd job for daily automated research cycles

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLIST_TEMPLATE="${PROJECT_ROOT}/launchd/com.neurohelix.daily.plist"
PLIST_DEST="${HOME}/Library/LaunchAgents/com.neurohelix.daily.plist"
LAUNCHAGENTS_DIR="${HOME}/Library/LaunchAgents"

echo "🤖 NeuroHelix Automation Installer"
echo "=================================="
echo ""

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌ Error: This installer is for macOS only"
    echo "   For Linux, use cron: crontab -e"
    echo "   Add: 0 7 * * * cd ${PROJECT_ROOT} && ./scripts/orchestrator.sh"
    exit 1
fi

# Ensure LaunchAgents directory exists
mkdir -p "$LAUNCHAGENTS_DIR"

# Check if already installed
if [ -f "$PLIST_DEST" ]; then
    echo "⚠️  Found existing automation setup"
    echo ""
    read -p "Reinstall? This will unload the current job. [y/N] " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Cancelled."
        exit 0
    fi
    
    # Unload existing job
    echo "🔄 Unloading existing job..."
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
    rm -f "$PLIST_DEST"
fi

# Create personalized plist from template
echo "📝 Creating launchd configuration..."
sed "s|PROJECT_ROOT_PLACEHOLDER|${PROJECT_ROOT}|g" "$PLIST_TEMPLATE" | \
sed "s|HOME_PLACEHOLDER|${HOME}|g" > "$PLIST_DEST"

echo "✅ Created: $PLIST_DEST"
echo ""

# Show schedule details
echo "📅 Schedule Configuration:"
echo "   • Runs daily at 7:00 AM"
echo "   • Working directory: ${PROJECT_ROOT}"
echo "   • Logs: ${PROJECT_ROOT}/logs/launchd_*.log"
echo ""

# Ask for confirmation
read -p "Install and activate this schedule? [Y/n] " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Nn]$ ]]; then
    echo "Cancelled. Plist created but not loaded."
    echo "To manually load later: launchctl load $PLIST_DEST"
    exit 0
fi

# Load the job
echo "🚀 Loading launchd job..."
launchctl load "$PLIST_DEST"

if [ $? -eq 0 ]; then
    echo "✅ Successfully installed!"
    echo ""
    echo "📊 Management Commands:"
    echo "   • Check status:    launchctl list | grep neurohelix"
    echo "   • View logs:       tail -f ${PROJECT_ROOT}/logs/launchd_stdout.log"
    echo "   • Manual run:      launchctl start com.neurohelix.daily"
    echo "   • Uninstall:       ./uninstall_automation.sh"
    echo ""
    echo "🧪 Test the automation:"
    echo "   launchctl start com.neurohelix.daily"
    echo "   (This will run immediately, not wait until 7 AM)"
    echo ""
    echo "🎯 Next scheduled run: Tomorrow at 7:00 AM"
else
    echo "❌ Failed to load launchd job"
    echo "Check for errors with: launchctl load -w $PLIST_DEST"
    exit 1
fi
