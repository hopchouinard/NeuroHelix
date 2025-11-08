# NeuroHelix Telemetry & Failure Handling - Testing Guide

**Implementation Date:** November 8, 2025  
**Specification:** `ai_docs/001_prompt_pipeline_improvement.md`  
**Status:** ✅ Implementation Complete - Ready for Testing

## Implementation Summary

All requirements from the specification have been successfully implemented:

✅ **Logging & Telemetry**
- Daily telemetry logs at `logs/prompt_execution_YYYY-MM-DD.log`
- JSON execution ledgers at `data/runtime/execution_ledger_YYYY-MM-DD.json`
- ISO8601 timestamps with duration tracking
- Structured logging with best-effort error handling

✅ **Daily Report Integration**
- Prompt Execution Summary section in daily reports
- Statistics table with total, successful, failed counts
- Detailed execution table with status, duration, timestamps
- Failed prompt details with error messages

✅ **Failure Handling & Notifications**
- Non-blocking failures with `|| true` pattern
- Parallel execution isolation
- Batched email notifications to `chouinpa@gmail.com`
- Retry logic (3 attempts, 5-second delays)
- Comprehensive troubleshooting guidance in emails

## Testing Checklist

### 1. Unit Testing (Telemetry Library)

**Test Script:** `./tests/test_telemetry.sh`

**What it validates:**
- ✅ Log file creation and structure
- ✅ ISO8601 timestamp formatting (macOS BSD date compatible)
- ✅ JSON ledger initialization and schema
- ✅ Duration calculation accuracy
- ✅ Summary statistics generation
- ✅ Multiple prompt tracking
- ✅ JSON parseability (python3/jq validation)

**Run command:**
```bash
cd /Users/pchouinard/Dev/NeuroHelix
./tests/test_telemetry.sh
```

**Expected outcome:** All 14 tests pass

---

### 2. Integration Testing (Failure Handling)

**Test Script:** `./tests/test_prompt_failure.sh`

**What it validates:**
- ✅ Non-blocking execution continues despite failures
- ✅ Telemetry logging captures failure details
- ✅ JSON ledger tracks failed prompts correctly
- ✅ All prompts execute (no early abort)
- ✅ Output files created for all prompts
- ✅ Notification system detects failures
- ✅ Completion marker set even with failures

**Run command:**
```bash
cd /Users/pchouinard/Dev/NeuroHelix
./tests/test_prompt_failure.sh
```

**Expected outcome:** All 8 tests pass  
**Note:** This test uses mock prompts with intentional failures

---

### 3. Full Pipeline Test (Happy Path)

**Objective:** Verify telemetry works with actual prompts

**Steps:**
```bash
# 1. Ensure telemetry is enabled (should be by default)
grep ENABLE_FAILURE_NOTIFICATIONS config/env.sh
# Should show: export ENABLE_FAILURE_NOTIFICATIONS="true"

# 2. Clean any existing state for today
rm -f data/outputs/daily/$(date +%Y-%m-%d)/.execution_complete
rm -f logs/prompt_execution_$(date +%Y-%m-%d).log
rm -f data/runtime/execution_ledger_$(date +%Y-%m-%d).json

# 3. Run the orchestrator
./scripts/orchestrator.sh
```

**Validation steps:**
```bash
# Verify telemetry log exists
ls -lh logs/prompt_execution_$(date +%Y-%m-%d).log

# Check log contains START and END entries
grep "START" logs/prompt_execution_$(date +%Y-%m-%d).log | wc -l
grep "END" logs/prompt_execution_$(date +%Y-%m-%d).log | wc -l

# Verify JSON ledger is valid
python3 -c "import json; json.load(open('data/runtime/execution_ledger_$(date +%Y-%m-%d).json'))"

# Check ledger summary
grep -A 5 '"summary"' data/runtime/execution_ledger_$(date +%Y-%m-%d).json

# Verify report contains execution summary
grep "Prompt Execution Summary" data/reports/daily_report_$(date +%Y-%m-%d).md
```

**Expected outcomes:**
- ✅ Telemetry log contains entries for all prompts
- ✅ JSON ledger is valid and parseable
- ✅ Summary statistics match actual execution count
- ✅ Daily report includes execution summary section
- ✅ No failures detected (no email sent)

---

### 4. Failure Scenario Test

**Objective:** Verify failure handling and email notifications

