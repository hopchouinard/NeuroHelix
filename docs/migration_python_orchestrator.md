># Migration Guide: Bash to Python Orchestrator

This document guides the migration from the Bash-based orchestrator to the Python-based Typer CLI orchestrator.

## Overview

The Python orchestrator (`nh` CLI) provides a robust, testable, and maintainable replacement for the Bash scripts while maintaining full compatibility with existing data structures and downstream consumers.

## Key Benefits

1. **Type Safety**: Pydantic models validate all configurations and data structures
2. **Better Error Handling**: Structured exceptions with detailed error messages
3. **Testability**: Comprehensive unit and integration test coverage
4. **Observability**: Structured logging with JSONL ledgers
5. **Maintainability**: Modular services with clear responsibilities
6. **Concurrency**: ThreadPoolExecutor with configurable pool sizes
7. **Retry Logic**: Exponential backoff with configurable retries
8. **Locking**: TTL-based file locking prevents concurrent runs
9. **Idempotency**: Hash-verified completion markers

## Command Mapping

### Bash → Python Equivalents

| Bash Command | Python Command | Notes |
|--------------|----------------|-------|
| `./scripts/orchestrator.sh` | `nh run` | Full daily pipeline |
| `./scripts/executors/run_prompts.sh` | `nh run --wave search` | Search wave only |
| `./scripts/aggregators/aggregate_daily.sh` | `nh run --wave aggregator` | Aggregation only |
| Manual rerun | `nh run --force prompt_id` | Force specific prompt |
| Manual date | `./scripts/orchestrator.sh` with env | `nh run --date 2025-11-14` | Explicit date |
| `./install_automation.sh` | `nh automation install` | LaunchD setup |
| `launchctl list \| grep neurohelix` | `nh automation status` | Check automation |
| Manual cleanup | `nh cleanup` | Structured cleanup |
| N/A | `nh diag` | System diagnostics |
| N/A | `nh registry validate` | Registry validation |

### Flags & Options

| Bash Pattern | Python Equivalent |
|--------------|-------------------|
| `PARALLEL_EXECUTION=true` | Handled automatically via `concurrency_class` in registry |
| `MAX_PARALLEL_JOBS=4` | Configured in `.nh.toml` or registry |
| Script exit codes | Standardized exit codes (0, 10, 20, 30) |
| Manual dry-run | `--dry-run` flag on all commands |

## Data Structure Compatibility

### Directory Layout

Both implementations use identical layouts:

```
data/
├── outputs/daily/YYYY-MM-DD/     # Search outputs
├── reports/                       # Aggregated reports
├── publishing/                    # Export JSONs
└── manifests/                     # NEW: Run manifests

logs/
├── runs/                          # NEW: Human-readable logs
├── ledger/                        # NEW: Structured JSONL
└── audit/                         # NEW: Maintenance audit

var/locks/                         # NEW: Lock files
```

### File Naming

- Outputs: `data/outputs/daily/YYYY-MM-DD/{prompt_id}.md`
- Reports: `data/reports/daily_report_YYYY-MM-DD.md`
- Tags: `data/publishing/tags_YYYY-MM-DD.json`
- Exports: `data/publishing/YYYY-MM-DD.json`
- Dashboards: `dashboards/dashboard_YYYY-MM-DD.html`

**No changes required** - Python orchestrator maintains compatibility.

### New Artifacts

Python orchestrator adds:

1. **Run Manifest** (`data/manifests/YYYY-MM-DD.json`)
   - Tracks execution metadata
   - Lists completed/failed prompts
   - Records forced reruns
   - Includes publish metadata

2. **Completion Markers** (`.nh_status_{name}.json`)
   - Stored alongside outputs
   - Contains hash, exit code, retries
   - Enables idempotent reruns

3. **Ledger** (`logs/ledger/YYYY-MM-DD.jsonl`)
   - One entry per prompt execution
   - Structured telemetry
   - Includes config fingerprints

4. **Audit Log** (`logs/audit/YYYY-MM-DD.jsonl`)
   - Maintenance operations
   - User and command tracking

## Configuration Migration

### Old: `config/env.sh`

```bash
GEMINI_MODEL="gemini-2.5-pro"
PARALLEL_EXECUTION="true"
MAX_PARALLEL_JOBS="4"
```

### New: `.nh.toml` + Registry

```toml
[settings]
default_model = "gemini-2.5-pro"
max_parallel_jobs = 4
```

Plus per-prompt configuration in `orchestrator/config/prompts.tsv`:

```tsv
prompt_id	concurrency_class	model	temperature
ai_watch	high	gemini-2.5-pro	0.7
```

### Registry Migration

The old `config/searches.tsv` format:

```tsv
domain	category	prompt	priority	enabled
AI Watch	Research	[prompt text]	high	true
```

Maps to new `orchestrator/config/prompts.tsv`:

```tsv
prompt_id	title	wave	category	model	temperature	timeout_sec	max_retries	concurrency_class	expected_outputs	notes
ai_watch	AI Watch	search	Research	gemini-2.5-pro	0.7	120	3	high	ai_watch.md	Tracks announcements
```

**Migration script** (TODO):
```bash
# Convert old searches.tsv to new prompts.tsv format
python scripts/migrate_registry.py
```

## Step-by-Step Migration

### Phase 1: Parallel Operation (Current)

1. **Install Python orchestrator**
   ```bash
   cd orchestrator
   poetry install
   nh diag  # Verify setup
   ```

