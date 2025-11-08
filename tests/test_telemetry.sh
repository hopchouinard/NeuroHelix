#!/bin/bash
# Test telemetry logging functionality
# Validates log creation, JSON ledger structure, and timestamp handling

set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

source "${PROJECT_ROOT}/config/env.sh"
source "${PROJECT_ROOT}/scripts/lib/telemetry.sh"

# Test configuration
TEST_DATE="2025-01-01"  # Use fixed date for testing
TEST_LOG_FILE="${LOGS_DIR}/prompt_execution_${TEST_DATE}.log"
TEST_LEDGER_FILE="${RUNTIME_DIR}/execution_ledger_${TEST_DATE}.json"
TEST_TEMP_FILE="${RUNTIME_DIR}/.telemetry_temp_${TEST_DATE}.txt"

TESTS_PASSED=0
TESTS_FAILED=0

# Cleanup function
cleanup_test_files() {
    rm -f "$TEST_LOG_FILE" "$TEST_LEDGER_FILE" "$TEST_TEMP_FILE" 2>/dev/null || true
}

# Print test result
print_result() {
    local test_name="$1"
    local result="$2"
    local message="${3:-}"
    
    if [ "$result" = "PASS" ]; then
        echo -e "${GREEN}✅ PASS${NC}: $test_name"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}❌ FAIL${NC}: $test_name"
        if [ -n "$message" ]; then
            echo -e "   ${YELLOW}$message${NC}"
        fi
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

echo "========================================="
echo "NeuroHelix Telemetry Testing Suite"
echo "========================================="
echo ""

# Clean up any existing test files
cleanup_test_files

# Test 1: Telemetry log initialization
echo "Test 1: Telemetry log file creation..."
init_telemetry_log "$TEST_DATE"

if [ -f "$TEST_LOG_FILE" ]; then
    if grep -q "NeuroHelix Prompt Execution Telemetry Log" "$TEST_LOG_FILE"; then
        print_result "Log file creation" "PASS"
    else
        print_result "Log file creation" "FAIL" "Header not found in log file"
    fi
else
    print_result "Log file creation" "FAIL" "Log file not created"
fi

# Test 2: Execution ledger initialization
echo "Test 2: Execution ledger JSON creation..."
init_execution_ledger "$TEST_DATE"

if [ -f "$TEST_LEDGER_FILE" ]; then
    # Validate JSON structure
    if grep -q '"date": "'$TEST_DATE'"' "$TEST_LEDGER_FILE" && \
       grep -q '"executions": \[' "$TEST_LEDGER_FILE" && \
       grep -q '"summary": {' "$TEST_LEDGER_FILE"; then
        print_result "Ledger file creation" "PASS"
    else
        print_result "Ledger file creation" "FAIL" "JSON structure incomplete"
    fi
else
    print_result "Ledger file creation" "FAIL" "Ledger file not created"
fi

# Test 3: ISO8601 timestamp formatting
echo "Test 3: ISO8601 timestamp format..."
TIMESTAMP=$(format_iso8601)

# Check if timestamp matches ISO8601 pattern (basic validation)
if echo "$TIMESTAMP" | grep -qE '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}'; then
    print_result "ISO8601 formatting" "PASS"
else
    print_result "ISO8601 formatting" "FAIL" "Timestamp: $TIMESTAMP"
fi

# Test 4: Log prompt start
echo "Test 4: Logging prompt start..."
log_prompt_start "Test Prompt" "Research" "Research"

if grep -q "START | Test Prompt | Research | Research" "$TEST_LOG_FILE"; then
    print_result "Log prompt start" "PASS"
else
    print_result "Log prompt start" "FAIL" "Start entry not found in log"
fi

# Test 5: Log prompt end (success)
echo "Test 5: Logging prompt end (success)..."
sleep 1  # Small delay to ensure duration is measurable
log_prompt_end "Test Prompt" "Research" "Research" "success"

if grep -q "END | Test Prompt | Research | success" "$TEST_LOG_FILE"; then
    print_result "Log prompt end (success)" "PASS"
else
    print_result "Log prompt end (success)" "FAIL" "End entry not found in log"
fi

# Test 6: Log prompt end (failure)
echo "Test 6: Logging prompt end (failure)..."
log_prompt_start "Failed Prompt" "Analysis" "Analysis"
sleep 1
log_prompt_end "Failed Prompt" "Analysis" "Analysis" "failure" "Test error message"

if grep -q "END | Failed Prompt | Analysis | failure" "$TEST_LOG_FILE" && \
   grep -q "Error: Test error message" "$TEST_LOG_FILE"; then
    print_result "Log prompt end (failure)" "PASS"
else
    print_result "Log prompt end (failure)" "FAIL" "Failure entry incomplete"
fi

# Test 7: Add entries to ledger
echo "Test 7: Adding entries to ledger..."
START_TIME=$(format_iso8601)
sleep 2
END_TIME=$(format_iso8601)

add_to_ledger "Test Prompt Success" "Research" "Research" "$START_TIME" "$END_TIME" "success" "/tmp/test.md" ""
add_to_ledger "Test Prompt Failure" "Analysis" "Analysis" "$START_TIME" "$END_TIME" "failure" "/tmp/test2.md" "Test error"

# Verify entries in ledger
if grep -q '"prompt_name": "Test Prompt Success"' "$TEST_LEDGER_FILE" && \
   grep -q '"prompt_name": "Test Prompt Failure"' "$TEST_LEDGER_FILE" && \
   grep -q '"status": "success"' "$TEST_LEDGER_FILE" && \
   grep -q '"status": "failure"' "$TEST_LEDGER_FILE"; then
    print_result "Add ledger entries" "PASS"
