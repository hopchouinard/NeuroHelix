# NeuroHelix – Problem Definition (Bash → Python/Typer Orchestrator)

This document captures the problem to be solved and the requirements the future solution must satisfy. It avoids prescribing implementation details.

1. Problem Statement

NeuroHelix currently uses Bash scripts to orchestrate a headless, multi-call workflow around Gemini CLI to collect research, transform it, and publish artifacts. Bash proved the concept but hampers growth: weak state management, limited configurability, fragile error handling, and no consistent telemetry. The goal is to replace the orchestration layer with a Python/Typer command-line application that:
 Hello preserves existing behavior, outputs, and scheduling;
 - manages context flow between multiple Gemini CLI runs;
 - centralizes configuration and policy (e.g., per‑prompt model selection);
 - provides reliable safety rails (locking, idempotency, cleanups);
 - surfaces auditable telemetry suitable for long‑term operations.

2. Objectives & In‑Scope
 - Orchestrate multi-stage runs where independent Gemini CLI calls read/write local files and later stages consume earlier artifacts.
 - Centralize and enforce per‑prompt execution policy (model, tools, temperature, timeouts, retries).
 - Provide first-class operations for daily runs, cleanup, reprocess‑today, automation installation/status, and publish handoff.
 - Maintain an execution ledger and audit trail for reproducibility and diagnosis.
 - Keep current directory structure and artifact types stable unless explicitly changed by requirements.

3. Out‑of‑Scope (for this project)
 - Rewriting Gemini CLI features or replacing it with direct SDK calls.
 - Redesigning the Astro/Cloudflare publication system.
 - Building a GUI. (A future management UI may be considered later.)

4. Stakeholders & Actors
 - Operator: runs daily pipelines, performs maintenance, reads diagnostics.
 - Maintainer: adjusts configuration/policies and prompt registry; triages failures.
 - Downstream Publisher: consumes exported JSON/markdown to update the website.
 - Auditor: verifies run lineage, inputs, outputs, and decisions.

5. Context & Environment
 - Runtime OS: macOS (LaunchD automation) with Node/PNPM, Wrangler, and Gemini CLI installed.
 - Filesystem: local repo with known folders for runtime, logs, outputs, and publishing payloads.
 - Concurrency: multiple headless Gemini CLI processes may run in parallel; orchestrator must ensure safe file access and predictable aggregation.

6. Current System Overview (as‑is)
 - Source prompts defined in a tabular list (TSV).
 - Bash orchestrates six steps: search, aggregation, tag extraction, render, export, publish.
 - Gemini CLI performs research and file I/O headlessly; each call can execute multi-step internal tasks.
 - LaunchD triggers daily execution at fixed times.
 - Maintenance scripts perform cleanup and reprocess‑today.

7. Functional Requirements

7.1 Orchestration
 - Execute a daily pipeline consisting of multiple waves of Gemini CLI calls.
 - Later waves must be able to consume artifacts produced by earlier waves via file paths.
 - Provide a single entrypoint for an entire run, plus sub-commands for maintenance and publishing.

7.2 Context Passing & Lineage
 - Track, by run date and prompt id, the source inputs, configuration used, and produced artifacts.
 - Maintain a dependency graph (implicit or explicit) that defines which outputs feed which subsequent steps.
 - Record lineage in a machine-readable ledger (JSON/JSONL) to make downstream analysis reproducible.

7.3 Prompt Policy & Registry
 - Define a prompt registry that maps each prompt to its execution policy: model, tools, temperature, token budget, retries, timeout, and expected outputs.
 - Support categorization/tags (e.g., fetch, transform, insight) to group prompts into waves.
 - Allow future migration of the registry from TSV to a light database without breaking consumers.

7.4 Concurrency & Scheduling Control
 - Permit controlled parallelism within a wave, with a configurable maximum concurrency.
 - Ensure isolation: prevent output collisions and partial-write corruption.
 - Stagger launches when needed and perform bounded retries with backoff.

7.5 Artifact Management
 - Preserve existing output locations and file naming unless explicitly revised.
 - Write completion markers/metadata per task (status, duration, hashes) alongside artifacts.
 - Support --force to recompute specific artifacts while leaving others intact.

7.6 Configuration Management
 - Centralize settings via environment variables and an optional config file.
 - Allow per-command overrides through CLI flags.
 - Validate configuration at startup; fail fast with actionable diagnostics.

7.7 Automation Operations
 - Provide operations to install/uninstall/status the daily scheduler (LaunchD on macOS).
 - Report last and next run times, and whether the job is currently loaded.

