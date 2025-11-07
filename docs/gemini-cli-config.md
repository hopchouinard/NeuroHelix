# Gemini CLI Configuration Reference

## Overview

NeuroHelix uses the Gemini CLI for all AI-powered research, synthesis, and analysis tasks. This document explains the configuration options and how they're used in the pipeline.

## Configuration Location

All Gemini CLI settings are defined in `config/env.sh`:

```bash
# CLI tools
export GEMINI_CLI="gemini"
export COPILOT_CLI="gh copilot"

# Gemini CLI settings
export GEMINI_MODEL="gemini-2.0-flash-exp"
export GEMINI_OUTPUT_FORMAT="text"
export GEMINI_APPROVAL_MODE="default"
export GEMINI_YOLO_MODE="false"
export GEMINI_DEBUG="false"
```

## Configuration Options

### GEMINI_MODEL

**Options:** Any valid Gemini model name
**Default:** `gemini-2.0-flash-exp`
**Usage:** Specifies which Gemini model to use for all queries

**Available models:**
- `gemini-2.0-flash-exp` - Fast, experimental (recommended for high-volume research)
- `gemini-pro` - Balanced performance
- `gemini-ultra` - Most capable (if available)

### GEMINI_OUTPUT_FORMAT

**Options:** `text`, `json`, `stream-json`
**Default:** `text`
**Usage:** Controls the format of Gemini CLI responses

- `text` - Plain text output (best for reports)
- `json` - Structured JSON output (for programmatic parsing)
- `stream-json` - Streaming JSON (for real-time processing)

### GEMINI_APPROVAL_MODE

**Options:** `default`, `auto_edit`, `yolo`
**Default:** `default`
**Usage:** Controls tool approval behavior (if using Gemini extensions/tools)

- `default` - Prompt for approval before running tools
- `auto_edit` - Auto-approve edit tools
- `yolo` - Auto-approve all tools (⚠️ use with caution)

### GEMINI_YOLO_MODE

**Options:** `true`, `false`
**Default:** `false`
**Usage:** Shortcut for `--yolo` flag (auto-approve all actions)

⚠️ **Warning:** Only enable in trusted, isolated environments.

### GEMINI_DEBUG

**Options:** `true`, `false`
**Default:** `false`
**Usage:** Enable verbose debug output

Set to `true` when troubleshooting pipeline issues.

## Usage in Scripts

### Prompt Executor (`scripts/executors/run_prompts.sh`)

Executes research prompts using positional arguments:

```bash
${GEMINI_CLI} ${DEBUG_FLAG} \
    --model "${GEMINI_MODEL}" \
    --output-format "${GEMINI_OUTPUT_FORMAT}" \
    "$prompt" >> "$output_file"
```

### Aggregator (`scripts/aggregators/aggregate_daily.sh`)

Generates executive summaries:

```bash
SUMMARY_OUTPUT=$(${GEMINI_CLI} \
    --model "${GEMINI_MODEL}" \
    --output-format "${GEMINI_OUTPUT_FORMAT}" \
    "$SUMMARY_PROMPT")
```

## Command Line Reference

### Non-Interactive Mode (Default for NeuroHelix)

```bash
gemini "Your prompt here"
```

### With Model Selection

```bash
gemini --model gemini-2.0-flash-exp "Your prompt"
```

### With Output Format

```bash
gemini --output-format json "Your prompt"
```

### Interactive Mode

```bash
gemini  # Launch interactive CLI
```

### Prompt Interactive (Execute then stay interactive)

```bash
gemini --prompt-interactive "Initial query"
```

### Debug Mode

```bash
gemini --debug "Your prompt"
```

## Advanced Options

### Extensions

```bash
gemini --extensions extension1,extension2 "Your prompt"
```

### List Available Extensions

```bash
gemini --list-extensions
```

### MCP Server Management

```bash
gemini mcp  # Manage MCP servers
```

### Allowed MCP Servers