2. **Validate registry**
   ```bash
   nh registry validate
   ```

3. **Test dry-run**
   ```bash
   nh run --dry-run
   ```

4. **Run in parallel with Bash**
   - Keep Bash automation active
   - Run Python manually for testing
   - Compare outputs using parity harness

### Phase 2: Parity Testing

1. **Freeze a test date**
   ```bash
   TEST_DATE="2025-11-14"

   # Run Bash version
   ./scripts/orchestrator.sh  # Captures in data/outputs/daily/$TEST_DATE

   # Run Python version
   nh run --date $TEST_DATE --force
   ```

2. **Compare outputs** (TODO: parity harness)
   ```bash
   nh compare --date $TEST_DATE --bash-artifacts data/outputs/daily/$TEST_DATE
   ```

3. **Verify:**
   - All files present
   - File hashes match
   - Manifest includes all prompts
   - Ledger captures all executions

### Phase 3: Switchover

1. **Disable Bash automation**
   ```bash
   ./uninstall_automation.sh
   ```

2. **Install Python automation**
   ```bash
   nh automation install
   ```

3. **Verify automation**
   ```bash
   nh automation status
   launchctl list | grep neurohelix
   ```

4. **Monitor first automated run**
   ```bash
   tail -f logs/runs/$(date +%Y-%m-%d).log
   ```

### Phase 4: Cleanup

1. **Archive Bash scripts**
   ```bash
   mkdir scripts/archived_bash
   mv scripts/{orchestrator,executors,aggregators}.sh scripts/archived_bash/
   ```

2. **Update documentation**
   - Update CLAUDE.md references
   - Update README.md
   - Archive old runbooks

3. **Remove legacy config**
   ```bash
   mv config/env.sh config/env.sh.archived
   mv config/searches.tsv config/searches.tsv.archived
   ```

## Rollback Plan

If issues arise, rollback is simple:

```bash
# Stop Python automation
nh automation remove

# Reinstall Bash automation
./install_automation.sh

# Revert to Bash for manual runs
./scripts/orchestrator.sh
```

Python artifacts don't interfere with Bash, so rollback is non-destructive.

## Testing Strategy

### Unit Tests

```bash
cd orchestrator
poetry run pytest tests/unit/
```

Tests cover:
- Registry loading and validation
- Manifest creation and persistence
- Ledger writing and reading
- Filesystem utilities (locking, hashing)

### Integration Tests

```bash
poetry run pytest tests/integration/
```

Uses stub Gemini CLI to validate:
- Wave sequencing
- Dependency resolution
- Retry logic
- Completion marker behavior

### Parity Tests

```bash
# Run both orchestrators on frozen date
./scripts/run_parity_test.sh 2025-11-14

# Compare outputs
nh compare --date 2025-11-14
```

Validates file-by-file hash matches.

## Common Issues

### Lock Conflicts

**Symptom**: `Lock already held` error

**Solution**:
```bash
# Check lock file
cat var/locks/nh-run.lock

# If stale (older than TTL):
rm var/locks/nh-run.lock

# Or use diagnostics
nh diag
```

### Registry Validation Failures

**Symptom**: Registry validation errors on startup

**Solution**:
```bash
# Run validation explicitly
nh registry validate

# Check for:
# - Duplicate prompt_id
# - Missing required columns
# - Invalid wave names
# - Temperature > 1.0 with tools
```

### Missing Dependencies

**Symptom**: `gemini` or `pnpm` not found

**Solution**:
```bash
# Check diagnostics
nh diag

# Install missing tools
brew install pnpm
# Install Gemini CLI from Google
```

### Output Path Mismatches

**Symptom**: Outputs not appearing in expected locations

**Solution**:
- Verify `expected_outputs` in registry
- Check wave type (determines base directory)
- Ensure date format is YYYY-MM-DD

## Performance Comparison

| Metric | Bash | Python | Notes |
|--------|------|--------|-------|
| Startup overhead | ~50ms | ~200ms | Python import time |
| Prompt execution | N/A | N/A | Dominated by Gemini CLI |
| Concurrency | `parallel` | ThreadPoolExecutor | Similar performance |
| Idempotency check | None | ~10ms/prompt | Hash verification |
| Telemetry write | ~1ms | ~5ms | Structured JSONL |

**Net impact**: <1% overhead for significantly better reliability.

## Future Enhancements

Once migration is complete:

1. **SQLite Registry** - Replace TSV with database
2. **Web Dashboard** - Real-time monitoring
3. **Slack Notifications** - Failure alerts
4. **Advanced Scheduling** - Conditional wave execution
5. **Distributed Execution** - Run waves on separate machines
6. **A/B Testing** - Compare prompt variations

## Support

- **Documentation**: `orchestrator/README.md`
- **Diagnostics**: `nh diag`
- **Validation**: `nh registry validate`
- **Logs**: `logs/runs/YYYY-MM-DD.log`
- **GitHub Issues**: Report migration blockers

## Timeline

| Phase | Duration | Status |
|-------|----------|--------|
| Initial Implementation | 2 weeks | ✅ Complete |
| Testing & Parity | 1 week | 🔄 In Progress |
| Parallel Operation | 1 week | ⏳ Pending |
| Switchover | 1 day | ⏳ Pending |
| Monitoring | 1 week | ⏳ Pending |
| Cleanup | 1 day | ⏳ Pending |

**Target completion**: 2025-12-01
