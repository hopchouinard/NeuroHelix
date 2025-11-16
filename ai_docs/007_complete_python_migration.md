# Plan: Complete Migration to Python Orchestrator

## Overview
This plan captures the changes required to port remaining Bash-only features—git safety checks, Cloudflare cleanup context, and notifier hooks—into the Python CLI. Once implemented, daily automation can rely entirely on `nh` commands without invoking Bash orchestrator scripts.

## Goals
- Provide parity for destructive-operation safeguards (git clean verification).
- Include Cloudflare deployment context and optional rollback notes during Python cleanup.
- Integrate success/failure notifier scripts so operators receive identical alerts.
- Document configuration toggles and testing strategy to validate these new features.

## Workstreams

### 1. Git Safety Checks
1. **Reference behavior** – study `scripts/lib/git_safety.sh` to mirror logic (block dirty tree unless `--allow-dirty`).
2. **Create helper** – add `services/git_safety.py` exposing `ensure_clean_repo(allow_dirty: bool, logger)` built on `subprocess.run(["git", "status", "--porcelain"])`.
3. **CLI integration** – extend `nh cleanup` and `nh reprocess` with `--allow-dirty` flag. Invoke helper before deleting files; exit gracefully with detailed status when dirty.
4. **Console/JSON output** – print pending changes and update JSON mode to include a `git_clean` boolean.
5. **Tests** – use temporary git repos inside pytest to validate clean vs. dirty behavior, both with and without the flag.

### 2. Cloudflare Context for Cleanup
1. **Reference behavior** – review `scripts/lib/cloudflare.sh` usage during `--cleanup-all` runs.
2. **Cloudflare service** – introduce `services/cloudflare.py` with `get_latest_deployment_id(project, token)` and optional `rollback_to_empty` helper. Reuse `wrangler pages deployment list` or REST API via `requests` (respecting token env var).
3. **CLI changes** – update `nh cleanup` options to accept `--cloudflare-project` (default from config) and to read `CLOUDFLARE_API_TOKEN`. Before deletion, fetch latest deploy ID and print summary; after deletion, include ID in `AuditService.log_cleanup` metadata.
4. **Audit extension** – modify `AuditService.log_cleanup` to store `cloudflare_deploy_id` and `dry_run` info just like Bash.
5. **Tests** – mock subprocess calls to `wrangler` (or HTTP) to cover success/failure paths; ensure cleanup still works without token.

### 3. Notifier Hooks
1. **Inventory** – Bash pipeline calls `scripts/notifiers/notify_failures.sh` (on prompt failures) and `scripts/notifiers/notify.sh` (success) when env flags are true.
2. **Notifier service** – create `services/notifier.py` wrapping these scripts via `subprocess.run`, with methods `notify_failures(log_path, manifest)` and `notify_success(date, summary)`.
3. **Configuration** – extend `.nh.toml` schema with `[notifier] enable_success`, `enable_failure`, `failure_script`, `success_script`. Provide env overrides.
4. **Runner integration** – after `RunnerService` completes waves, if failures exist and failure notifications enabled, call notifier service (skip on `--dry-run`). After successful run and `ENABLE_NOTIFICATIONS` true, call success notifier using ledger stats.
5. **Tests** – mock `subprocess.run` to confirm correct scripts invoked, cover toggles, dry-run behavior, and missing-script warnings.

### 4. Documentation & Config Updates
1. Update `.nh.toml` sample and `config/settings_schema.py` with new options.
2. Document new flags in `README.md`, `docs/migration_python_orchestrator.md`, and command help text (`typer.Option` descriptions).
3. Highlight that LaunchD automation can now rely solely on `nh run` + `nh cleanup` once features land.

### 5. Validation Strategy
1. **Unit tests** – add pytest coverage for new services, config parsing, and CLI behavior.
2. **Integration tests** – run `nh cleanup --dry-run` and `nh reprocess` within CI to ensure git safety and Cloudflare logging operate.
3. **Parity checks** – execute `nh compare` against recent Bash runs to verify outputs remain aligned.
4. **Operational dry run** – trigger `nh run` with notifier flags in a staging environment to confirm alerts fire.

### 6. Rollout Steps
1. Implement git safety helper and CLI flags (least risky).
2. Add Cloudflare context + audit logging.
3. Wire notifier hooks into runner.
4. Update docs/config + add tests.
5. After validation, switch LaunchD automation to call `nh` commands only; deprecate Bash orchestrator scripts.
