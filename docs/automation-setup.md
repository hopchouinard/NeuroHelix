# Automation Setup Guide

## Overview

NeuroHelix uses **launchd** (macOS) for automated daily research cycles. This guide covers installation, management, and troubleshooting.

---

## Quick Start

### Install Automation

```bash
./install_automation.sh
```

This will:
1. Create launchd plist in `~/Library/LaunchAgents/`
2. Schedule daily execution at 7:00 AM
3. Configure logging
4. Load and activate the job

### Uninstall Automation

```bash
./uninstall_automation.sh
```

This will:
1. Unload the launchd job
2. Remove the plist file
3. Preserve all data and logs

---

## Schedule Configuration

### Default Schedule

- **Time:** 7:00 AM daily
- **Working Directory:** Project root
- **Logs:** `logs/launchd_stdout.log` and `logs/launchd_stderr.log`
- **Process Priority:** Nice +5 (lower priority)

### Custom Schedule

To change the time, edit `launchd/com.neurohelix.daily.plist` before installing:

```xml
<key>StartCalendarInterval</key>
<dict>
    <key>Hour</key>
    <integer>7</integer>  <!-- Change this (0-23) -->
    <key>Minute</key>
    <integer>0</integer>  <!-- Change this (0-59) -->
</dict>
```

**Multiple times per day:**

```xml
<key>StartCalendarInterval</key>
<array>
    <dict>
        <key>Hour</key>
        <integer>7</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <dict>
        <key>Hour</key>
        <integer>19</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
</array>
```

Then reinstall:
```bash
./uninstall_automation.sh
./install_automation.sh
```

---

## Management Commands

### Check Status

```bash
# See if job is loaded
launchctl list | grep neurohelix

# Output: PID    Status  Label
#         -      0       com.neurohelix.daily
```

**Status codes:**
- `-` in PID column = Not currently running (normal between scheduled times)
- `0` in Status = Last run was successful
- Non-zero Status = Last run failed (check logs)

### Manual Trigger

Run immediately without waiting for scheduled time:

```bash
launchctl start com.neurohelix.daily
```

**Note:** This runs in background. Check logs to see progress.

### View Logs

```bash
# Real-time stdout
tail -f logs/launchd_stdout.log

# Real-time stderr
tail -f logs/launchd_stderr.log

# Recent stdout (last 50 lines)
tail -50 logs/launchd_stdout.log

# All orchestrator logs
ls -lht logs/orchestrator_*.log | head -10
```

### Stop Job (Temporarily)

```bash
launchctl stop com.neurohelix.daily
```

**Note:** This only stops the current execution. Job will run again at next scheduled time.

### Disable Job (Keep Installed)

```bash
launchctl unload ~/Library/LaunchAgents/com.neurohelix.daily.plist
```

### Re-enable Job

```bash
launchctl load ~/Library/LaunchAgents/com.neurohelix.daily.plist
```

---

## File Locations

### launchd Configuration

```
~/Library/LaunchAgents/com.neurohelix.daily.plist
```

This is the active configuration loaded by macOS.

### Template

```
PROJECT_ROOT/launchd/com.neurohelix.daily.plist
```

This is the template used by `install_automation.sh`.

### Logs

```
PROJECT_ROOT/logs/launchd_stdout.log  # Standard output
PROJECT_ROOT/logs/launchd_stderr.log  # Error output
PROJECT_ROOT/logs/orchestrator_*.log  # Pipeline execution logs
```

---

## Environment Variables

The launchd job sets these environment variables:

```xml
<key>EnvironmentVariables</key>
<dict>
    <key>PATH</key>
    <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.local/bin</string>
    
    <key>HOME</key>
    <string>/Users/username</string>
</dict>
```

### Adding Custom Variables

Edit the plist template before installing:

