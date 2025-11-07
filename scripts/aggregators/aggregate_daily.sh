#!/bin/bash
# Aggregate daily results into intelligent synthesized report

set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../config/env.sh"

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

Your task is to analyze ALL the research findings below and create a comprehensive, well-structured daily report that:

**REQUIREMENTS:**

1. **Executive Summary** (200-300 words)
   - Identify the 3-5 most significant developments
   - Highlight emerging patterns and trends
   - Surface unexpected connections between different domains
   - Provide strategic implications

2. **Key Themes & Insights** (organized by theme, NOT by source)
   - Group related findings across different research domains
   - Identify cross-domain patterns (e.g., regulation + tech development)
   - Highlight contradictions or tensions
   - Surface non-obvious connections

3. **Thematic Sections** (create 4-6 sections based on natural themes in the data)
   - Model & Technology Advances
   - Market Dynamics & Business Strategy  
   - Regulatory & Policy Developments
   - Developer Tools & Ecosystem
   - Research & Academic Progress
   - (Add other themes as needed based on findings)

4. **Notable Developments** (bullet list)
   - Highlight 5-10 specific announcements/releases
   - Include concrete details (names, versions, companies)
   - Prioritize novelty and impact

5. **Strategic Implications**
   - What do these developments mean for:
     - AI application developers
     - Enterprise adoption
     - Competitive landscape
     - Future research directions

6. **Actionable Recommendations** (3-5 specific actions)
   - Concrete next steps based on today's findings
   - Opportunities to explore
   - Risks to monitor

**CRITICAL INSTRUCTIONS:**

- DO NOT simply list findings by domain
- DO synthesize and connect information across domains
- DO remove redundancy (many domains may mention the same development)
- DO prioritize signal over noise
- DO use clear headings and structure
- DO cite specific sources when mentioning concrete facts
- DO NOT use marketing language or hype
- DO maintain analytical, objective tone

**FORMAT:**

Use clean Markdown with:
- ## for main sections
- ### for subsections  
- **bold** for emphasis
- Bullet points for lists
- > blockquotes for key insights

Now analyze the following research findings:

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
