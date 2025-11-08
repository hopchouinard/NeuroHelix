#!/bin/bash
# Extract tags and categories from completed daily report
# This runs AFTER aggregate_daily.sh creates the report

set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../config/env.sh"

DATE=$(date +%Y-%m-%d)
REPORT_FILE="${DATA_DIR}/reports/daily_report_${DATE}.md"
TAGS_OUTPUT="${DATA_DIR}/reports/tags_${DATE}.json"

# Idempotency check: Skip if tags already exist and report hasn't changed
if [ -f "$TAGS_OUTPUT" ]; then
    if [ "$REPORT_FILE" -ot "$TAGS_OUTPUT" ]; then
        echo "✅ Tags already extracted for ${DATE} and are up-to-date"
        echo "   To regenerate, delete: $TAGS_OUTPUT"
        exit 0
    else
        echo "🔄 Report has been updated, regenerating tags..."
    fi
fi

if [ ! -f "$REPORT_FILE" ]; then
    echo "❌ Error: Report file not found: $REPORT_FILE"
    exit 1
fi

echo "🏷️  Extracting tags and categories from ${DATE} report..."

# Create prompt for Gemini to extract tags
TAG_EXTRACTION_PROMPT=$(cat << 'TAG_PROMPT'
You are a keyword extraction and categorization expert. Analyze the research report below and generate structured metadata.

**CRITICAL: Output ONLY valid JSON (no markdown code blocks, no explanation, no extra text).**

Required format:
{
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "categories": ["category1", "category2", "category3"]
}

Rules:
1. Extract 5-8 concise tags (1-3 words each) representing:
   - Key technologies (e.g., "GPT-5", "Claude 4.5", "NVIDIA Blackwell")
   - Major companies mentioned (e.g., "OpenAI", "Google", "Microsoft")
   - Important concepts (e.g., "AI Agents", "Edge AI", "Regulation")
   - Market trends (e.g., "Enterprise AI", "Open Source", "Funding")

2. Map findings to 3-5 categories from this list:
   - AI Models
   - Market Analysis  
   - Regulation
   - Strategy
   - Developer Tools
   - Hardware
   - Research
   - Safety & Ethics

3. Prioritize tags and categories that appear prominently in the Executive Summary and Key Themes sections

4. Output MUST be valid, parseable JSON with no additional text

Now analyze this report:

---

TAG_PROMPT
)

# Append the report content
FULL_PROMPT="${TAG_EXTRACTION_PROMPT}$(cat "$REPORT_FILE")"

# Call Gemini to extract tags
echo "🤖 Calling AI to extract tags (this may take 10-15 seconds)..."

TEMP_OUTPUT="${TAGS_OUTPUT}.tmp"

${GEMINI_CLI} --model "${GEMINI_MODEL}" --output-format "text" \
    "$FULL_PROMPT" < /dev/null > "$TEMP_OUTPUT" 2>&1 || {
    echo "❌ Error: Tag extraction failed"
    echo "Falling back to empty tags..."
    echo '{"tags": [], "categories": []}' > "$TAGS_OUTPUT"
    rm -f "$TEMP_OUTPUT"
    exit 0  # Non-fatal, continue pipeline
}

# Clean the output (remove markdown code blocks if present)
# Extract everything from first { to last } (handles multiline JSON)
CLEANED_JSON=$(cat "$TEMP_OUTPUT" | \
    grep -v "^Loaded cached credentials" | \
    sed '/^```json/d' | \
    sed '/^```/d' | \
    awk '/^\{/,/^\}/' | \
    tr -d '\n' | \
    sed 's/  */ /g')

# Validate JSON
if [ -n "$CLEANED_JSON" ] && echo "$CLEANED_JSON" | jq empty 2>/dev/null; then
    echo "$CLEANED_JSON" | jq . > "$TAGS_OUTPUT"
    rm -f "$TEMP_OUTPUT"
    
    # Display results
    TAGS_COUNT=$(jq -r '.tags | length' "$TAGS_OUTPUT")
    CATEGORIES_COUNT=$(jq -r '.categories | length' "$TAGS_OUTPUT")
    
    echo "✅ Tags extracted successfully: $TAGS_OUTPUT"
    echo "🏷️  Extracted $TAGS_COUNT tags and $CATEGORIES_COUNT categories"
    
    # Show the tags for visibility
    echo "   Tags: $(jq -r '.tags | join(", ")' "$TAGS_OUTPUT")"
    echo "   Categories: $(jq -r '.categories | join(", ")' "$TAGS_OUTPUT")"
else
    echo "⚠️  Warning: AI output was not valid JSON"
    echo "   Raw output: $CLEANED_JSON"
    echo "   Falling back to empty tags..."
    echo '{"tags": [], "categories": []}' > "$TAGS_OUTPUT"
    rm -f "$TEMP_OUTPUT"
fi