**Steps:**
```bash
# 1. Backup current searches.tsv
cp config/searches.tsv config/searches.tsv.backup

# 2. Add a failing prompt to searches.tsv
echo -e "Test Failure\tResearch\tTHIS_WILL_FAIL_INTENTIONALLY_XYZ\thigh\ttrue" >> config/searches.tsv

# 3. Clean execution state
rm -f data/outputs/daily/$(date +%Y-%m-%d)/.execution_complete
rm -f logs/prompt_execution_$(date +%Y-%m-%d).log
rm -f data/runtime/execution_ledger_$(date +%Y-%m-%d).json

# 4. Run orchestrator
./scripts/orchestrator.sh
```

**Validation steps:**
```bash
# Check for failure in telemetry log
grep "failure" logs/prompt_execution_$(date +%Y-%m-%d).log

# Verify ledger shows at least 1 failure
grep '"failed":' data/runtime/execution_ledger_$(date +%Y-%m-%d).json

# Check if notification was sent (look at mail logs or check inbox)
# Check orchestrator log for notification step
grep "Step 2.75" logs/orchestrator_*.log | tail -5

# Verify pipeline completed despite failure
ls -lh data/outputs/daily/$(date +%Y-%m-%d)/.execution_complete
```

**Cleanup:**
```bash
# Restore original searches.tsv
mv config/searches.tsv.backup config/searches.tsv
```

**Expected outcomes:**
- ✅ Pipeline completes despite failing prompt
- ✅ Failure is logged in telemetry log with error message
- ✅ JSON ledger shows `"failed": 1` or more
- ✅ Email notification sent to chouinpa@gmail.com
- ✅ Email contains failure details and troubleshooting steps
- ✅ Daily report shows failed prompt with ❌ indicator

---

### 5. Idempotency Test with Failures

**Objective:** Verify re-execution behavior

**Steps:**
```bash
# 1. After running with a failure (from Test 4):
# Check completion marker
cat data/outputs/daily/$(date +%Y-%m-%d)/.execution_complete

# 2. Re-run orchestrator without changes
./scripts/orchestrator.sh
```

**Expected outcomes:**
- ✅ Script detects completion marker
- ✅ Skips prompt execution stage
- ✅ Completes in < 1 second
- ✅ No duplicate telemetry entries

---

### 6. Parallel Execution Test

**Objective:** Verify failure isolation in parallel mode

**Steps:**
```bash
# 1. Verify parallel execution is enabled
grep PARALLEL_EXECUTION config/env.sh
# Should show: export PARALLEL_EXECUTION="true"

# 2. Check parallel jobs limit
grep MAX_PARALLEL_JOBS config/env.sh
# Should show: export MAX_PARALLEL_JOBS="4"

# 3. Run test with multiple failures (from test_prompt_failure.sh)
./tests/test_prompt_failure.sh
```

**Expected outcomes:**
- ✅ Multiple prompts execute in parallel
- ✅ One failure doesn't block other parallel jobs
- ✅ All prompts complete regardless of failures
- ✅ Telemetry captures timing for parallel execution

---

### 7. Dashboard Rendering Test

**Objective:** Ensure dashboards still render correctly with new report section

**Steps:**
```bash
# After running orchestrator with telemetry:
./scripts/renderers/generate_dashboard.sh

# Open the dashboard
open dashboards/latest.html
```

**Expected outcomes:**
- ✅ Dashboard renders without errors
- ✅ Execution summary section is visible in HTML
- ✅ Failed prompts (if any) are highlighted
- ✅ All formatting and links work correctly

---

### 8. Email Notification Test

**Objective:** Verify actual email delivery

**Prerequisites:**
- `mail` command must be configured on macOS
- Mail.app should have an active account configured

**Steps:**
```bash
# 1. Test mail command directly
echo "Test email body" | mail -s "NeuroHelix Test" chouinpa@gmail.com

# 2. Check if email was received (check inbox)

# 3. Run orchestrator with a failure (Test 4)
# and verify failure notification email arrives
```

**Expected outcomes:**
- ✅ Test email is delivered successfully
- ✅ Failure notification email arrives at chouinpa@gmail.com
- ✅ Email contains all required sections:
  - Failure summary table
  - Error details
  - Telemetry log links
  - Rerun instructions
  - Troubleshooting guidance

**If email fails:**
- Check Mail.app configuration
- Verify System Preferences → Internet Accounts
- Try alternative: `mailx` command
- Review logs: `tail -f logs/orchestrator_*.log`

---