```bash
gemini --allowed-mcp-server-names server1,server2 "Your prompt"
```

### Include Additional Directories

```bash
gemini --include-directories /path/to/dir "Your prompt"
```

### Screen Reader Mode

```bash
gemini --screen-reader "Your prompt"
```

## Troubleshooting

### Enable Debug Output

Set in `config/env.sh`:
```bash
export GEMINI_DEBUG="true"
```

Then run the pipeline:
```bash
./scripts/orchestrator.sh
```

Check logs in `logs/` directory for detailed output.

### Test Gemini CLI Directly

```bash
gemini --model gemini-2.0-flash-exp "What is 2+2?"
```

### Verify Configuration

```bash
source config/env.sh
echo "Model: $GEMINI_MODEL"
echo "Output Format: $GEMINI_OUTPUT_FORMAT"
echo "Debug: $GEMINI_DEBUG"
```

## Performance Optimization

### For High-Volume Research

```bash
export GEMINI_MODEL="gemini-2.0-flash-exp"  # Fastest model
export GEMINI_OUTPUT_FORMAT="text"  # Minimal overhead
export PARALLEL_EXECUTION="true"  # Run prompts in parallel
export MAX_PARALLEL_JOBS="4"  # Adjust based on rate limits
```

### For Structured Data Extraction

```bash
export GEMINI_OUTPUT_FORMAT="json"  # Structured output
```

### For Real-Time Monitoring

```bash
export GEMINI_OUTPUT_FORMAT="stream-json"  # Streaming responses
```

## Rate Limits & Best Practices

1. **Monitor API usage** - Check your Gemini API quota regularly
2. **Adjust parallel jobs** - Start with 4, increase if rate limits allow
3. **Cache results** - NeuroHelix stores all outputs in `data/outputs/`
4. **Use appropriate models** - Flash for research, Pro/Ultra for complex analysis

## Security Notes

- **Never enable `yolo` mode** in production without understanding the risks
- **Keep API keys secure** - Use environment variables or secret management
- **Review tool approvals** - Understand what tools Gemini might invoke
- **Sandbox mode** - Use `--sandbox` flag for untrusted prompts

## Example Configurations

### Conservative (Recommended for Production)

```bash
export GEMINI_MODEL="gemini-2.0-flash-exp"
export GEMINI_OUTPUT_FORMAT="text"
export GEMINI_APPROVAL_MODE="default"
export GEMINI_YOLO_MODE="false"
export GEMINI_DEBUG="false"
export MAX_PARALLEL_JOBS="2"
```

### High-Throughput (Research/Development)

```bash
export GEMINI_MODEL="gemini-2.0-flash-exp"
export GEMINI_OUTPUT_FORMAT="text"
export GEMINI_APPROVAL_MODE="auto_edit"
export GEMINI_YOLO_MODE="false"
export GEMINI_DEBUG="false"
export MAX_PARALLEL_JOBS="8"
```

### Debug/Troubleshooting

```bash
export GEMINI_MODEL="gemini-2.0-flash-exp"
export GEMINI_OUTPUT_FORMAT="text"
export GEMINI_APPROVAL_MODE="default"
export GEMINI_YOLO_MODE="false"
export GEMINI_DEBUG="true"
export MAX_PARALLEL_JOBS="1"  # Sequential for clearer logs
export PARALLEL_EXECUTION="false"
```

## Related Documentation

- [Gemini CLI Official Docs](https://github.com/google/generative-ai-cli) *(if available)*
- [NeuroHelix README](../README.md)
- [Pipeline Architecture](./pipeline-architecture.md) *(if exists)*

## Support

If you encounter issues with Gemini CLI configuration:

1. Check `logs/` directory for error messages
2. Run with `GEMINI_DEBUG="true"` for verbose output
3. Test Gemini CLI directly: `gemini "test"`
4. Verify API credentials are configured
5. Check rate limits and quotas

---

**Last Updated:** 2025-11-07  
**NeuroHelix Version:** 1.0
