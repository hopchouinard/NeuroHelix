#!/bin/bash
# NeuroHelix Automation Uninstaller
# Removes launchd job for daily automated research cycles

set -euo pipefail

PLIST_DEST="${HOME}/Library/LaunchAgents/com.neurohelix.daily.plist"

echo "🗑️  NeuroHelix Automation Uninstaller"
echo "====================================="
echo ""

# Check if installed
if [ ! -f "$PLIST_DEST" ]; then
    echo "ℹ️  No automation found. Nothing to uninstall."
    echo "   Expected location: $PLIST_DEST"
    exit 0
fi

echo "Found automation at: $PLIST_DEST"
echo ""

# Ask for confirmation
read -p "Uninstall daily automation? [y/N] " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

# Unload the job
echo "🔄 Unloading launchd job..."
launchctl unload "$PLIST_DEST" 2>/dev/null || true

# Remove the plist
rm -f "$PLIST_DEST"

echo "✅ Successfully uninstalled!"
echo ""
echo "ℹ️  Note: Existing data and logs are preserved"
echo "   To reinstall: ./install_automation.sh"