## Known Issues & Limitations

### macOS Date Command
- Uses BSD date format (`date -j -f`)
- ISO8601 parsing may fail on some timestamp formats
- Fallback logic implemented for compatibility

### JSON Ledger Manipulation
- Uses sed/awk for JSON manipulation (not jq dependency)
- Complex but portable across systems
- Edge case: Very long error messages may need truncation

### Email Delivery
- Depends on system `mail` command
- May require Mail.app configuration on macOS
- Non-fatal: pipeline continues if email fails

---

## Acceptance Criteria Validation

From specification document `001_prompt_pipeline_improvement.md`:

### ✅ Criterion 1: Daily Log Files
> `logs/prompt_execution_YYYY-MM-DD.log` contains well-formed entries for each prompt with start/end timestamps and status.

**Validation:** Run `./tests/test_telemetry.sh` - Tests 1, 4, 5, 6, 12

### ✅ Criterion 2: Report Summary
> The daily report ends with a Prompt Execution Summary table/list showing every prompt and its success/failure state.

**Validation:** Check any generated daily report for "## Prompt Execution Summary" section

### ✅ Criterion 3: Failure Handling & Notification
> If a prompt fails, the orchestrator still completes all other prompts, marks the failure in the summary, and an email reaches `chouinpa@gmail.com` with the logged error details.

**Validation:** Run `./tests/test_prompt_failure.sh` - Tests 1, 3, 5, 6, 8

---

## Rollback Procedure

If issues are found and rollback is needed:

```bash
# 1. Disable failure notifications
sed -i.bak 's/ENABLE_FAILURE_NOTIFICATIONS="true"/ENABLE_FAILURE_NOTIFICATIONS="false"/' config/env.sh

# 2. Restore original run_prompts.sh from git
git checkout scripts/executors/run_prompts.sh

# 3. Remove telemetry library
rm scripts/lib/telemetry.sh

# 4. Restore original aggregate_daily.sh
git checkout scripts/aggregators/aggregate_daily.sh

# 5. Restore original orchestrator.sh
git checkout scripts/orchestrator.sh
```

**Note:** Rollback removes telemetry features but system remains functional.

---

## Performance Impact

**Expected performance changes:**
- Telemetry logging adds ~50-100ms per prompt
- JSON ledger manipulation adds ~10-20ms per prompt
- Total overhead: < 5% for typical 20-prompt execution
- No impact on idempotent re-runs

**Monitoring:**
```bash
# Compare execution times
grep "Total duration" logs/prompt_execution_$(date +%Y-%m-%d).log
```

---

## Next Steps

After validation:

1. **Monitor production runs** for 3-7 days
2. **Review email notifications** for false positives
3. **Analyze telemetry data** for insights
4. **Tune timeout values** if needed
5. **Document common failure patterns**

---

## Support & Troubleshooting

**Documentation:**
- Full troubleshooting guide: `WARP.md` (sections: Telemetry & Monitoring, Failure Handling, Troubleshooting)
- Telemetry library: `scripts/lib/telemetry.sh`
- Notification script: `scripts/notifiers/notify_failures.sh`

**Test Scripts:**
- Unit tests: `./tests/test_telemetry.sh`
- Integration tests: `./tests/test_prompt_failure.sh`

**Contact:**
- Email notifications: chouinpa@gmail.com
- Configuration: `config/env.sh`

---

## Implementation Files

**New Files Created:**
- `scripts/lib/telemetry.sh` - Telemetry logging library
- `scripts/notifiers/notify_failures.sh` - Failure notification system
- `tests/test_telemetry.sh` - Telemetry unit tests
- `tests/test_prompt_failure.sh` - Failure handling integration tests
- `data/runtime/` - Directory for execution ledgers
- `IMPLEMENTATION_TESTING.md` - This document

**Modified Files:**
- `scripts/executors/run_prompts.sh` - Added telemetry tracking and failure isolation
- `scripts/aggregators/aggregate_daily.sh` - Added execution summary generation
- `scripts/orchestrator.sh` - Added failure notification step (Step 2.75)
- `config/env.sh` - Added telemetry and notification configuration
- `WARP.md` - Added comprehensive documentation

**Total Lines of Code Added:** ~1,200 lines
**Total Files Changed:** 9 files

---

**Implementation Status: ✅ COMPLETE**  
**Testing Status: ⏳ PENDING USER VALIDATION**  
**Production Ready: ⚠️  PENDING TESTING**
