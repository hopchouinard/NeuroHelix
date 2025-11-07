#!/bin/bash
# Generate interactive HTML dashboard

set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../config/env.sh"

DATE=$(date +%Y-%m-%d)
REPORT_FILE="${DATA_DIR}/reports/daily_report_${DATE}.md"
DASHBOARD_FILE="${DASHBOARD_DIR}/dashboard_${DATE}.html"

mkdir -p "$DASHBOARD_DIR"

# Idempotency check: Skip if dashboard already exists and is complete
if [ -f "$DASHBOARD_FILE" ] && grep -q "</html>" "$DASHBOARD_FILE" 2>/dev/null; then
    DASHBOARD_SIZE=$(wc -l < "$DASHBOARD_FILE" | xargs)
    if [ "$DASHBOARD_SIZE" -gt 100 ]; then
        echo "✅ Dashboard already exists for ${DATE} (${DASHBOARD_SIZE} lines)"
        echo "   To regenerate, delete: $DASHBOARD_FILE"
        # Still update symlink
        ln -sf "dashboard_${DATE}.html" "${DASHBOARD_DIR}/latest.html"
        exit 0
    fi
fi

if [ ! -f "$REPORT_FILE" ]; then
    echo "Error: Report file not found"
    exit 1
fi

echo "Generating dashboard for ${DATE}..."

# Create HTML template
cat > "$DASHBOARD_FILE" << 'HTML'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NeuroHelix Dashboard - DATE_PLACEHOLDER</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            line-height: 1.6;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 40px;
        }
        h1 {
            color: #667eea;
            margin-bottom: 10px;
            font-size: 2.5em;
        }
        .meta {
            color: #666;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #e0e0e0;
        }
        .section {
            margin: 30px 0;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }
        h2 {
            color: #764ba2;
            margin-bottom: 15px;
        }
        code {
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }
        pre {
            background: #2d2d2d;
            color: #f8f8f2;
            padding: 15px;
            border-radius: 6px;
            overflow-x: auto;
        }
        .highlight {
            background: #fff3cd;
            padding: 15px;
            border-left: 4px solid #ffc107;
            margin: 15px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🧠 NeuroHelix Dashboard</h1>
        <div class="meta">
            <strong>Date:</strong> DATE_PLACEHOLDER<br>
            <strong>Status:</strong> ✅ Pipeline Completed<br>
            <strong>Generated:</strong> TIMESTAMP_PLACEHOLDER
        </div>
        <div id="content">
CONTENT_PLACEHOLDER
        </div>
    </div>
</body>
</html>
HTML

# Convert markdown to HTML (simple conversion)
echo "<div class='section'>" > "${DASHBOARD_FILE}.content.tmp"
awk '
    /^# / { sub(/^# /, ""); print "<h2>" $0 "</h2>"; next }
    /^## / { sub(/^## /, ""); print "<h3>" $0 "</h3>"; next }
    /^### / { sub(/^### /, ""); print "<h4>" $0 "</h4>"; next }
    /^\* / { sub(/^\* /, ""); print "<li>" $0 "</li>"; next }
    /^---$/ { print "</div><hr><div class='section'>"; next }
    /^$/ { print "<br>"; next }
    { print "<p>" $0 "</p>" }
' "$REPORT_FILE" >> "${DASHBOARD_FILE}.content.tmp"
echo "</div>" >> "${DASHBOARD_FILE}.content.tmp"

# Build complete dashboard file from scratch
cat > "$DASHBOARD_FILE" << 'DASHBOARD_START'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NeuroHelix Dashboard - DATEPLACEHOLDER</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            line-height: 1.6;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 40px;
        }
        h1 {
            color: #667eea;
            margin-bottom: 10px;
            font-size: 2.5em;
        }
        h2 {
            color: #764ba2;
            margin: 25px 0 15px 0;
            font-size: 1.8em;
        }
        h3 {
            color: #555;
            margin: 20px 0 10px 0;
        }
        h4 {
            color: #666;
            margin: 15px 0 8px 0;
        }
        .meta {
            color: #666;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #e0e0e0;
        }
        .section {
            margin: 20px 0;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }
        p {
            margin: 8px 0;
        }
        li {
            margin: 5px 0 5px 20px;
        }
        hr {
            margin: 30px 0;
            border: none;
            border-top: 2px solid #e0e0e0;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🧠 NeuroHelix Dashboard</h1>
        <div class="meta">
            <strong>Date:</strong> DATEPLACEHOLDER<br>
            <strong>Status:</strong> ✅ Pipeline Completed<br>
            <strong>Generated:</strong> TIMEPLACEHOLDER
        </div>
        <div id="content">
DASHBOARD_START

# Append content
cat "${DASHBOARD_FILE}.content.tmp" >> "$DASHBOARD_FILE"

# Append closing tags
cat >> "$DASHBOARD_FILE" << 'DASHBOARD_END'
        </div>
    </div>
</body>
</html>
DASHBOARD_END

# Replace placeholders
sed -i.bak "s/DATEPLACEHOLDER/${DATE}/g" "$DASHBOARD_FILE"
sed -i.bak "s/TIMEPLACEHOLDER/$(date +"%Y-%m-%d %H:%M:%S")/g" "$DASHBOARD_FILE"
rm -f "${DASHBOARD_FILE}.bak" "${DASHBOARD_FILE}.content.tmp" 2>/dev/null || true

# Create symlink to latest dashboard
ln -sf "dashboard_${DATE}.html" "${DASHBOARD_DIR}/latest.html"

echo "✅ Dashboard created: $DASHBOARD_FILE"
echo "🌐 View at: file://${DASHBOARD_FILE}"
