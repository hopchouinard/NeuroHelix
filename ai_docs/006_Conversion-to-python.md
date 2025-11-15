# NeuroHelix Python Orchestrator Specification

## Context
- NeuroHelix currently depends on chained Bash scripts (`scripts/orchestrator.sh`) to drive Gemini CLI across six prompt waves; this proved the concept but lacks durable state, error isolation, and observability.
- Daily runs, cleanup, reprocess-today, and publish handoffs all live in separate scripts with inconsistent flags, which complicates LaunchD automation and parity testing.
- The pipeline’s outputs (markdown, JSON exports, tags, logs) must remain stable so downstream specs—especially `004_static_site_publishing.md` and `005_new_neurohelix_layout.md`—ingest identical artifacts.
- Operators, maintainers, and auditors all need a single Typer-based CLI that orchestrates the workflow, enforces policy, and emits machine-friendly telemetry for long-term operations.

## Objectives
1. Deliver a Typer CLI (`nh`) that becomes the single entrypoint for daily runs, maintenance, and publishing lifecycle commands.
2. Encode every prompt’s execution policy (model, tools, temperature, retries, timeout, concurrency class) in a registry that can evolve from TSV to a backing store without breaking consumers.
3. Manage context passing across waves with explicit manifests, dependency tracking, locking, and resumability that match current artifact layouts.
4. Provide reliable safety rails—idempotent reruns, --force targeting, dry-run previews, structured exit codes, and locking—so LaunchD + humans can trust automation.
5. Emit auditable telemetry: human-readable logs plus structured ledgers capturing configuration, lineage, durations, hashes, exit codes, and publish metadata.

## Scope
### In Scope
- Python 3.14.0-based orchestration package under `orchestrator/` with Typer CLI entrypoints (`nh run`, `nh cleanup`, etc.) powered by Typer 0.20.0 + Pydantic 2.12.4.
- Prompt registry loader/parsers, policy enforcement, and future-proofing for alternate storage (TSV now, SQLite later).
- Execution ledger, audit log, locking, resumable manifests, and publish/export handoff logic.
- LaunchD integration helpers, diagnostics, and parity tooling to compare Bash ↔ Python outputs on frozen dates.
- Unit/integration test harnesses and fixtures for registry, ledger, and limited Gemini CLI mock flows.

### Out of Scope
- Rewriting Gemini CLI itself or moving prompts into SDK calls.
- Redesigning Astro/Cloudflare publishing beyond triggering existing scripts and capturing metadata.
- Building a GUI or web dashboard for orchestration management.
- Expanding prompt content, search infrastructure, or analytics outside of what the Bash orchestrator already handles.

## Delivery Process & Tooling Baselines
- Toolchain versions verified on 2025-11-15: Python 3.14.0 (latest stable listed on python.org/downloads), Typer 0.20.0, Pydantic 2.12.4, uv 0.9.9, and Poetry 2.2.1 (per PyPI JSON metadata). All commands, lockfiles, and CI images must pin to these versions or document deltas.
- Implementation must follow strict test-driven development: write or update tests first so they fail, implement the minimal code to pass, and only then refactor. Every functional change needs corresponding automated tests in the same change set.
- Before modifying any files, engineers must create a dedicated feature branch (e.g., `feature/python-orchestrator`); all PRs and review artifacts originate from that branch to preserve a clean main history and simplify migration comparisons.

## CLI Experience Overview
- `nh run [--date YYYY-MM-DD] [--wave search|aggregator|...]` executes the canonical daily flow, reading prompt registry metadata to determine waves, concurrency, and dependencies.
- `nh cleanup`, `nh reprocess`, and `nh publish` expose existing maintenance behaviors but wrap them in Typer commands with consistent flags, confirmations, and logging.
- Automation commands (`nh automation install/status/remove`) manage LaunchD plists, validating environment prerequisites before mutating state.
- Operators can request dry runs (`--dry-run`) for any command; Typer surface ensures consistent help text, colorized summaries, and exit codes.

## Functional Requirements
1. **Pipeline Execution**
   - Support full daily runs plus scoped runs by date, wave, or prompt id; default date is “today” in repo timezone.
   - Each wave executes Gemini CLI invocations defined in the registry; outputs are written to the same directories (`data/outputs/daily/YYYY-MM-DD/` etc.) as the Bash flow.
   - Produce a per-run manifest summarizing executed prompts, dependencies, output paths, and content hashes; manifest stored under `data/manifests/YYYY-MM-DD.json`.
