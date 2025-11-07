# Context-Aware Prompts

## Overview

NeuroHelix includes a **context-aware prompt system** that automatically provides relevant historical data and file system context to specific research domains. This enables temporal analysis, trend tracking, and self-improvement capabilities.

## How It Works

### Architecture

```
┌─────────────────────────────────────────────────┐
│  Prompt Definition (config/searches.tsv)        │
│  - Declares need for context                    │
│  - Specifies what data is needed                │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│  Executor (scripts/executors/run_prompts.sh)    │
│  - Detects context-aware domains                │
│  - Loads relevant historical files              │
│  - Enhances prompt with actual data             │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│  Gemini CLI Execution                           │
│  - Receives enhanced prompt with file content   │
│  - Analyzes with full historical context        │
└─────────────────────────────────────────────────┘
```

### Context Injection Points

The executor detects specific domain names and automatically injects relevant context:

| Domain | Context Provided | Files Accessed |
|--------|------------------|----------------|
| **Concept Synthesizer** | None (generates baseline) | Output format structured for reuse |
| **Novelty Filter** | Yesterday's 5 ideas | `data/outputs/daily/YYYY-MM-DD/concept_synthesizer.md` |
| **Continuity Builder** | Last 7 days of reports | `data/reports/daily_report_*.md` (7 most recent) |
| **Meta-Project Explorer** | System structure & config | `config/searches.tsv`, directory listings |

---

## Context-Aware Domains

### 1. Concept Synthesizer

**Purpose:** Generate 5 innovative project ideas from today's research

**Context Provided:** None (this is the baseline generator)

**Output Structure:**
```markdown
## Top 5 Project Ideas

### 1. [Title]
**Description:** [2-3 sentences]
**Inspired by:** [Research findings]
**Technical Feasibility:** X/10
**Market Novelty:** Y/10

[... repeat for ideas 2-5 ...]

## TOP 5 IDEAS SUMMARY
1. [Title] (Feasibility: X, Novelty: Y)
2. [Title] (Feasibility: X, Novelty: Y)
...
```

**Why:** Creates structured output that Novelty Filter can easily parse tomorrow.

---

### 2. Novelty Filter

**Purpose:** Re-evaluate yesterday's ideas with today's research findings

**Context Provided:**
- Yesterday's concept synthesizer output
- File path: `data/outputs/daily/YYYY-MM-DD/concept_synthesizer.md`
- Full content of yesterday's 5 ideas with ratings

**Prompt Enhancement:**
```bash
# Original prompt
"Evaluate yesterday's top 5 ideas..."

# Enhanced with context
"Evaluate yesterday's top 5 ideas...

YESTERDAY'S IDEAS (from 2025-11-05):
[Full content of concept_synthesizer.md]"
```

**Behavior:**
- If yesterday's file exists → Analyzes with actual ideas
- If file missing → States "No previous ideas found - skipping evaluation"

**Example Output:**
```markdown
## Re-evaluated Ideas (2025-11-06)

### 1. AI-Powered Code Review Assistant
**Original Ratings:** Feasibility: 8/10, Novelty: 7/10
**Updated Assessment:** Feasibility increased to 9/10 due to 
today's announcement of GitHub Copilot X with architectural 
review features. Market novelty decreased to 5/10 as this 
space is now crowded.
**Recommendation:** MONITOR - Strong execution risk

[... analysis for all 5 ideas ...]

## Final Ranking
1. **Keep Pursuing:** Regulatory Compliance AI Agent, ...
2. **Monitor:** AI-Powered Code Review, ...
3. **Archive:** Developer Productivity Analytics
```

---

### 3. Continuity Builder

**Purpose:** Identify patterns across the last 7 days of research

**Context Provided:**
- Last 7 days of synthesized reports (or fewer if unavailable)
- File paths: `data/reports/daily_report_YYYY-MM-DD.md`
- First 200 lines of each report (to manage token limits)

**Prompt Enhancement:**
```bash
# Original prompt
"Compare the last 7 days of idea summaries..."

# Enhanced with context
"Compare the last 7 days of idea summaries...

AVAILABLE REPORTS:

=== Report from 2025-11-06 ===
[First 200 lines]

=== Report from 2025-11-05 ===
[First 200 lines]

[... up to 7 days ...]"
```

