#!/usr/bin/env python3
"""Stub Gemini CLI for integration testing.

This stub records invocations and returns fixture responses instead of
calling the real Gemini API. Used for integration testing without API costs.
"""

import json
import sys
from datetime import datetime
from pathlib import Path


def main():
    """Main stub entry point."""
    # Parse arguments
    args = sys.argv[1:]

    # Record invocation
    invocation_log = Path("/tmp/stub_gemini_invocations.jsonl")
    invocation = {
        "timestamp": datetime.now().isoformat(),
        "args": args,
        "cwd": str(Path.cwd()),
    }

    with open(invocation_log, "a") as f:
        f.write(json.dumps(invocation) + "\n")

    # Parse model and prompt from args
    model = "gemini-2.5-flash"
    prompt = ""

    i = 0
    while i < len(args):
        if args[i] == "--model" and i + 1 < len(args):
            model = args[i + 1]
            i += 2
        else:
            # Assume it's the prompt
            prompt = args[i]
            i += 1

    # Generate fixture response based on prompt
    response = generate_fixture_response(prompt)

    # Write to stdout (will be captured by subprocess.run)
    print(response)

    # Exit successfully
    sys.exit(0)


def generate_fixture_response(prompt: str) -> str:
    """Generate a fixture response based on the prompt.

    Args:
        prompt: The prompt text

    Returns:
        Fixture response text
    """
    # Extract key topic from prompt
    prompt_lower = prompt.lower()

    if "ai ecosystem" in prompt_lower or "announcements" in prompt_lower:
        return """# AI Ecosystem Watch

**Date:** 2025-11-14

## Key Announcements

1. **OpenAI releases GPT-5 preview** - New multimodal capabilities
2. **Anthropic announces Claude 4** - Extended 500K context window
3. **Google updates Gemini 2.5** - Improved reasoning and coding

## Research Milestones

- New transformer architecture achieving SOTA on MMLU
- Breakthrough in AI alignment research from Anthropic
- Meta releases open-source LLaMA 4

## Developer Tools

- GitHub Copilot Enterprise launched
- New Claude Code features for pair programming
- Cursor IDE reaches 1M developers
"""

    elif "regulation" in prompt_lower or "policy" in prompt_lower:
        return """# Tech Regulation Pulse

**Date:** 2025-11-14

## North America

- US Congress introduces AI Safety Act
- California passes SB-1047 for AI model licensing
- FTC investigates AI competitive practices

## European Union

- AI Act implementation guidelines published
- GDPR updates for AI systems
- Digital Services Act enforcement begins

## Business Impacts

- Compliance costs for AI startups increasing
- Model cards now mandatory for EU deployment
- Data residency requirements tightening
"""

    elif "open-source" in prompt_lower or "open source" in prompt_lower:
        return """# Emergent Open-Source Activity

**Date:** 2025-11-14

## New Frameworks

1. **Mixtral-8x22B** - New MoE architecture from Mistral AI
2. **Llama-4-70B** - Meta's latest open model
3. **Stable Diffusion 4** - Image generation improvements

## Libraries & Tools

- LangChain 0.3 with streaming support
- LlamaIndex for RAG applications
- AutoGen for multi-agent systems

## Datasets

- OpenHermes-3 instruction dataset (500K samples)
- CodeAlpaca for code generation
- MMLU-Pro extended benchmark
"""

    elif "synthesis" in prompt_lower or "innovative project" in prompt_lower:
        return """# Concept Synthesizer

**Date:** 2025-11-14

## Evidence Summary

Based on today's research, key themes include: AI regulation intensifying, open-source
models reaching parity with proprietary, developer tooling advancing rapidly, and
ethical concerns driving policy changes.

## Top 5 Innovative Projects

### 1. Regulatory Compliance Copilot
An AI assistant that helps companies navigate AI regulations across jurisdictions.
**Feasibility:** 8/10 | **Novelty:** 7/10
**Inspired by:** Tech Regulation Pulse findings on compliance complexity

### 2. Open-Source Model Marketplace
A platform for discovering, comparing, and deploying open-source LLMs.
**Feasibility:** 9/10 | **Novelty:** 6/10
**Inspired by:** Emergent Open-Source Activity tracking

### 3. Multi-Modal Knowledge Graph Builder
Tool that extracts entities and relationships from diverse content types.
**Feasibility:** 7/10 | **Novelty:** 8/10
**Inspired by:** AI Ecosystem Watch on multimodal capabilities

### 4. Distributed Training Orchestrator
System for coordinating training across consumer hardware.
**Feasibility:** 6/10 | **Novelty:** 9/10
**Inspired by:** Open-source democratization trends

### 5. AI Safety Testing Suite
Automated framework for adversarial testing of LLMs.
**Feasibility:** 8/10 | **Novelty:** 7/10
**Inspired by:** Regulation push for model safety

## TOP 5 IDEAS SUMMARY
1. Regulatory Compliance Copilot (Feas: 8, Nov: 7)
2. Open-Source Model Marketplace (Feas: 9, Nov: 6)
3. Multi-Modal Knowledge Graph Builder (Feas: 7, Nov: 8)
4. Distributed Training Orchestrator (Feas: 6, Nov: 9)
5. AI Safety Testing Suite (Feas: 8, Nov: 7)
"""

    else:
        # Generic response for other prompts
        return f"""# Research Response

**Date:** 2025-11-14

## Summary

This is a fixture response for integration testing. The prompt was analyzed and
a contextual response was generated.

## Key Findings

- Finding 1: Based on recent developments in AI
- Finding 2: Industry trends suggest continued growth
- Finding 3: Regulatory landscape evolving rapidly

## Analysis

The data indicates several important patterns that warrant further investigation.
Cross-domain insights suggest opportunities for innovation in multiple areas.

## Recommendations

1. Monitor developments closely
2. Consider strategic partnerships
3. Invest in compliance infrastructure
"""


if __name__ == "__main__":
    main()