2. **Prompt Policy & Registry**
   - Load registry rows from `config/prompts.tsv` (v1) into typed models that record: prompt id, title, wave, model, safety settings, temperature, retries, timeout, max concurrency class, expected outputs.
   - Validate registry on startup; reject duplicates, missing policy fields, or unsupported combinations (e.g., incompatible tools with temperature > limit).
   - Provide adapters so the CLI can later read from SQLite without changing command flags; include CLI plumbing for `nh registry validate`.
3. **Context Passing & Artifact Management**
   - Later waves receive structured context objects referencing prior outputs (paths, metadata, hashes). Dependency graph stored in manifest.
   - Preserve existing filenames and directories unless requirements explicitly change them; add completion markers (`.nh_status.json`) alongside generated artifacts with duration, exit state, and hash.
   - Support `--force prompt-id` or `--force wave-name` which invalidates completion markers and reruns only selected scopes.
4. **Concurrency, Scheduling & Safety Rails**
   - Enforce single-run locking (e.g., `var/locks/nh-run.lock`); commands fail fast with actionable messaging if a run is active.
   - Obey per-wave concurrency caps from the registry; use bounded worker pools with retries/backoff for transient Gemini CLI failures.
   - Provide dry-run output summarizing planned actions, touched directories, and command counts without invoking Gemini CLI.
   - Normalize exit codes: `0` success, `10` config validation error, `20` dependency missing, `30` external tool failure, etc.
5. **Configuration Management**
   - Settings resolved via precedence: CLI flags > `.nh.toml` (per repo) > environment variables (e.g., `NH_DEFAULT_MODEL`).
   - Startup diagnostics verify required binaries (Gemini CLI, pnpm, wrangler), directory permissions, and environment secrets.
   - Secrets loaded from env or Keychain helpers; never logged.
6. **Observability & Telemetry**
   - Human-readable logs per run at `logs/runs/YYYY-MM-DD.log` with structured sections per wave, colorized summaries in TTY.
   - Machine ledger written as JSONL under `logs/ledger/YYYY-MM-DD.jsonl` capturing prompt id, parameters, timestamps, exit codes, hashes, retries, dependent inputs.
   - Audit log for maintenance commands (cleanup, reprocess, automation operations) stored under `logs/audit/YYYY-MM-DD.jsonl`.
7. **Publishing Handoff**
   - Export step emits the existing JSON payload consumed by the Astro site, plus metadata linking to manifest and ledger entries.
   - Optional `--publish` flag triggers the Cloudflare deploy wrapper defined in spec 004/005; command records deploy URL, status, duration in ledger.
   - Publish actions can also be invoked separately via `nh publish --date YYYY-MM-DD --source manifest.json`.

## Non-Functional Requirements
- **Reliability**: Recoverable retries with exponential backoff and resumable manifests; commands abort with descriptive errors when dependencies/locks fail.
- **Performance**: Orchestration overhead kept minimal—Gemini CLI invocations dominate runtime; concurrency per wave configurable via registry.
- **Security**: Secrets pulled from env/Keychain; no token logging; file permissions validated before writes.
- **Maintainability**: Modular services (registry, runner, ledger, automation) with docstrings, type hints, and tests; CLI help auto-generated via Typer 0.20.0.
- **Testability**: Enforce true TDD—every feature starts by adding failing tests (unit/integration) before production code; include fixtures for synthetic prompt registry and stub Gemini CLI command that records invocations; CI-ready unit/integration suites running on Python 3.14.0.
- **Usability**: Consistent flag naming, rich help text, colorized summaries, `--json` output mode for scripting.

## Solution Architecture
### Project Layout
```
neurohelix/
├── orchestrator/
│   ├── nh_cli/                # Typer app + command modules
│   ├── services/
│   │   ├── registry.py        # TSV/SQLite adapters & validation
│   │   ├── runner.py          # Wave scheduler + concurrency pools
│   │   ├── manifest.py        # Dependency graph + completion markers
│   │   ├── ledger.py          # Structured logging helpers
│   │   └── automation.py      # LaunchD plist install/status/remove
│   ├── config/
│   │   ├── prompts.tsv        # Source-of-truth registry (v1)
│   │   └── settings_schema.py # Pydantic models for CLI + config files
│   ├── adapters/
│   │   ├── gemini_cli.py      # Shell invocation + retries
│   │   └── filesystem.py      # Path utilities, hashing, locking
│   └── tests/
│       ├── fixtures/
│       └── integration/
├── data/outputs/daily/        # Existing artifacts (consumed/produced)
├── data/manifests/            # New manifests keyed by date
├── logs/                      # runs/, ledger/, audit/
└── scripts/launchd/           # Generated plist + install helper
```