7.8 Observability & Telemetry
 - Emit human-readable logs for operators and structured logs for machines.
 - Maintain a per-run execution ledger that includes: timestamps, prompts executed, models used, parameters, exit codes, durations, output hashes/paths.
 - Keep an audit trail for maintenance commands (cleanup, reprocess) with who/when/what.

7.9 Safety Rails
 - Enforce single-run via locking to prevent concurrent orchestrations clobbering state.
 - Verify clean working directory before destructive actions unless explicitly overridden.
 - Provide dry-run mode for any command that mutates state.

7.10 Idempotency & Determinism
 - Re-running the same date without --force must not duplicate work or alter artifacts.
 - Where upstream LLM variability is unavoidable, log parameterization and content hashes so diffs are detectable.

7.11 Error Handling
 - Standardize exit codes and error categories (setup failure, external tool failure, artifact missing, lock acquisition failure, etc.).
 - Provide retries for transient errors and surface clear, operator-focused remediation messages.

7.12 Publication Handoff
 - Produce a structured export artifact compatible with the existing site builder.
 - Optionally trigger the existing publish routine, capturing deployment metadata.

8. Data Requirements
 - Inputs: prompt registry (TSV initially), environment tokens, previous run artifacts where applicable.
 - Outputs: per-prompt files (markdown/json), daily aggregated report, tags, export JSON for publishing, structured logs, execution ledger, audit logs.
 - Metadata: run id/date, prompt id, policy parameters, start/end times, durations, exit status, retries, dependent inputs, content hashes.

9. Constraints & Policies
 - Must continue using Gemini CLI as the execution engine (no SDK rewrite in this phase).
 - Must run under macOS with existing toolchain available on PATH.
 - Must keep daily schedule compatibility with existing LaunchD expectations.
 - Network access patterns must respect rate limits and free-tier constraints.

10. Non‑Functional Requirements
 - Reliability: pipeline must recover from partial failures via retries and clear resumability rules.
 - Performance: orchestration overhead should be negligible relative to LLM work; concurrency caps must be configurable.
 - Security: secrets sourced from environment or secure files; no secrets logged; permissions checked on writable paths.
 - Maintainability: code and config must be organized, documented, and testable.
 - Testability: enable unit tests (parsers, registry, ledger) and integration tests with a small fixture prompt set.
 - Usability: CLI must present consistent verbs, flags, and helpful messages.

11. Acceptance Criteria (verifiable)
 - A daily run for a fixed date reproduces the same directory tree and file presence as the Bash pipeline for the same inputs.
 - Execution ledger and logs contain, at minimum, model choices, parameters, timings, exit codes, and content hashes for each artifact.
 - Cleanup and reprocess‑today operations succeed with dry-run previews and confirmations, and cannot run concurrently with a live pipeline.
 - LaunchD install/status/uninstall produce expected outcomes on a standard macOS host.

12. Migration Requirements
 - Provide a parity mapping from existing scripts/flags to new commands/flags.
 - Support a transition period where both orchestrations can be run against a frozen test date to compare outputs.
 - Document differences in behavior or file naming, if any, and supply a one-time migration guide.

13. Risks
 - Hidden dependencies in Bash scripts that are not documented.
 - Race conditions from concurrent Gemini CLI runs writing to adjacent paths.
 - Upstream changes to Gemini CLI behaviors or defaults.

14. Assumptions
 - The headless multi-step capability of Gemini CLI remains available and stable.
 - The operator has compatible versions of Node/PNPM, Wrangler, and Gemini CLI installed.
 - The filesystem layout used by downstream publishing is correctly understood and fixed during migration.

15. Open Questions (to resolve before design)
 - Exact, canonical list of prompt classes and their required policy fields (model, tools, temperature, token budget, timeout, retry policy).
 - Formal definition of waves and dependencies: static sequencing vs. per‑prompt dependency declarations.
 - Desired concurrency defaults and hard caps per wave/class.
 - Required schemas for the execution ledger and audit logs (minimum and nice‑to‑have fields).
 - Canonical naming conventions for artifacts and completion markers.
 - How to handle partial reruns: per‑prompt --force or per‑wave, and how to detect stale intermediates.
 - Publication trigger policy: always run, opt‑in via flag, or config-driven.
 - Registry backend roadmap: remain TSV for v1 or introduce SQLite immediately with a read‑only adapter for TSV?
 - Diagnostics scope: which external commands and versions must be verified at startup?
 - What constitutes a “successful day” for acceptance testing: byte‑for‑byte equality or structural parity with hash records?

16. Glossary
 - Wave: a set of prompts that may execute concurrently and whose outputs feed a later wave.
 - Prompt Registry: authoritative list of prompt definitions and execution policies.
 - Execution Ledger: per-run structured record of what was executed, with parameters and results metadata.
 - Audit Log: record of maintenance actions affecting state outside the normal pipeline run.
