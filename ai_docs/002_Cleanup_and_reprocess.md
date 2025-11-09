# Cleanup & Reprocess Controls

## Background
The daily NeuroHelix run accumulates generated artifacts (prompt outputs, reports, dashboards, runtime ledgers, logs, search indexes, Cloudflare deploys). When experimentation, prompt tweaks, or failures leave the workspace in an inconsistent state, we currently have no single command to wipe the slate clean or to force the current day to re-run end-to-end. Manual deletion is error-prone and risks removing configuration scaffolding. Likewise, re-triggering the entire pipeline for “today” requires stringing together multiple scripts and does not stamp the resulting data as a manual override. We need first-class orchestration flags that let an operator at the terminal perform these maintenance tasks safely and predictably.

## Goals
1. Provide a `scripts/orchestrator.sh` flag that performs a full cleanup of all generated content, retracts the latest Cloudflare Pages deploy, and leaves the repo ready for a fresh run.
2. Provide a second flag that forcefully reprocesses the current day (system local time) by deleting today’s outputs/logs, rerunning the entire 6-step pipeline, redeploying the site, and resending notifications.
3. Ensure both flows are interactive, auditable, and idempotent, with dry-run previews, git safety checks, and explicit ledger entries identifying manual overrides.

## Operator & Invocation
- **Operator**: Human maintainer at the terminal; automation (LaunchD) must not invoke these flags.
- **Entry points**: Extend `scripts/orchestrator.sh` with two mutually exclusive flags:
  - `--cleanup-all` (alias `--reset-workspace`): performs the full purge.
  - `--reprocess-today` (alias `--force-today`): forces today’s pipeline.
- **Mutual exclusion**: If either flag is present, skip the normal scheduled run logic. Reject combined usage.
- **Dry-run preview**: `--dry-run` optional sub-flag for both modes to print the plan (paths, remote actions) without executing.
- **Interactive confirmation**: Require a `y/N` prompt unless `--yes` is supplied. Confirmation text must restate the action (cleanup vs reprocess) and the impact.

## Cleanup Mode
1. **Scope of deletion** (local filesystem):
   - Remove generated artifacts under: `data/outputs/daily/`, `data/reports/`, `data/publishing/`, `dashboards/`, `logs/`, `data/runtime/`, `site/public/search-index.json`, and cached build outputs under `site/scripts/` if any exist.
   - Preserve configs, templates, launchd files, manual notes, `config/`, `data/config/`, `ai_docs/`, `site/src/`, and any git-tracked scaffolding.
2. **Remote retract**:
   - After local deletion succeeds, call a helper (new or existing) that retracts the most recent Cloudflare Pages deployment via the Pages REST API: first `GET /accounts/:account_id/pages/projects/:project/deployments?per_page=1&status=success` to fetch the most recent successful deploy ID, then `DELETE /accounts/:account_id/pages/projects/:project/deployments/:deployment_id` to retract it. Capture both request and response payloads (deploy ID, status, errors) for the audit log.
3. **Git safety**:
   - Before modifying files, ensure `git status --porcelain` is clean *or* explicitly confirm the operator wants to continue if uncommitted changes exist. The default should be to abort unless `--allow-dirty` is supplied.
4. **Idempotency**:
   - Missing directories/files should not throw errors; report “already clean” and continue.
5. **Ledger/audit**:
   - Write an entry to `logs/maintenance/cleanup_YYYY-MM-DDTHHMMSS.log` (new directory if needed) and append a JSON record to `data/runtime/audit.jsonl` with fields: `action=cleanup_all`, `operator`, `timestamp`, `dry_run`, `git_status`, `target_paths`, `cloudflare_deploy_id`.
6. **Backup policy**:
   - No automatic snapshot/tarball is taken before cleanup; outright deletion is acceptable for now. Document how to re-run the daily pipeline manually once cleanup finishes.
7. **Exit codes**:
   - Non-zero exit if any deletion or Cloudflare retract fails; partial work must be summarized so the operator can manually finish.
8. **Post-cleanup flow**:
   - Cleanup does not automatically trigger a fresh pipeline run. Operators are expected to launch `./scripts/orchestrator.sh` manually when they are satisfied with the clean state.

