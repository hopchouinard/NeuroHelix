#!/bin/bash
# Test single Gemini CLI call

source config/env.sh

echo "Testing Gemini CLI with a simple prompt..."

TEST_PROMPT="What is 2+2? Answer in one sentence."

echo "Running: gemini --model ${GEMINI_MODEL} --output-format ${GEMINI_OUTPUT_FORMAT} \"${TEST_PROMPT}\""

timeout 30 gemini --model "${GEMINI_MODEL}" --output-format "${GEMINI_OUTPUT_FORMAT}" "${TEST_PROMPT}" < /dev/null

echo ""
echo "Exit code: $?"