### Execution Flow (Daily Run)
1. CLI parses flags, loads configuration, validates registry, and acquires lock.
2. Build run manifest by stitching registry rows into ordered waves, resolving dependencies to previous artifacts.
3. For each wave, spawn bounded worker pool executing Gemini CLI commands with context payloads assembled from manifest.
4. After each command, write completion marker + ledger entry with hashes, durations, parameters; on failure, retry as configured, otherwise halt with manifest update marking failed node.
5. After final wave, assemble aggregate report + export JSON exactly as Bash flow, then optionally invoke publish step.
6. Release lock, emit summary (success/failure table, durations, output locations), and exit with standardized code.

### Prompt Registry & Policy Format
- TSV columns: `prompt_id`, `title`, `wave`, `category`, `model`, `tools`, `temperature`, `token_budget`, `timeout_sec`, `max_retries`, `concurrency_class`, `expected_outputs`, `notes`.
- Registry validator enforces: 
  - unique `prompt_id`
  - contiguous wave ordering (search < aggregator < tagger < render < export < publish)
  - concurrency caps (e.g., aggregator prompts share pool size n)
- Adapter interface: `RegistryProvider.load()` returns Pydantic models; `TSVRegistryProvider` (default) and `SQLiteRegistryProvider` (future) implement same contract.

### Configuration & Secrets
- `.nh.toml` houses defaults (paths, concurrency overrides, telemetry toggles);
- Environment variables prefixed `NH_` override file defaults (e.g., `NH_DEFAULT_MODEL`).
- CLI flags override all; `nh diag` prints resolved config plus binary versions.
- Secrets (Gemini token, Cloudflare API token) referenced via env/Keychain; CLI validates presence before running commands that need them.

## Data & Persistence Contracts
- **Run Manifest (`data/manifests/YYYY-MM-DD.json`)**: captures run id, start/end timestamps, prompt dependency graph, forced reruns, completion markers, publish metadata.
- **Completion Marker (`*.nh_status.json`)**: stored beside each artifact with prompt id, started/ended timestamps, exit code, retries, sha256 of produced files.
- **Ledger (`logs/ledger/YYYY-MM-DD.jsonl`)**: append-only entries for every command + publish step.
- **Audit Log (`logs/audit/*.jsonl`)**: records maintenance commands with operator, CLI version, affected paths.
- **Lock File (`var/locks/nh-run.lock`)**: contains pid, command, timestamp; stale locks auto-expire with configurable TTL.

## CLI Surface (Initial Commands)

| Command | Description | Notes |
|---------|-------------|-------|
| `nh run [--date YYYY-MM-DD] [--wave ...] [--force ...] [--dry-run]` | Execute daily pipeline or scoped subset | Default date = today; `--json` emits summary payload |
| `nh reprocess --date YYYY-MM-DD [--force wave|prompt]` | Rebuild artifacts for a past day | Validates manifest, ensures safe partial reruns |
| `nh cleanup [--dry-run] [--keep-days N]` | Remove temporary files, stale locks, cache dirs | Audit logged with before/after stats |
| `nh publish --date YYYY-MM-DD [--skip-build]` | Trigger export + Cloudflare deploy | Writes deploy metadata to ledger |
| `nh automation install|status|remove [--plist /path]` | Manage LaunchD job | Confirms env prerequisites before mutation |
| `nh registry validate [--format tsv|sqlite]` | Lint registry definitions | Fails CI if schema mismatches |
| `nh diag [--json]` | Print diagnostics (binaries, env, permissions) | Used pre-flight + support |

## Automation & Scheduler Integration
- LaunchD plist generated under `scripts/launchd/neurohelix.orchestrator.plist`; Typer command installs/removes plist and ensures PATH + env variables exist.
- Automation status reports: last run timestamp (from ledger), next scheduled fire (from plist), lock status, queued reruns.
- Installation requires verifying `NH_REPO_ROOT`, `PNPM_HOME`, `GEMINI_CONFIG`, and secret availability; command aborts if validation fails.

## Safety Rails & Idempotency
- Lock enforcement prevents concurrent `nh run` or `nh reprocess`; maintenance commands check lock and require `--force` to proceed if a run is active.
- Dry-run preview lists commands, paths, concurrency, estimated duration; nothing is executed.
- Idempotent design: rerunning without `--force` respects completion markers; only missing or failed prompts execute.
- Partial reruns update manifest and ledger so downstream systems know which artifacts changed.