```xml
<key>EnvironmentVariables</key>
<dict>
    <!-- Existing variables -->
    <key>PATH</key>
    <string>...</string>
    
    <!-- Add your custom variables -->
    <key>MY_CUSTOM_VAR</key>
    <string>value</string>
</dict>
```

---

## Troubleshooting

### Job Not Running

**Check if loaded:**
```bash
launchctl list | grep neurohelix
```

**If not listed:**
```bash
./install_automation.sh
```

**If listed but not running at scheduled time:**

1. Check system time:
   ```bash
   date
   ```

2. Verify plist schedule:
   ```bash
   grep -A5 StartCalendarInterval ~/Library/LaunchAgents/com.neurohelix.daily.plist
   ```

3. Check macOS sleep settings:
   - System Preferences → Energy Saver
   - Ensure Mac isn't sleeping at scheduled time

### Failed Execution

**Check exit status:**
```bash
launchctl list | grep neurohelix
# Look at second column (Status)
```

**Check logs:**
```bash
# Errors
cat logs/launchd_stderr.log

# Last execution log
ls -lt logs/orchestrator_*.log | head -1 | awk '{print $NF}' | xargs cat
```

**Common issues:**

1. **Gemini CLI not found**
   - Add Gemini CLI to PATH in plist
   - Or use absolute path in `config/env.sh`

2. **Permission denied**
   - Ensure scripts are executable: `chmod +x scripts/**/*.sh`

3. **Working directory error**
   - Verify PROJECT_ROOT in plist is correct
   - Reinstall: `./install_automation.sh`

### Manual Test

Run pipeline manually to verify it works:

```bash
cd /path/to/NeuroHelix
./scripts/orchestrator.sh
```

If manual run works but launchd fails, it's usually an environment issue.

### Debug launchd Execution

Add debug flag to plist temporarily:

```xml
<key>ProgramArguments</key>
<array>
    <string>/bin/bash</string>
    <string>-x</string>  <!-- Enable debug mode -->
    <string>PROJECT_ROOT/scripts/orchestrator.sh</string>
</array>
```

Reinstall and check logs for detailed output.

---

## Advanced Configuration

### Run at System Start

Add this to plist:

```xml
<key>RunAtLoad</key>
<true/>
```

Job will run when launchd loads (at login or system start).

### Run Only on Specific Days

```xml
<key>StartCalendarInterval</key>
<dict>
    <key>Weekday</key>
    <integer>1</integer>  <!-- Monday = 1, Sunday = 7 -->
    <key>Hour</key>
    <integer>7</integer>
    <key>Minute</key>
    <integer>0</integer>
</dict>
```

**Multiple specific days:**

```xml
<key>StartCalendarInterval</key>
<array>
    <dict>
        <key>Weekday</key>
        <integer>1</integer>  <!-- Monday -->
        <key>Hour</key>
        <integer>7</integer>
    </dict>
    <dict>
        <key>Weekday</key>
        <integer>3</integer>  <!-- Wednesday -->
        <key>Hour</key>
        <integer>7</integer>
    </dict>
    <dict>
        <key>Weekday</key>
        <integer>5</integer>  <!-- Friday -->
        <key>Hour</key>
        <integer>7</integer>
    </dict>
</array>
```

### Keep Job Alive (Continuous Running)

```xml
<key>KeepAlive</key>
<true/>
```

**Warning:** This is NOT recommended for NeuroHelix. The job should run once per day and exit.

### Throttle Interval

Prevent rapid restarts if job fails:

```xml
<key>ThrottleInterval</key>
<integer>3600</integer>  <!-- Wait 1 hour before restart -->
```

---

## Monitoring

### Check Last Run

```bash
# Last modified orchestrator log
ls -lt logs/orchestrator_*.log | head -1
```

### Check Success

```bash
# Check if today's report exists
ls -lh data/reports/daily_report_$(date +%Y-%m-%d).md

# Check if today's dashboard exists
ls -lh dashboards/dashboard_$(date +%Y-%m-%d).html
```

