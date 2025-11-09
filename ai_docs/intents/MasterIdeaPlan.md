# Project Overview: Automated Research & Ideation Ecosystem

1. Core Concept

Use Gemini CLI (or any LLM-capable CLI) in headless mode, orchestrated by Bash + cron, to execute a daily pipeline of AI-driven research, synthesis, and project ideation tasks.
Each step is modular and model-agnostic: Gemini CLI for discovery, Copilot CLI for planning, Claude Code or Cloud Code for implementation.

⸻

2. Architectural Layers

Layer Function Tool Example
Scheduler / Orchestrator Executes recurring jobs, manages logs, and coordinates stages cron + bash
Manifest / Config Stores the list of research or task prompts searches.tsv or searches.csv
Executor Layer Runs each prompt in parallel, handles retries, writes outputs Gemini CLI (headless)
Summarizer Layer Aggregates daily Markdown results into a unified report Gemini CLI again
Renderer Layer Converts daily Markdown into a single-file, self-contained HTML dashboard Gemini CLI (prompted for design generation)
Notifier Layer Optionally emails or posts summaries for review/approval local mail or Discord bot
Meta-Prompt Layer (optional) Updates or extends the workflow itself using stored templates Gemini CLI or local model


⸻

3. Daily Workflow
 1. Cron Trigger – At a scheduled hour (e.g., 07:00 AM), a bash script runs.
 2. Prompt Execution – Each line in the TSV defines a research domain or task; Gemini CLI runs them in parallel.
 3. Output Storage – Each prompt produces a structured Markdown file (with YAML front-matter) stored by date.
 4. Aggregation – Another Gemini CLI call merges all Markdown files into a daily summary (daily_report.md).
 5. Visualization – A final Gemini CLI pass converts the summary into a self-contained interactive HTML dashboard.
 6. Optional Notification – Email or Discord message links you to the dashboard for the day.

⸻

4. Evolutionary Expansion
 • Idea Loop – Each day’s summaries feed a corpus. The next run uses that corpus to generate new project ideas, validate them against market data, and rank by novelty or potential.
 • Recursive Reasoning – The system cross-references new ideas with previous ones and external sources, pruning duplicates and enriching promising leads.
 • Autonomous R&D Flow – Once an idea reaches a novelty threshold, it spawns a PRD (via Gemini) → project specification (via Copilot CLI + SpecKit) → proof-of-concept generation (via Cloud Code).

⸻

5. Long-Term Vision

This evolves into a self-improving knowledge and creation ecosystem:
 • Gemini CLI acts as the cognitive front-end—researcher, analyst, and summarizer.
 • Copilot CLI plans and organizes execution.
 • Cloud Code or Claude Code implements prototypes.
 • The cron/Bash framework is the heartbeat, ensuring daily iteration.
 • You remain the final approval layer—deciding which automatically generated ideas become real projects.

⸻

6. Key Benefits
 • Low complexity: just shell scripts and text files—no custom backend.
 • Model-agnostic: Gemini for prototyping, local LLMs for production.
 • Cost-efficient: one daily reasoning cycle, minimal token use.
 • Private & portable: can run entirely on local infrastructure.
 • Continuously creative: system never sleeps; it evolves through daily loops.

⸻

7. Optional Meta-Automation

A “meta-job” could even manage its own templates:
 • Reads existing workflow configs.
 • Adds new research categories or adjusts file structures.
 • Rewrites its prompts as needs evolve.
Essentially, the system updates itself, staying aligned with your goals through natural-language instructions.

⸻

In short:
You’ve designed a self-contained, AI-driven lab where Bash provides time, Gemini provides thought, and you provide judgment. Every morning you wake up to a dashboard of new insights, refined ideas, and sometimes a working prototype—all born while you slept.
