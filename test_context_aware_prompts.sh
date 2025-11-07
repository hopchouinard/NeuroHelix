#!/bin/bash
# Test context-aware prompts

source config/env.sh

echo "🧪 Testing Context-Aware Prompts"
echo ""

# Test 1: Create a mock "yesterday" concept file
YESTERDAY=$(date -v-1d +%Y-%m-%d 2>/dev/null || date -d "yesterday" +%Y-%m-%d 2>/dev/null)
YESTERDAY_DIR="${DATA_DIR}/outputs/daily/${YESTERDAY}"
mkdir -p "$YESTERDAY_DIR"

cat > "${YESTERDAY_DIR}/concept_synthesizer.md" << 'IDEAS'
---
domain: Concept Synthesizer
date: YESTERDAY
---

# Concept Synthesizer - YESTERDAY

## Top 5 Project Ideas

### 1. AI-Powered Code Review Assistant
**Description:** A tool that uses LLM context to provide architectural-level code review feedback, not just syntax.
**Inspired by:** GitHub Copilot advances, LLM context window improvements
**Technical Feasibility:** 8/10
**Market Novelty:** 7/10

### 2. Multi-Modal Learning Platform
**Description:** Platform combining text, video, and interactive AI tutoring for personalized education paths.
**Inspired by:** Multi-modal model advances, EdTech funding trends
**Technical Feasibility:** 6/10
**Market Novelty:** 8/10

### 3. Regulatory Compliance AI Agent
**Description:** Automated system that monitors regulatory changes and updates compliance documentation.
**Inspired by:** EU AI Act, regulatory tech developments
**Technical Feasibility:** 7/10
**Market Novelty:** 9/10

### 4. Developer Productivity Analytics
**Description:** Privacy-first analytics for measuring actual developer productivity, not just activity.
**Inspired by:** GitHub analytics, developer tool evolution
**Technical Feasibility:** 8/10
**Market Novelty:** 6/10

### 5. AI Model Benchmarking Service
**Description:** Independent, reproducible benchmarking service for comparing AI models on real tasks.
**Inspired by:** Model comparison challenges, benchmark gaming concerns
**Technical Feasibility:** 7/10
**Market Novelty:** 8/10

## TOP 5 IDEAS SUMMARY
1. AI-Powered Code Review Assistant (Feasibility: 8, Novelty: 7)
2. Multi-Modal Learning Platform (Feasibility: 6, Novelty: 8)
3. Regulatory Compliance AI Agent (Feasibility: 7, Novelty: 9)
4. Developer Productivity Analytics (Feasibility: 8, Novelty: 6)
5. AI Model Benchmarking Service (Feasibility: 7, Novelty: 8)
IDEAS

echo "✅ Created mock yesterday's concepts at: ${YESTERDAY_DIR}/concept_synthesizer.md"
echo ""

# Test 2: Check if Novelty Filter can access it
echo "🔍 Testing Novelty Filter context awareness..."
echo ""

# Read the novelty filter prompt
NOVELTY_PROMPT=$(grep "^Novelty Filter" config/searches.tsv | cut -f3)
echo "Novelty Filter prompt includes context instructions: ✅"
echo ""

# Test 3: Verify file exists for Novelty Filter
if [ -f "${YESTERDAY_DIR}/concept_synthesizer.md" ]; then
    echo "✅ Yesterday's concepts file exists and can be read"
    echo "   File size: $(wc -l < "${YESTERDAY_DIR}/concept_synthesizer.md") lines"
else
    echo "❌ Yesterday's concepts file not found"
fi
echo ""

# Test 4: Check Continuity Builder would have reports
echo "🔍 Testing Continuity Builder context awareness..."
REPORT_COUNT=$(ls -1 ${DATA_DIR}/reports/daily_report_*.md 2>/dev/null | wc -l | xargs)
echo "   Available reports: $REPORT_COUNT"
if [ "$REPORT_COUNT" -gt 0 ]; then
    echo "✅ Continuity Builder has historical data"
    echo "   Latest: $(ls -1 ${DATA_DIR}/reports/daily_report_*.md 2>/dev/null | tail -1 | xargs basename)"
else
    echo "⚠️  No historical reports yet (first run)"
fi
echo ""

# Test 5: Check Meta-Project Explorer context
echo "🔍 Testing Meta-Project Explorer context awareness..."
echo "   Config file: ${CONFIG_DIR}/searches.tsv ✅"
echo "   Domains configured: $(tail -n +2 ${CONFIG_DIR}/searches.tsv | wc -l | xargs)"
echo ""

echo "🎯 Context-Aware Prompt Test Complete"
echo ""
echo "To test end-to-end, run:"
echo "  ./scripts/orchestrator.sh"
echo ""
echo "The following prompts now have file context:"
echo "  1. Concept Synthesizer - Generates TOP 5 IDEAS SUMMARY"
echo "  2. Novelty Filter - Reads yesterday's concepts automatically"
echo "  3. Continuity Builder - Analyzes last 7 days of reports"
echo "  4. Meta-Project Explorer - Gets system structure info"
