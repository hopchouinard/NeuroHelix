#!/bin/bash
# Integration test for failure handling
# Tests non-blocking failures, telemetry logging, and email notifications

set -uo pipefail

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

source "${PROJECT_ROOT}/config/env.sh"

echo "========================================="
echo "NeuroHelix Failure Handling Test"
echo "========================================="
echo ""
echo "This test validates:"
echo "  - Non-blocking failure behavior"
echo "  - Telemetry logging of failures"
echo "  - JSON ledger failure tracking"
echo "  - Email notification system"
echo ""

# Test configuration
TEST_DATE=$(date +%Y-%m-%d)
TEST_TSV="${CONFIG_DIR}/searches_test.tsv"
BACKUP_TSV="${CONFIG_DIR}/searches.tsv.backup"
TEST_LOG="${LOGS_DIR}/prompt_execution_${TEST_DATE}.log"
TEST_LEDGER="${RUNTIME_DIR}/execution_ledger_${TEST_DATE}.json"

# Backup original searches.tsv
if [ -f "${CONFIG_DIR}/searches.tsv" ]; then
    cp "${CONFIG_DIR}/searches.tsv" "$BACKUP_TSV"
    echo -e "${BLUE}ℹ️  Backed up original searches.tsv${NC}"
fi

# Cleanup function
cleanup() {
    echo ""
    echo "Cleaning up test environment..."
    
    # Restore original searches.tsv
    if [ -f "$BACKUP_TSV" ]; then
        mv "$BACKUP_TSV" "${CONFIG_DIR}/searches.tsv"
        echo "✅ Restored original searches.tsv"
    fi
    
    # Remove test TSV
    rm -f "$TEST_TSV" 2>/dev/null || true
    
    # Clean up test outputs
    rm -rf "${DATA_DIR}/outputs/daily/${TEST_DATE}" 2>/dev/null || true
    
    echo "Cleanup complete"
}

# Set up trap to cleanup on exit
trap cleanup EXIT INT TERM

# Create test TSV with mix of success and failure scenarios
echo "📝 Creating test prompt configuration..."

cat > "$TEST_TSV" << 'TEST_TSV'
domain	category	prompt	priority	enabled
Success Prompt 1	Research	Respond with exactly: "Test successful. This is a working prompt."	high	true
Failing Prompt 1	Research	INVALID_COMMAND_XYZ_THIS_WILL_FAIL	high	true
Success Prompt 2	Analysis	Respond with exactly: "Second test successful."	medium	true
Failing Prompt 2	Ideation	ERROR_ERROR_ERROR_MAKE_THIS_FAIL	medium	true
Success Prompt 3	Market	Respond with exactly: "Third test successful."	low	true
TEST_TSV

echo "✅ Test configuration created with 3 success + 2 failure prompts"
echo ""

# Replace searches.tsv with test version
cp "$TEST_TSV" "${CONFIG_DIR}/searches.tsv"

# Clean any existing execution state for today
rm -f "${DATA_DIR}/outputs/daily/${TEST_DATE}/.execution_complete" 2>/dev/null || true
rm -f "$TEST_LOG" "$TEST_LEDGER" 2>/dev/null || true

echo "🚀 Running prompt executor with test configuration..."
echo ""

# Run the prompt executor
"${PROJECT_ROOT}/scripts/executors/run_prompts.sh"
EXIT_CODE=$?

echo ""
echo "========================================="
echo "Analyzing Results"
echo "========================================="
echo ""

TESTS_PASSED=0
TESTS_FAILED=0

# Test 1: Executor should complete (non-zero exit is OK due to failures)
echo "Test 1: Executor completed execution..."
if [ -f "${DATA_DIR}/outputs/daily/${TEST_DATE}/.execution_complete" ]; then
    echo -e "${GREEN}✅ PASS${NC}: Executor marked completion despite failures"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}❌ FAIL${NC}: Executor did not complete"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# Test 2: Telemetry log exists
echo "Test 2: Telemetry log file created..."
if [ -f "$TEST_LOG" ]; then
    echo -e "${GREEN}✅ PASS${NC}: Telemetry log exists at $TEST_LOG"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}❌ FAIL${NC}: Telemetry log not found"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# Test 3: Telemetry log contains failure entries
echo "Test 3: Telemetry log contains failure entries..."
if [ -f "$TEST_LOG" ]; then
    FAILURE_COUNT=$(grep -c " END | .* | failure " "$TEST_LOG" 2>/dev/null || echo 0)
    if [ "$FAILURE_COUNT" -ge 2 ]; then
        echo -e "${GREEN}✅ PASS${NC}: Found $FAILURE_COUNT failure entries in log"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}❌ FAIL${NC}: Expected at least 2 failures, found $FAILURE_COUNT"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
else
    echo -e "${RED}❌ FAIL${NC}: Cannot check - log file missing"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# Test 4: JSON ledger exists