**Behavior:**
- Loads up to 7 most recent reports
- If fewer than 7 days exist, uses available data
- Notes the limitation in output

**Example Output:**
```markdown
## 7-Day Pattern Analysis (2025-10-30 to 2025-11-06)

**Data Available:** 5 days (system started 2025-11-02)

### Persistent Themes
1. **Model Context Windows:** Mentioned in 4/5 reports, 
   accelerating trend
2. **Regulatory Compliance:** Present in all 5 reports, 
   EU AI Act implementation driving discussion

### Emerging Trends
- **Multi-modal Integration:** Weak signal on days 1-2, 
  strong signal days 4-5
- **Cost Optimization:** Mentioned once (day 3), not recurring

### Contradictory Signals
- Open-source vs. closed models: conflicting narratives 
  about performance parity

### Meta-Themes
- Convergence of developer tools toward AI-native workflows
- Regulatory pressure creating new product categories
```

---

### 4. Meta-Project Explorer

**Purpose:** Suggest improvements to the research system itself

**Context Provided:**
- System directory structure
- List of configured research domains
- Recent report filenames
- Configuration file locations

**Prompt Enhancement:**
```bash
# Original prompt
"Based on accumulated daily reports, suggest improvements..."

# Enhanced with context
"Based on accumulated daily reports, suggest improvements...

SYSTEM STRUCTURE:
- Output directory: /path/to/data/outputs/daily/
- Reports directory: /path/to/data/reports/
- Recent reports available:
  daily_report_2025-11-06.md
  daily_report_2025-11-05.md
  [...]

CURRENT SEARCH DOMAINS:
AI Ecosystem Watch       Research
Tech Regulation Pulse    Research
[... all 20 domains ...]"
```

**Example Output:**
```markdown
## System Improvement Suggestions (2025-11-06)

### 1. Research Domain Changes
**Add:**
- "AI Safety Incidents" (high) - Track real-world AI failures
- "Energy Efficiency" (medium) - Growing concern in reports

**Merge:**
- "Startup Radar" + "Developer-Tool Evolution" → "AI Tooling Ecosystem"
  Rationale: 80% content overlap in recent reports

**Remove:**
- None recommended at this time

### 2. Prompt Quality Improvements
**Prompt-Engineering Trends:** Too narrow, expand to:
"Identify new techniques, frameworks, AND architectural patterns 
discussed by practitioners"

### 3. Synthesis Enhancements
- Add "Investment Signals" section to daily report
- Current thematic grouping works well, keep structure

### 4. Output Format
**Missing:** 
- Weekly rollup report (synthesize 7 days into executive brief)
- JSON export for programmatic analysis
```

---

## Implementation Details

### Date Calculation (Cross-Platform)

The executor handles both macOS and Linux date commands:

```bash
# macOS (BSD date)
YESTERDAY=$(date -v-1d +%Y-%m-%d 2>/dev/null || \
            date -d "yesterday" +%Y-%m-%d 2>/dev/null)

# Tries both formats, uses whichever succeeds
```

### Token Management

**Challenge:** Historical context can exceed token limits

**Solutions:**
1. **Novelty Filter:** Full content (typically <2000 tokens)
2. **Continuity Builder:** First 200 lines per report (~1500 tokens × 7 = 10,500 tokens)
3. **Meta-Project Explorer:** Summaries only, not full content

### Error Handling

**Graceful Degradation:**

```bash
if [ -f "$YESTERDAY_CONCEPTS" ]; then
    # Provide context
    enhanced_prompt="...with yesterday's ideas..."
else
    # Continue without context
    enhanced_prompt="...Note: No previous ideas found..."
fi
```

**Benefits:**
- First-day runs succeed (no historical data yet)
- Missing files don't break the pipeline
- Clear communication about data availability

---

## Testing Context Awareness

### Unit Test

Run the provided test script:

```bash
./test_context_aware_prompts.sh
```

**Checks:**
- ✅ Creates mock historical data
- ✅ Verifies file access paths
- ✅ Confirms prompt enhancements
- ✅ Validates system structure info

### Integration Test

Run full pipeline and check outputs:

```bash
# Day 1: Generate baseline concepts
./scripts/orchestrator.sh

# Check Concept Synthesizer output has TOP 5 IDEAS SUMMARY
grep "TOP 5 IDEAS SUMMARY" data/outputs/daily/$(date +%Y-%m-%d)/concept_synthesizer.md

# Day 2: Run again (next day)
./scripts/orchestrator.sh

# Check Novelty Filter used yesterday's ideas
grep "YESTERDAY'S IDEAS" data/outputs/daily/$(date +%Y-%m-%d)/novelty_filter.md
```

### Manual Verification

```bash
# Verify Continuity Builder has multi-day context
cat data/outputs/daily/$(date +%Y-%m-%d)/continuity_builder.md | grep "Report from"

# Verify Meta-Project Explorer sees system structure
cat data/outputs/daily/$(date +%Y-%m-%d)/meta-project_explorer.md | grep "SYSTEM STRUCTURE"
```

---

## Adding New Context-Aware Prompts

### Step 1: Update TSV Prompt

Add context instructions to the prompt:

```tsv
New Domain	Category	CONTEXT: You need to access [files]. Description...	priority	enabled
```

### Step 2: Update Executor

Add case to `scripts/executors/run_prompts.sh`:

```bash
case "$domain" in
    # ... existing cases ...
    "New Domain")
        # Load required files
        SOME_FILE="${DATA_DIR}/path/to/file.md"
        if [ -f "$SOME_FILE" ]; then
            enhanced_prompt="${prompt}\n\nDATA:\n$(cat \"$SOME_FILE\")"
        fi
        ;;
esac
```

### Step 3: Test

```bash
# Create mock data
echo "test" > data/path/to/file.md

# Run executor
./scripts/executors/run_prompts.sh

# Verify context was injected
grep "DATA:" data/outputs/daily/$(date +%Y-%m-%d)/new_domain.md
```

---

## Best Practices

### 1. Structured Output in Generators

When creating prompts that generate data for later use:
- Use clear section headers (## TOP 5 IDEAS SUMMARY)
- Include machine-parseable ratings (Feasibility: X/10)
- Maintain consistent formatting

### 2. Defensive File Access

Always check file existence:
```bash
if [ -f "$FILE" ]; then
    # Use file
else
    # Graceful fallback
fi
```

### 3. Token Budget Management

For large historical data:
- Use `head -N` to limit lines
- Summarize instead of including full content
- Consider sampling (every Nth day) for long histories

### 4. Clear Context Markers

In enhanced prompts, use clear markers:
```
YESTERDAY'S IDEAS (from 2025-11-05):
=== Report from 2025-11-06 ===
SYSTEM STRUCTURE:
```

This helps the LLM understand the context structure.

---

## Troubleshooting

### Issue: "No previous ideas found"

**Cause:** First-day run or missing yesterday's output

**Solution:** 
- Expected on first day - system will generate baseline
- Check file exists: `ls data/outputs/daily/YYYY-MM-DD/concept_synthesizer.md`
- If missing, re-run yesterday: `rm data/outputs/daily/YYYY-MM-DD/.execution_complete`

### Issue: Continuity Builder says "No reports available"

**Cause:** Fewer than 1 day of historical data

**Solution:**
- Wait for more days to accumulate
- System is working correctly, just needs time

### Issue: Context not appearing in output

**Cause:** Executor not detecting domain name

**Solution:**
- Check exact domain name in TSV matches case statement
- Verify enhanced_prompt is being used (not original prompt)
- Enable debug: `GEMINI_DEBUG="true"` in config/env.sh

---

## Future Enhancements

### Planned Features

1. **Corpus Builder**
   - Long-term storage of ideas across months
   - Searchable idea database
   - Trend analysis over 30/90/365 days

2. **Cross-Reference System**
   - Link related ideas across days
   - Track idea evolution
   - Identify idea clusters

3. **Automated Validation**
   - Check if yesterday's recommended ideas gained traction
   - Compare predictions with actual developments
   - Self-calibration of recommendation quality

4. **Context Compression**
   - Intelligent summarization for token efficiency
   - Semantic search instead of full content
   - Embedding-based similarity matching

---

## Related Documentation

- [README.md](../README.md) - Project overview
- [Gemini CLI Configuration](gemini-cli-config.md) - CLI setup
- [Synthesis System](../SYNTHESIS_COMPLETE.md) - Report generation

---

**Version:** 1.0  
**Last Updated:** 2025-11-06  
**Status:** Production Ready ✅
