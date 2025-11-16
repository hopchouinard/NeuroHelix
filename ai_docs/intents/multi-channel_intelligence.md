# 🧠 NeuroHelix – New Cognition & Multi-Channel Intelligence Extensions

This document compiles all functionalities discussed after the previous specification document. It focuses on expanding NeuroHelix beyond a daily research-and-synthesis pipeline into a multi-channel cognitive system with layered intelligence, selective search strategies, external LLM calls, and multi-format outputs.

⸻

## 1. Multi-Channel Cognitive Architecture

NeuroHelix will evolve from a single daily report generator into a distributed cognition system with four parallel modes of information delivery.

### 1.1 High-Effort Cognition: Written Deep Dive
 - Existing functionality becomes Channel A.
 - Continues generating:
 - Daily analytical reports
 - Cross-correlations
 - Trend analysis (7-day, 30-day, 365-day)
 - Synthesized insight documents
 - Adds exposure of raw materials through an IDE-inspired navigation layout.

### 1.2 Medium-Effort Cognition: Narrative Podcast Output
 - Converts the daily written report into:
 - A multi-persona conversational debate
 - Contextual storytelling around news
 - A long-form narrative suitable for voice synthesis (11Labs)
 - Output becomes a “daily podcast episode.”

### 1.3 Low-Effort Cognition: Condensed Micro-Summary
 - Three-sentence distillation of:
 - The main theme of the day
 - Priority signal
 - Critical shifts
 - Delivered as text or short audio clip.

### 1.4 Interrupt Cognition: Event-Triggered Alerts
 - New system for pushing urgent updates outside the daily cycle:
 - Significant changes in monitored subjects
 - Breaking events detected in real time
 - Cross-subject anomalies
 - Delivery options include Discord, email, or push notifications.

⸻

## 2. Multi-Layered Search Strategy (New Research Pipeline)

The research model becomes tiered, reducing hallucination risk and increasing precision.

### 2.1 Lightweight “Probe” Search (Perplexity/Sonar-Pro)
 - Before deep research, NeuroHelix will:
 - Query Perplexity Sonar-Pro via OpenRouter
 - Ask: “Is there news for subject X in the last 24 hours?”
 - Receive a boolean + short summary
 - Only subjects confirmed to have new information will proceed to full research.

### 2.2 Hierarchical Subject Decomposition
 - Subjects may be decomposed into smaller micro-topics (probes):
 - Fine-grained queries (e.g., topic/company/event specifics)
 - Mid-level aggregation (themes across companies)
 - High-level thematic synthesis
 - Supports stacking cognition from bottom-up.

### 2.3 Heavy Research via Gemini CLI (Flash/Pro)
 - Complex queries, tool-use and agentic reasoning delegated to:
 - Gemini 2.5 Flash for fast research
 - Gemini 2.5 Pro for synthesis & reflection
 - Heavy queries only run after lightweight probe confirmation.

### 2.4 Integration Strategy
 - Light model → “Should we investigate?”
 - Heavy agent → “Investigate deeply.”
 - The pipeline becomes:

User subjects → Probe Search → Validated List → Deep Research → Synthesis → Multi-Channel Outputs


⸻

### 3. Multi-Agent, Multi-Model Cognitive Loop

NeuroHelix now leverages:
 - OpenRouter LLM calls
 - Gemini CLI agentic workflows
 - Local Llama-CPP for housekeeping and RAG maintenance
 - Optional GPT-5.1 for narrative podcast script generation

### 3.1 Role Assignment
 - Perplexity/Sonar-Pro: fast boolean probes
 - Gemini Flash/Pro: core research + cognitive analysis
 - GPT-5.1: narrative podcast construction
 - Local Llama-CPP agent:
 - Vector store maintenance
 - Embedding refresh
 - Cleanup and classification

⸻

## 4. Vector Database + Daily Knowledge Ingestion

Introduce a local vector DB storing all daily research.

### 4.1 Daily Embedding Pipeline
 - Each day’s raw and synthesized output is embedded
 - Stored locally (e.g., Chroma, LanceDB, Milvus Lite)
 - Local Q4/Q5 models used for embedding to reduce cloud cost

### 4.2 Knowledge Expansion & Novel Insight Detection
 - NeuroHelix can query the vector DB daily:
 - Detect contradictions
 - Identify unexplored connections
 - Discover cross-subject analogies
 - Perform meta-insight generation beyond the daily report

### 4.3 Third Layer Cognition
 - Vector DB becomes the “long-term memory cortex”
 - New prompts mine the accumulated memory for:
 - Novel insight
 - Trend discovery
 - Hypothesis formation
 - Project idea generation

⸻

## 5. Automated Project Ideation Layer

NeuroHelix now:
 - Generates project ideas daily
 - Scores them
 - Compares today’s ideas with yesterday’s ideas
 - Detects recurring themes to raise priority

Future extension:
 - Multi-day trend detection across idea patterns
 - Prioritization algorithms inspired by reinforcement signals

⸻

## 6. Multi-Device Output Modes

NeuroHelix becomes multimodal in how it communicates.

### 6.1 Published Website (Astro)
 - Written deep dive
 - Podcast script
 - Raw research materials (IDE-inspired layout)
 - Timeline charts for:
 - 7-day trends
 - 30-day trends
 - 365-day trends

### 6.2 Discord / Notification Output
 - Breaking-news alerts
 - Daily micro-summary in text or audio form

### 6.3 Podcast Audio via 11Labs
 - Automatic generation of a “NeuroHelix Daily Podcast”

⸻

## 7. Architectural Philosophy: Distributed Cognition

NeuroHelix evolves from:
 - A daily tool
into:
 - A multi-channel cognitive assistant
 - A personal research satellite constellation
 - A continuously thinking system distributed across:
 - Local compute
 - Cloud LLMs
 - A vector memory stack

The system builds long-term knowledge, reacts in real time, and adapts its pipeline dynamically.

⸻

## 8. Next Steps for Implementation Planning

This document serves as a foundation for a new feature spec. A coding agent should be asked to:
 1. Decompose each feature into actionable tasks
 2. Identify prerequisites (local vector DB, OpenRouter config, notification integration)
 3. Produce scaffolding, module boundaries, and Typer workflows
 4. Evaluate model selection for each cognitive layer

NeuroHelix is no longer a research script.
It is becoming a distributed cognition platform.

⸻