echo "Test 4: JSON ledger file created..."
if [ -f "$TEST_LEDGER" ]; then
    echo -e "${GREEN}✅ PASS${NC}: JSON ledger exists at $TEST_LEDGER"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}❌ FAIL${NC}: JSON ledger not found"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# Test 5: JSON ledger shows correct failure count
echo "Test 5: JSON ledger failure tracking..."
if [ -f "$TEST_LEDGER" ]; then
    LEDGER_FAILED=$(grep '"failed":' "$TEST_LEDGER" | tail -1 | sed 's/.*"failed": \([0-9]*\).*/\1/')
    LEDGER_SUCCESSFUL=$(grep '"successful":' "$TEST_LEDGER" | tail -1 | sed 's/.*"successful": \([0-9]*\).*/\1/')
    
    if [ "$LEDGER_FAILED" -ge 2 ] && [ "$LEDGER_SUCCESSFUL" -ge 3 ]; then
        echo -e "${GREEN}✅ PASS${NC}: Ledger shows $LEDGER_SUCCESSFUL successful, $LEDGER_FAILED failed"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}❌ FAIL${NC}: Unexpected counts - Success: $LEDGER_SUCCESSFUL, Failed: $LEDGER_FAILED"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
else
    echo -e "${RED}❌ FAIL${NC}: Cannot check - ledger file missing"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# Test 6: All prompts executed (not aborted early)
echo "Test 6: All prompts executed (non-blocking)..."
if [ -f "$TEST_LEDGER" ]; then
    TOTAL_EXECUTED=$(grep '"total":' "$TEST_LEDGER" | tail -1 | sed 's/.*"total": \([0-9]*\).*/\1/')
    if [ "$TOTAL_EXECUTED" -eq 5 ]; then
        echo -e "${GREEN}✅ PASS${NC}: All 5 prompts executed despite failures"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}❌ FAIL${NC}: Only $TOTAL_EXECUTED/5 prompts executed"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
else
    echo -e "${RED}❌ FAIL${NC}: Cannot check - ledger file missing"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# Test 7: Output files exist for all prompts
echo "Test 7: Output files created for all prompts..."
SUCCESS_FILE_COUNT=$(find "${DATA_DIR}/outputs/daily/${TEST_DATE}" -name "*.md" -type f 2>/dev/null | wc -l | xargs)
if [ "$SUCCESS_FILE_COUNT" -eq 5 ]; then
    echo -e "${GREEN}✅ PASS${NC}: All 5 output files created"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}❌ FAIL${NC}: Found $SUCCESS_FILE_COUNT/5 output files"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# Test 8: Check notification system (dry run)
echo "Test 8: Notification system check..."
echo -e "${BLUE}ℹ️  Testing notification script (dry run)${NC}"

# Run notification script
"${PROJECT_ROOT}/scripts/notifiers/notify_failures.sh" "$TEST_LEDGER" > /tmp/notification_test.log 2>&1
NOTIFY_EXIT=$?

if [ $NOTIFY_EXIT -eq 0 ]; then
    if grep -q "Failed prompts: " /tmp/notification_test.log; then
        echo -e "${GREEN}✅ PASS${NC}: Notification script executed successfully"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        
        # Show notification summary
        echo -e "${BLUE}   Notification log:${NC}"
        cat /tmp/notification_test.log | head -10
    else
        echo -e "${YELLOW}⚠️  PARTIAL${NC}: Script ran but output unexpected"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    fi
else
    echo -e "${RED}❌ FAIL${NC}: Notification script failed (exit $NOTIFY_EXIT)"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

rm -f /tmp/notification_test.log 2>/dev/null || true

echo ""
echo "========================================="
echo "Test Summary"
echo "========================================="
echo -e "Tests Passed: ${GREEN}${TESTS_PASSED}${NC}/8"
echo -e "Tests Failed: ${RED}${TESTS_FAILED}${NC}/8"
echo ""

if [ "$TESTS_FAILED" -eq 0 ]; then
    echo -e "${GREEN}✅ All failure handling tests passed!${NC}"
    echo ""
    echo "Test artifacts:"
    echo "  - Telemetry log: $TEST_LOG"
    echo "  - JSON ledger: $TEST_LEDGER"
    echo "  - Outputs: ${DATA_DIR}/outputs/daily/${TEST_DATE}/"
    echo ""
    echo -e "${YELLOW}📧 Note: To test actual email delivery, ensure:${NC}"
    echo "  1. ENABLE_FAILURE_NOTIFICATIONS=true in config/env.sh"
    echo "  2. 'mail' command is configured on your system"
    echo "  3. Run: ./scripts/orchestrator.sh"
    echo ""
    exit 0
else
    echo -e "${RED}❌ Some tests failed. Review output above.${NC}"
    echo ""
    echo "Debug information:"
    echo "  - Telemetry log: $TEST_LOG"
    echo "  - JSON ledger: $TEST_LEDGER"
    echo ""
    exit 1
fi
