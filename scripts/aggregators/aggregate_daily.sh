#!/bin/bash
# Aggregate daily results into intelligent synthesized report

set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../config/env.sh"
source "${SCRIPTS_DIR}/lib/telemetry.sh"

DATE=$(date +%Y-%m-%d)
INPUT_DIR="${DATA_DIR}/outputs/daily/${DATE}"
REPORT_DIR="${DATA_DIR}/reports"
REPORT_FILE="${REPORT_DIR}/daily_report_${DATE}.md"
COMBINED_FILE="${REPORT_DIR}/combined_findings_${DATE}.md"
SYNTHESIS_PROMPT_FILE="${REPORT_DIR}/synthesis_prompt_${DATE}.txt"

mkdir -p "$REPORT_DIR"

# Idempotency check: Skip if report already exists and is complete
if [ -f "$REPORT_FILE" ] && grep -q "## End of Report" "$REPORT_FILE" 2>/dev/null; then
    echo "✅ Report already exists for ${DATE}, skipping aggregation"
    echo "   To regenerate, delete: $REPORT_FILE"
    exit 0
fi

if [ ! -d "$INPUT_DIR" ]; then
    echo "Error: No output directory for ${DATE}"
    exit 1
fi

echo "Aggregating and synthesizing results for ${DATE}..."