### Automated Monitoring Script

Create `check_automation.sh`:

```bash
#!/bin/bash
# Check if NeuroHelix automation ran successfully today

DATE=$(date +%Y-%m-%d)
REPORT="data/reports/daily_report_${DATE}.md"
DASHBOARD="dashboards/dashboard_${DATE}.html"

if [ -f "$REPORT" ] && [ -f "$DASHBOARD" ]; then
    echo "✅ Automation ran successfully today"
    echo "   Report: $REPORT ($(wc -l < "$REPORT") lines)"
    echo "   Dashboard: $DASHBOARD"
    exit 0
else
    echo "❌ Automation may have failed today"
    echo "   Report exists: $([ -f "$REPORT" ] && echo "Yes" || echo "No")"
    echo "   Dashboard exists: $([ -f "$DASHBOARD" ] && echo "Yes" || echo "No")"
    echo ""
    echo "Check logs: tail logs/launchd_stderr.log"
    exit 1
fi
```

Run daily (e.g., at 8 AM) to verify 7 AM run succeeded.

---

## Comparison: launchd vs. cron

### Why launchd?

| Feature | launchd | cron |
|---------|---------|------|
| **Modern macOS** | ✅ Recommended | ⚠️ Deprecated |
| **Missed runs** | Runs on next opportunity | Skips if Mac was off |
| **Logging** | Built-in StandardOut/Error | Manual redirection |
| **Calendar** | Rich scheduling options | Basic time format |
| **Environment** | Clean, configurable | Inherits limited env |
| **Status** | `launchctl list` | No built-in status |

### launchd Advantages

1. **Catch-up execution:** If Mac was sleeping, job runs when it wakes
2. **Better logging:** Separate stdout/stderr logs
3. **Rich scheduling:** Multiple times, specific days, etc.
4. **Status queries:** Easy to check if loaded and last exit status
5. **macOS native:** Better integration with system

### When to Use cron

- Linux systems
- Simple time-based schedules
- Cross-platform scripts

---

## Migration from cron

If you previously used cron:

1. Remove cron entry:
   ```bash
   crontab -e
   # Delete NeuroHelix line
   ```

2. Install launchd automation:
   ```bash
   ./install_automation.sh
   ```

3. Verify:
   ```bash
   launchctl list | grep neurohelix
   ```

---

## Uninstallation

### Complete Removal

```bash
# Uninstall automation
./uninstall_automation.sh

# Verify removal
launchctl list | grep neurohelix
# Should return nothing

# Plist should be gone
ls ~/Library/LaunchAgents/com.neurohelix.daily.plist
# Should return "No such file"
```

### Keep Data

Uninstalling automation does NOT delete:
- Research outputs (`data/outputs/`)
- Reports (`data/reports/`)
- Dashboards (`dashboards/`)
- Logs (`logs/`)
- Configuration (`config/`)

To also remove data:
```bash
rm -rf data/ logs/ dashboards/
```

---

## Best Practices

1. **Test before scheduling:**
   ```bash
   ./scripts/orchestrator.sh  # Manual test
   ```

2. **Monitor first few runs:**
   ```bash
   tail -f logs/launchd_stdout.log
   ```

3. **Check logs weekly:**
   ```bash
   grep -i error logs/launchd_stderr.log
   ```

4. **Verify outputs exist:**
   ```bash
   ls -lh data/reports/daily_report_$(date +%Y-%m-%d).md
   ```

5. **Keep system awake during scheduled time:**
   - Or use `RunAtLoad` to run at next login

---

## Related Documentation

- [README.md](../README.md) - Project overview
- [STATUS.md](../STATUS.md) - System status
- [Gemini CLI Configuration](gemini-cli-config.md) - CLI setup

---

**Version:** 1.0  
**Last Updated:** 2025-11-06  
**Platform:** macOS (launchd)
