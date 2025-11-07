#!/bin/bash
# Export structured JSON payload for static site from daily report
# This script parses the markdown report and creates a machine-readable format

set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../config/env.sh"

DATE=$(date +%Y-%m-%d)
REPORT_FILE="${DATA_DIR}/reports/daily_report_${DATE}.md"
TAGS_FILE="${DATA_DIR}/outputs/daily/${DATE}/keyword_tag_generator.md"
OUTPUT_DIR="${PUBLISHING_DIR}"
OUTPUT_FILE="${OUTPUT_DIR}/${DATE}.json"

mkdir -p "$OUTPUT_DIR"

# Idempotency check: Skip if JSON exists and report hasn't changed
if [ -f "$OUTPUT_FILE" ]; then
    if [ "$REPORT_FILE" -ot "$OUTPUT_FILE" ]; then
        echo "✅ Payload already exported for ${DATE} and is up-to-date"
        echo "   To regenerate, delete: $OUTPUT_FILE"
        exit 0
    else
        echo "🔄 Report has been updated, regenerating payload..."
    fi
fi

if [ ! -f "$REPORT_FILE" ]; then
    echo "❌ Error: Report file not found: $REPORT_FILE"
    exit 1
fi

echo "📦 Exporting structured payload for ${DATE}..."

# Extract header metadata
GENERATED=$(grep "^\*\*Generated:\*\*" "$REPORT_FILE" | sed 's/\*\*Generated:\*\* //' | xargs)
DOMAINS_COUNT=$(grep "^\*\*Research Domains:\*\*" "$REPORT_FILE" | sed 's/\*\*Research Domains:\*\* //' | xargs)

# Extract title (first ## heading after the frontmatter)
TITLE=$(grep -m 1 "^## " "$REPORT_FILE" | sed 's/^## //')

# Extract Executive Summary section
SUMMARY=$(awk '
    /^### Executive Summary$/ { flag=1; next }
    /^### / && flag { exit }
    flag && NF { print }
' "$REPORT_FILE" | sed 's/"/\\"/g' | awk '{printf "%s ", $0}' | sed 's/ $//')

# Extract tags and categories from Keyword Tag Generator output
TAGS_JSON="{\"tags\": [], \"categories\": []}"
if [ -f "$TAGS_FILE" ]; then
    # Try to extract JSON from the tags file (could be wrapped in markdown code blocks)
    TAGS_CONTENT=$(cat "$TAGS_FILE")
    # Try to extract JSON between { and }
    EXTRACTED_JSON=$(echo "$TAGS_CONTENT" | grep -o '{[^}]*}' | head -1 || echo "")
    if [ -n "$EXTRACTED_JSON" ]; then
        # Validate it's valid JSON
        if echo "$EXTRACTED_JSON" | jq empty 2>/dev/null; then
            TAGS_JSON="$EXTRACTED_JSON"
        fi
    fi
fi

TAGS=$(echo "$TAGS_JSON" | jq -r '.tags // [] | @json')
CATEGORIES=$(echo "$TAGS_JSON" | jq -r '.categories // [] | @json')

# Extract thematic sections (all ### headings except specific metadata sections)
SECTIONS=$(awk '
    BEGIN { 
        in_section = 0
        section_heading = ""
        section_content = ""
        first = 1
    }
    /^### Thematic Sections$/ { next }
    /^### Executive Summary$/ { next }
    /^### Key Themes & Insights$/ { next }
    /^---$/ && /^### Notable Developments$/ { next }
    /^---$/ && /^### Strategic Implications$/ { next }
    /^---$/ && /^### Actionable Recommendations$/ { next }
    /^## Report Metadata$/ { exit }
    /^### / {
        if (in_section && section_heading != "") {
            gsub(/"/, "\\\"", section_content)
            gsub(/\n/, " ", section_content)
            if (!first) printf ","
            printf "{\"heading\":\"%s\",\"content\":\"%s\"}", section_heading, section_content
            first = 0
        }
        section_heading = substr($0, 5)
        section_content = ""
        in_section = 1
        next
    }
    in_section && NF {
        if (section_content != "") section_content = section_content " "
        section_content = section_content $0
    }
    END {
        if (in_section && section_heading != "") {
            gsub(/"/, "\\\"", section_content)
            gsub(/\n/, " ", section_content)
            if (!first) printf ","
            printf "{\"heading\":\"%s\",\"content\":\"%s\"}", section_heading, section_content
        }
    }
' "$REPORT_FILE")

# Extract Notable Developments (bullet list)
NOTABLE=$(awk '
    BEGIN { count = 0 }
    /^---$/ { in_notable = 0 }
    /^### Notable Developments$/ { in_notable = 1; next }
    in_notable && /^\* / {
        content = substr($0, 3)
        gsub(/"/, "\\\"", content)
        if (count > 0) printf ","
        printf "\"%s\"", content
        count++
    }
' "$REPORT_FILE")

# Extract Strategic Implications section
STRATEGIC_IMPL=$(awk '
    /^---$/ && seen_strategic { exit }
    /^### Strategic Implications$/ { flag=1; seen_strategic=1; next }
    /^---$/ && flag { exit }
    /^### / && flag { exit }
    flag && NF { print }
' "$REPORT_FILE" | sed 's/"/\\"/g' | awk '{printf "%s ", $0}' | sed 's/ $//')

# Extract Actionable Recommendations (numbered or bullet list)
RECOMMENDATIONS=$(awk '
    /^---$/ && seen_rec { exit }
    /^### Actionable Recommendations$/ { flag=1; seen_rec=1; next }
    /^---$/ && flag { exit }
    /^## / && flag { exit }
    flag && /^[0-9]+\./ {
        content = $0
        sub(/^[0-9]+\. /, "", content)
        gsub(/"/, "\\\"", content)
        if (count > 0) printf ","
        printf "\"%s\"", content
        count++
    }
' "$REPORT_FILE")

# Get full raw markdown content
RAW_MARKDOWN=$(cat "$REPORT_FILE" | jq -Rs .)

# Build JSON payload
cat > "$OUTPUT_FILE" << EOF
{
  "date": "${DATE}",
  "generated": "${GENERATED}",
  "domains_count": ${DOMAINS_COUNT:-0},
  "title": "${TITLE}",
  "summary": "${SUMMARY}",
  "tags": ${TAGS},
  "categories": ${CATEGORIES},
  "sections": [${SECTIONS}],
  "notable_developments": [${NOTABLE}],
  "strategic_implications": "${STRATEGIC_IMPL}",
  "recommendations": [${RECOMMENDATIONS}],
  "raw_markdown": ${RAW_MARKDOWN},
  "permalink": "/dashboards/${DATE}"
}
EOF

# Validate JSON
if ! jq empty "$OUTPUT_FILE" 2>/dev/null; then
    echo "❌ Error: Generated JSON is invalid"
    echo "   Output file: $OUTPUT_FILE"
    exit 1
fi

echo "✅ Payload exported successfully: $OUTPUT_FILE"
echo "📊 Payload size: $(du -h "$OUTPUT_FILE" | cut -f1)"
echo "🏷️  Tags extracted: $(echo "$TAGS" | jq -r 'length') tags, $(echo "$CATEGORIES" | jq -r 'length') categories"