# Function to generate execution summary from telemetry ledger
generate_execution_summary() {
    local date="$1"
    local ledger_file="${RUNTIME_DIR}/execution_ledger_${date}.json"
    local log_file="${LOGS_DIR}/prompt_execution_${date}.log"
    
    # Check if ledger exists (backward compatibility)
    if [ ! -f "$ledger_file" ]; then
        echo "<!-- No execution telemetry available for this report -->"
        return 0
    fi
    
    # Extract summary statistics
    local total=$(grep '"total":' "$ledger_file" 2>/dev/null | sed 's/.*"total": \([0-9]*\).*/\1/' || echo 0)
    local successful=$(grep '"successful":' "$ledger_file" 2>/dev/null | sed 's/.*"successful": \([0-9]*\).*/\1/' || echo 0)
    local failed=$(grep '"failed":' "$ledger_file" 2>/dev/null | sed 's/.*"failed": \([0-9]*\).*/\1/' || echo 0)
    local total_duration=$(grep '"total_duration_seconds":' "$ledger_file" 2>/dev/null | sed 's/.*"total_duration_seconds": \([0-9]*\).*/\1/' || echo 0)
    
    # Start building summary section
    cat << SUMMARY_HEADER

---

## Prompt Execution Summary

**Execution Statistics:**
- Total Prompts: ${total}
- Successful: ✅ ${successful}
- Failed: ❌ ${failed}
- Total Duration: $(format_duration ${total_duration})
- Telemetry Log: \`${log_file}\`

### Execution Details

| Prompt Name | Category | Status | Duration | Completed At |
|-------------|----------|--------|----------|-------------|
SUMMARY_HEADER
    
    # Parse JSON ledger and create table rows
    # Use awk for more robust JSON parsing
    awk '
        /"prompt_name":/ {
            gsub(/.*"prompt_name": "/, "");
            gsub(/".*/, "");
            prompt_name = $0;
        }
        /"category":/ {
            gsub(/.*"category": "/, "");
            gsub(/".*/, "");
            category = $0;
        }
        /"status":/ {
            gsub(/.*"status": "/, "");
            gsub(/".*/, "");
            status = $0;
            if (status == "success") {
                status_icon = "✅";
            } else {
                status_icon = "❌";
            }
        }
        /"duration_seconds":/ {
            gsub(/.*"duration_seconds": /, "");
            gsub(/,.*/, "");
            duration = $0;
        }
        /"end_time":/ {
            gsub(/.*"end_time": "/, "");
            gsub(/".*/, "");
            # Extract just time portion (HH:MM:SS)
            split($0, time_parts, "T");
            if (length(time_parts) > 1) {
                split(time_parts[2], time_only, "+");
                split(time_only[1], hms, ":");
                end_time = hms[1] ":" hms[2] ":" hms[3];
            } else {
                end_time = $0;
            }
        }
        /"error":/ && !/"error": null/ {
            gsub(/.*"error": "/, "");
            gsub(/".*/, "");
            # Truncate error to 50 chars
            error = substr($0, 1, 50);
            if (length($0) > 50) error = error "...";
        }
        /}/ {
            if (prompt_name != "") {
                # Format duration
                if (duration < 60) {
                    duration_str = duration "s";
                } else if (duration < 3600) {
                    minutes = int(duration / 60);
                    seconds = duration % 60;
                    duration_str = minutes "m " seconds "s";
                } else {
                    hours = int(duration / 3600);
                    minutes = int((duration % 3600) / 60);
                    duration_str = hours "h " minutes "m";
                }
                
                printf "| %s | %s | %s | %s | %s |\n", prompt_name, category, status_icon, duration_str, end_time;
                
                # Reset for next entry
                prompt_name = "";
                category = "";
                status = "";
                duration = 0;
                end_time = "";
                error = "";
            }
        }
    ' "$ledger_file"
    
    # Add failure details if any
    if [ "$failed" -gt 0 ]; then
        cat << FAILURE_SECTION

### Failed Prompts Details

The following prompts encountered errors during execution:

FAILURE_SECTION
        
        # Extract and display failure details
        grep -A 10 '"status": "failure"' "$ledger_file" | awk '
            /"prompt_name":/ {
                gsub(/.*"prompt_name": "/, "");
                gsub(/".*/, "");
                prompt_name = $0;
            }
            /"error":/ && !/"error": null/ {
                gsub(/.*"error": "/, "");
                gsub(/".*/, "");
                error = $0;
                if (prompt_name != "") {
                    printf "**%s:**\n\n", prompt_name;
                    printf "%s\n\n", error;
                    prompt_name = "";
                }
            }
        '
        
        echo "For detailed error information, review the telemetry log at:"
        echo "\`${log_file}\`"
    fi
    
    echo ""
}

# Step 1: Combine all findings into a single document for AI analysis
echo "📊 Collecting findings from $(ls -1 "$INPUT_DIR"/*.md 2>/dev/null | wc -l | xargs) research domains..."

cat > "$COMBINED_FILE" << 'COMBINED_HEADER'
# Combined Research Findings

This document contains all research findings from today's automated research cycle.
Each section represents a different research domain.

---

COMBINED_HEADER

# Collect all domain outputs with metadata
for file in "$INPUT_DIR"/*.md; do
    if [ -f "$file" ]; then
        basename="$(basename "$file" .md)"
        echo "" >> "$COMBINED_FILE"
        echo "### Domain: ${basename//_/ }" >> "$COMBINED_FILE"
        echo "" >> "$COMBINED_FILE"
        cat "$file" >> "$COMBINED_FILE"
        echo "" >> "$COMBINED_FILE"
        echo "---" >> "$COMBINED_FILE"
        echo "" >> "$COMBINED_FILE"
    fi
done

# Step 2: Create sophisticated synthesis prompt
echo "🧠 Creating synthesis prompt..."

cat > "$SYNTHESIS_PROMPT_FILE" << 'SYNTHESIS_PROMPT'
You are an expert research analyst synthesizing today's AI and technology research findings.

Your task is to analyze ALL the research findings below and create a comprehensive, well-structured daily report.

**CRITICAL: You MUST use this EXACT markdown structure. Do not deviate from this heading hierarchy:**

```
### Executive Summary

[200-300 words identifying 3-5 most significant developments, emerging patterns, cross-domain connections, and strategic implications]

### Key Themes & Insights

[Brief overview paragraph with key insights, organized by theme NOT by source]

### Model & Technology Advances

[Content about AI models, research breakthroughs, technical capabilities]

### Market Dynamics & Business Strategy

[Content about investments, partnerships, acquisitions, competitive moves]

### Regulatory & Policy Developments

[Content about laws, governance, policy statements, regulatory changes]

### Developer Tools & Ecosystem

[Content about coding tools, frameworks, platforms, developer experience]

### Hardware & Compute Landscape

[Content about GPUs, TPUs, compute infrastructure, edge devices]

### Notable Developments

* [Specific announcement 1 with concrete details]
* [Specific announcement 2 with concrete details]
* [Specific announcement 3 with concrete details]
* [5-10 total items, prioritizing novelty and impact]

### Strategic Implications

[Analysis of what these developments mean for AI developers, enterprise adoption, competitive landscape, and future research directions]

### Actionable Recommendations

1. [Specific action based on today's findings]
2. [Opportunity to explore]
3. [Risk to monitor]
4. [3-5 total items]
```

**REQUIREMENTS:**

1. **Use ONLY h3 headings (###)** - Never use h2 (##) or h4 (####) for main sections
2. **Keep the exact section names** - "Model & Technology Advances", "Market Dynamics & Business Strategy", etc.
3. **Executive Summary** must be 200-300 words
4. **Notable Developments** must be a bullet list (not numbered)
5. **Actionable Recommendations** must be a numbered list
6. Synthesize across domains - do not list by source
7. Remove redundancy - many domains mention the same events
8. Prioritize signal over noise
9. Cite specific sources when referencing concrete facts
10. Maintain analytical, objective tone - no marketing hype

**FORMATTING:**

- Use **bold** for emphasis on key terms
- Use > blockquotes for especially important insights
- Use bullet points (*) for Notable Developments
- Use numbered lists (1., 2., 3.) for Actionable Recommendations
- Keep paragraphs concise and scannable

Now analyze the following research findings and generate the report using the EXACT structure above:

---

SYNTHESIS_PROMPT

# Append the combined findings
cat "$COMBINED_FILE" >> "$SYNTHESIS_PROMPT_FILE"

# Step 3: Generate synthesized report using AI
echo "🤖 Generating synthesized report (this may take 30-60 seconds)..."

SYNTHESIZED_REPORT="${REPORT_DIR}/synthesized_${DATE}.md"

${GEMINI_CLI} --model "${GEMINI_MODEL}" --output-format "${GEMINI_OUTPUT_FORMAT}" \
    "$(cat "$SYNTHESIS_PROMPT_FILE")" < /dev/null > "$SYNTHESIZED_REPORT" 2>&1 || {
    echo "❌ Error: Synthesis failed"
    echo "Falling back to simple concatenation..."
    cp "$COMBINED_FILE" "$SYNTHESIZED_REPORT"
}

# Step 4: Build final report with header and footer
echo "📝 Building final report..."

cat > "$REPORT_FILE" << REPORT_HEADER
# NeuroHelix Daily Intelligence Report

**Date:** ${DATE}  
**Generated:** $(date +"%Y-%m-%d %H:%M:%S")  
**Research Domains:** $(ls -1 "$INPUT_DIR"/*.md 2>/dev/null | wc -l | xargs)  
**Analysis Type:** AI-Synthesized Cross-Domain Analysis

---

REPORT_HEADER

# Append synthesized content
cat "$SYNTHESIZED_REPORT" >> "$REPORT_FILE"

# Add execution summary before footer
generate_execution_summary "$DATE" >> "$REPORT_FILE"

# Add footer with metadata
cat >> "$REPORT_FILE" << 'REPORT_FOOTER'

---

## Report Metadata

**Sources:**
- AI Ecosystem Watch
- Tech Regulation Pulse
- Emergent Open-Source Activity
- Hardware & Compute Landscape
- Ethics & Alignment
- Model Comparison Digest
- Corporate Strategy Roundup
- Startup Radar
- Developer-Tool Evolution
- Prompt-Engineering Trends
- Cross-Domain Insights
- Market Implications

**Methodology:**
This report was generated through automated research across multiple domains, 
followed by AI-powered synthesis to identify patterns, connections, and insights 
across the collected information. Raw findings were analyzed and restructured to 
present a coherent narrative rather than isolated data points.

**Note:** This is an automated intelligence report. All findings should be 
independently verified before making strategic decisions.

## End of Report

REPORT_FOOTER

# Cleanup temporary files
rm -f "$COMBINED_FILE" "$SYNTHESIS_PROMPT_FILE" 2>/dev/null || true

echo "✅ Synthesized report created: $REPORT_FILE"
echo "📊 Report size: $(wc -l < "$REPORT_FILE") lines"
echo "🎯 Analysis complete"