else
    print_result "Add ledger entries" "FAIL" "Entries not found in ledger"
fi

# Test 8: JSON schema validation
echo "Test 8: JSON schema validation..."
SCHEMA_VALID=true

# Check required fields
for field in "prompt_id" "prompt_name" "category" "stage" "start_time" "end_time" "duration_seconds" "status" "output_file"; do
    if ! grep -q "\"$field\":" "$TEST_LEDGER_FILE"; then
        SCHEMA_VALID=false
        break
    fi
done

if [ "$SCHEMA_VALID" = true ]; then
    print_result "JSON schema" "PASS"
else
    print_result "JSON schema" "FAIL" "Required field missing"
fi

# Test 9: Duration calculation
echo "Test 9: Duration calculation..."
# Test with known timestamps (2 seconds apart)
# Note: macOS date format
DURATION=$(calculate_duration "$START_TIME" "$END_TIME")

if [ "$DURATION" -ge 1 ] && [ "$DURATION" -le 3 ]; then
    print_result "Duration calculation" "PASS"
else
    print_result "Duration calculation" "FAIL" "Expected ~2s, got ${DURATION}s"
fi

# Test 10: Finalize ledger summary
echo "Test 10: Finalizing ledger summary..."
finalize_ledger_summary

# Extract summary values
TOTAL=$(grep '"total":' "$TEST_LEDGER_FILE" | sed 's/.*"total": \([0-9]*\).*/\1/')
SUCCESSFUL=$(grep '"successful":' "$TEST_LEDGER_FILE" | sed 's/.*"successful": \([0-9]*\).*/\1/')
FAILED=$(grep '"failed":' "$TEST_LEDGER_FILE" | sed 's/.*"failed": \([0-9]*\).*/\1/')

# We added 2 entries (1 success, 1 failure)
if [ "$TOTAL" = "2" ] && [ "$SUCCESSFUL" = "1" ] && [ "$FAILED" = "1" ]; then
    print_result "Summary statistics" "PASS"
else
    print_result "Summary statistics" "FAIL" "Total=$TOTAL, Success=$SUCCESSFUL, Failed=$FAILED (expected 2,1,1)"
fi

# Test 11: Format duration helper
echo "Test 11: Format duration helper..."
DURATION_5S=$(format_duration 5)
DURATION_90S=$(format_duration 90)
DURATION_3700S=$(format_duration 3700)

if [ "$DURATION_5S" = "5s" ] && \
   [ "$DURATION_90S" = "1m 30s" ] && \
   [ "$DURATION_3700S" = "1h 1m" ]; then
    print_result "Duration formatting" "PASS"
else
    print_result "Duration formatting" "FAIL" "5s=$DURATION_5S, 90s=$DURATION_90S, 3700s=$DURATION_3700S"
fi

# Test 12: Log file structure
echo "Test 12: Log file structure validation..."
if grep -q "^# NeuroHelix" "$TEST_LOG_FILE" && \
   grep -q "^# Format:" "$TEST_LOG_FILE" && \
   grep -q "^\[.*\] START |" "$TEST_LOG_FILE" && \
   grep -q "^\[.*\] END |" "$TEST_LOG_FILE"; then
    print_result "Log file structure" "PASS"
else
    print_result "Log file structure" "FAIL" "Expected format not found"
fi

# Test 13: Validate JSON is parseable
echo "Test 13: JSON parseability..."
if python3 -c "import json; json.load(open('$TEST_LEDGER_FILE'))" 2>/dev/null; then
    print_result "JSON parseability" "PASS"
elif which jq &>/dev/null && jq empty "$TEST_LEDGER_FILE" &>/dev/null; then
    print_result "JSON parseability" "PASS"
else
    print_result "JSON parseability" "FAIL" "JSON is not valid (tested with python3/jq)"
fi

# Test 14: Multiple prompt tracking
echo "Test 14: Multiple prompt tracking..."
# Add 3 more prompts
for i in {1..3}; do
    START=$(format_iso8601)
    sleep 0.5
    END=$(format_iso8601)
    add_to_ledger "Prompt $i" "Test" "Research" "$START" "$END" "success" "/tmp/test$i.md" ""
done

finalize_ledger_summary
FINAL_TOTAL=$(grep '"total":' "$TEST_LEDGER_FILE" | sed 's/.*"total": \([0-9]*\).*/\1/')

if [ "$FINAL_TOTAL" = "5" ]; then
    print_result "Multiple prompt tracking" "PASS"
else
    print_result "Multiple prompt tracking" "FAIL" "Expected 5 total prompts, got $FINAL_TOTAL"
fi

echo ""
echo "========================================="
echo "Test Summary"
echo "========================================="
echo -e "Tests Passed: ${GREEN}${TESTS_PASSED}${NC}"
echo -e "Tests Failed: ${RED}${TESTS_FAILED}${NC}"
echo "Total Tests: $((TESTS_PASSED + TESTS_FAILED))"
echo ""

if [ "$TESTS_FAILED" -eq 0 ]; then
    echo -e "${GREEN}✅ All telemetry tests passed!${NC}"
    echo ""
    echo "Test files created:"
    echo "  - $TEST_LOG_FILE"
    echo "  - $TEST_LEDGER_FILE"
    echo ""
    echo "You can inspect these files to see the telemetry output."
    cleanup_test_files
    exit 0
else
    echo -e "${RED}❌ Some tests failed. Review output above for details.${NC}"
    echo ""
    echo "Test files preserved for debugging:"
    echo "  - $TEST_LOG_FILE"
    echo "  - $TEST_LEDGER_FILE"
    exit 1
fi