## Telemetry & Diagnostics
- Logging backend emits structured events (JSON) plus rich console output; log levels adjustable via flag/env.
- Execution ledger entries include: run id, prompt id, registry hash, config fingerprint, timestamps, duration, success flag, retries, sha256, dependent inputs, output paths.
- Diagnostics command verifies tool versions (`gemini --version`, `pnpm --version`, `python --version`), file permissions, disk space, environment variables, LaunchD job health.

## Migration & Acceptance
- Provide parity harness (`nh compare --date YYYY-MM-DD --bash-manifest path`) that diff-checks Bash vs. Python outputs (file presence + hash) for frozen dates.
- Document mapping of old scripts/flags to new commands in README & `docs/migration_python_orchestrator.md`.
- Acceptance requires: 
  - daily run reproduces directory tree + file hashes vs. Bash baseline;
  - ledger + audit logs include fields listed in requirements;
  - cleanup/reprocess/publish commands respected locking and produced audit entries;
  - LaunchD install/status/remove verified on macOS reference host.

## Testing Strategy
- **TDD workflow**: for each capability, write or extend the relevant failing test (unit/integration/golden) before implementation; the commit history must show tests landing with the feature they validate.
- **Unit tests** for registry parsing/validation, manifest builder, ledger writer, locking utilities, config resolution.
- **Integration tests** using stub Gemini CLI binary that records invocations and writes fixture artifacts; run small fixture registry to validate wave sequencing and idempotency.
- **Golden tests** for migration harness comparing Python outputs against stored Bash fixtures.
- **Smoke test command** `nh run --date fixture --dry-run` executed in CI to ensure CLI wiring and config defaults.

## Task Breakdown

| # | Task | Owner | Notes |
|---|------|-------|-------|
|0|Create a dedicated feature branch before touching files|All|Use a descriptive name (e.g., `feature/python-orchestrator`) so PRs cleanly diff from `main`|
|1|Scaffold Typer app, config resolution, and CLI surface|Python|Establish project layout + packaging under Python 3.14.0|
|2|Implement registry loader (TSV) + validation + adapters|Python|Pydantic 2.12.4 models + CLI `registry validate`|
|3|Build manifest + dependency graph + completion markers|Python|Backed by JSON + hashed outputs|
|4|Implement Gemini CLI adapter, concurrency pools, retries|Python|Bounded worker pools per wave|
|5|Develop ledger/audit logging + telemetry emitters|Python|JSONL writer + console summaries|
|6|Implement maintenance commands (cleanup, reprocess, publish)|Python|Wrap existing scripts with Typer 0.20.0 UX primitives|
|7|LaunchD automation helper + diagnostics|DevOps|Install/status/remove + env validation|
|8|Migration + parity harness + documentation|QA/Eng|Frozen-date comparison + runbook|
|9|Test suite + CI wiring|DevEx|Fixtures, stub CLI, lint/type checks run under uv 0.9.9 or Poetry 2.2.1|

## Decisions & Assumptions
1. Typer 0.20.0 + Pydantic 2.12.4 (latest PyPI releases as of 2025-11-15) are the foundational frameworks for CLI + config/registry modeling.
2. Gemini CLI remains the execution engine; orchestrator shells out via adapter with structured inputs/outputs.
3. Data layout (outputs, exports, logs) remains identical to Bash baseline; new manifests/markers live alongside but do not alter downstream contracts.
4. `pnpm` remains package manager for non-Python assets; orchestrator dependencies managed via `uv` 0.9.9 or `poetry` 2.2.1 (both verified against PyPI metadata on 2025-11-15) with lockfiles committed accordingly.

## Open Questions
- Final schema for registry categories and whether publish wave remains part of Typer command’s responsibility or split.
  - Answer: Publish wave remains part of `nh run` for simplicity; categories limited to existing six waves.
- Preferred storage backend for registry after TSV (SQLite vs. DuckDB) and migration timeframe.
  - Answer: SQLite is preferred for simplicity; migration planned as part of this conversion.
- Exact concurrency defaults and whether operators need CLI overrides beyond registry-defined caps.
  - Answer: CLI overrides will be supported for flexibility during testing and special runs.
- Required structure + retention for ledger/audit logs (rotation policy, redaction requirements).
  - Answer: Logs will be rotated monthly with a retention period of one year; no need to redact anything NeuroHelix does not process any sensitive data.
- How to detect + reconcile stale intermediates when reprocessing partial days (timestamps vs. hashes?).
  - Answer: Hash-based verification will be used to ensure data integrity during reprocessing.
- Whether diagnostics should verify large external data dependencies (search indices) in addition to binaries.
  - Answer: Diagnostics will focus on binaries and environment variables; external data dependencies will be validated during the run itself.