## Force Reprocess Mode
1. **Pre-flight checks**:
   - Ensure no pipeline run is currently active by inspecting the existing lock/marker (if none exists, create one). If active, inform the operator and exit unless `--allow-abort` is passed; that flag should terminate the running process gracefully before proceeding.
   - Validate today’s date using system local timezone.
2. **State reset for today**:
   - Delete today’s subdirectories/files across `data/outputs/daily/<today>/`, `data/reports/daily_report_<today>.md`, `data/publishing/<today>.json`, `dashboards/dashboard_<today>.html`, `logs/*<today>*`, and any runtime ledgers tagged with today. Never touch previous days.
3. **Manual override tagging**:
   - Inject a `RUN_MODE=manual_override` (or similar) env var for the upcoming orchestrator run so downstream logs, ledgers, and report metadata can annotate that the run was forced.
   - Add a `manual_override=true` flag inside the runtime ledger JSON, and include the operator name (from `$USER`) plus reason string “force reprocess”.
4. **Pipeline execution**:
   - After cleanup, invoke the standard 6-step pipeline (same as default orchestrator path) so that prompts, aggregation, tag extraction, rendering, JSON export, and publishing all occur.
   - Ensure notification emails and Cloudflare deploys fire as usual; duplicate sends are acceptable and intentional.
5. **Post-run logging**:
   - Append a dedicated entry to `logs/maintenance/reprocess_YYYY-MM-DDTHHMMSS.log` capturing status of each of the 6 steps, the new deploy ID, and notification status.
   - Update `data/runtime/audit.jsonl` with `action=reprocess_today`, `date`, `manual_override=true`, `lock_behavior` (blocked, aborted, or clean), and pipeline duration.
6. **Idempotency**:
   - Multiple force runs in one day should succeed; each invocation deletes and recreates that day’s assets, producing a monotonic sequence of audit entries.

## LaunchD & Concurrency
- Cleanup and force-reprocess flags must be guarded so LaunchD never calls them via scheduled jobs. Document that they are operator-only.
- Respect the existing orchestrator lock file to prevent concurrent runs. Provide clear CLI output when blocking.
- When `--allow-abort` is used, implement a safe shutdown that signals the running process, waits for confirmation, then proceeds with reprocess. Surface this interaction in the audit log (`lock_behavior=aborted` vs `blocked`).

## User Experience & Messaging
- All destructive actions should be preceded by:
  1. Dry-run table summarizing directories/files to remove and whether Cloudflare retract/publish will occur.
  2. Explicit confirmation prompt (default `No`) unless `--yes`.
  3. Clear CLI logging with emoji or prefixes similar to existing orchestrator output for consistency.
- After successful cleanup or reprocess, print next-step guidance (e.g., “Run ./scripts/orchestrator.sh normally to generate a new report”).

## Testing & Validation
- Provide helper targets or documentation for how to simulate both flows in a safe environment.
- Include unit-style tests or shell-script smoke tests (if feasible) that mock filesystem and Cloudflare API calls to verify dry-run, idempotency, and audit logging logic.
- Make automated tests a release gate: new cleanup and reprocess paths must land with corresponding test coverage and the orchestrator CI must execute those tests on every run, preventing untested maintenance flags from shipping.

## Acceptance Criteria
1. Running `scripts/orchestrator.sh --cleanup-all --dry-run` prints the exact set of paths and Cloudflare deploy slated for removal without modifying files; `--yes` executes the purge, retracts the latest deploy, and logs the action locally and in `audit.jsonl`.
2. Running `scripts/orchestrator.sh --reprocess-today` while no other run is active deletes only today’s artifacts, reruns all six pipeline stages, redeploys the site, resends notifications, and annotates every log/ledger/report with `manual_override=true`.
3. Attempting to force reprocess during an active run blocks with a clear message and exits unless `--allow-abort` is supplied, in which case the running job is safely stopped and replaced; all behaviors are recorded in maintenance logs.
4. Both flows refuse to proceed when the git working tree is dirty unless the operator passes `--allow-dirty`; confirmations and dry-run previews are enforced by default.
5. All actions append structured entries to both `logs/maintenance/*.log` and `data/runtime/audit.jsonl`, providing a durable audit trail of who ran what, when, and with which parameters.

## Open Questions

None; Cloudflare retract method, backup handling, and post-cleanup behavior are now fully specified above.
