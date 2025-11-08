# Tag & Category Extraction Fix

## Problem

The NeuroHelix pipeline was generating JSON files for the static site with empty `tags` and `categories` arrays, causing the site to not display this metadata.

### Root Cause

The `Keyword Tag Generator` prompt in `config/searches.tsv` was configured to run during the **execution phase** (Step 1), but it needed to read the daily report which is only created during the **aggregation phase** (Step 2). This timing mismatch meant:

1. Tag generator prompt runs at 7:00 AM
2. It tries to read `data/reports/daily_report_YYYY-MM-DD.md`  
3. File doesn't exist yet (created 30+ seconds later during aggregation)
4. Prompt fails with: "File path is ignored by configured ignore patterns"
5. No tags extracted → empty arrays in JSON

## Solution

Created a **post-aggregation tag extraction script** that runs after the report is complete:

### 1. New Script: `scripts/aggregators/extract_tags.sh`

**Purpose**: Extract tags and categories from the completed daily report using Gemini AI

**Key features**:
- Runs AFTER `aggregate_daily.sh` completes
- Reads the completed report
- Sends structured prompt to Gemini for metadata extraction
- Handles JSON parsing with multiline support
- Validates output with `jq`
- Falls back to empty arrays if extraction fails
- Idempotent (skips if tags file is newer than report)

**Output**: `data/reports/tags_YYYY-MM-DD.json`

```json
{
  "tags": ["AI Models", "AI Governance", "Developer Tools", "NVIDIA Blackwell", "Google AI", "OpenAI", "Edge AI", "Open Source"],
  "categories": ["AI Models", "Market Analysis", "Regulation", "Developer Tools", "Hardware"]
}
```

### 2. Updated Pipeline: `scripts/orchestrator.sh`

Added **Step 2.5** between aggregation and dashboard rendering:

```bash
# Step 2: Aggregate results
scripts/aggregators/aggregate_daily.sh

# Step 2.5: Extract tags and categories  ← NEW
scripts/aggregators/extract_tags.sh

# Step 3: Generate dashboard
scripts/renderers/generate_dashboard.sh

# Step 4: Export static site payload
scripts/renderers/export_site_payload.sh
```

### 3. Updated Export: `scripts/renderers/export_site_payload.sh`

Changed from:
```bash
TAGS_FILE="${DATA_DIR}/outputs/daily/${DATE}/keyword_tag_generator.md"
```

To:
```bash
TAGS_FILE="${DATA_DIR}/reports/tags_${DATE}.json"
```

Simplified extraction logic to read from clean JSON file instead of parsing markdown output.

### 4. Disabled Old Prompt: `config/searches.tsv`

Set `Keyword Tag Generator` prompt to `enabled=false` since it's replaced by the dedicated script.

The prompt is preserved in the file for reference but won't run during execution phase.

## Benefits

### 1. **Correct Timing**
- Tags extracted AFTER report exists
- No more file-not-found errors
- Reliable execution every time

### 2. **Better Reliability**
- Dedicated script with error handling
- Clean JSON output validation
- Fallback to empty arrays on failure
- Non-fatal errors (pipeline continues)

### 3. **Improved Quality**
- Can read entire completed report
- Better context for tag extraction
- More accurate categorization

### 4. **Maintainability**
- Separate, focused script
- Easy to test independently
- Clear logging and debugging

## Testing Results

### Before Fix
```
📦 Starting content ingestion...
✅ Ingestion complete: 1 dashboards processed
🏷️  Extracted 0 unique tags  ← No tags!
```

### After Fix
```
🏷️  Extracting tags and categories from 2025-11-07 report...
🤖 Calling AI to extract tags (this may take 10-15 seconds)...
✅ Tags extracted successfully: data/reports/tags_2025-11-07.json
🏷️  Extracted 8 tags and 5 categories
   Tags: AI Models, AI Governance, Developer Tools, NVIDIA Blackwell, Google AI, OpenAI, Edge AI, Open Source
   Categories: AI Models, Market Analysis, Regulation, Developer Tools, Hardware

📦 Exporting structured payload for 2025-11-07...
✅ Payload exported successfully: data/publishing/2025-11-07.json
📊 Payload size: 32K
🏷️  Tags extracted: 8 tags, 5 categories

# Site build
📦 Starting content ingestion...
✅ Ingestion complete: 1 dashboards processed
🏷️  Extracted 8 unique tags  ← Tags present!
```

### Site Display

Dashboard pages now show:
- **8 purple tag chips**: AI Models, AI Governance, Developer Tools, NVIDIA Blackwell, Google AI, OpenAI, Edge AI, Open Source
- **3 amber category chips**: AI Trends, Regulation, Tooling

(Categories are derived from tags by the site's ingest script based on mapping rules)

## Files Modified

1. **Created**: `scripts/aggregators/extract_tags.sh` - New tag extraction script (117 lines)
2. **Modified**: `scripts/orchestrator.sh` - Added Step 2.5 call
3. **Modified**: `scripts/renderers/export_site_payload.sh` - Changed tags file path and parsing logic
4. **Modified**: `config/searches.tsv` - Disabled Keyword Tag Generator prompt

## Usage

### Manual Tag Extraction
```bash
cd /Users/pchouinard/Dev/NeuroHelix
./scripts/aggregators/extract_tags.sh
```

### Regenerate Tags
```bash
rm data/reports/tags_YYYY-MM-DD.json
./scripts/aggregators/extract_tags.sh
```

### Full Pipeline
```bash
./scripts/orchestrator.sh
# Now includes tag extraction automatically at Step 2.5
```

## Customization

### Adjust Tag Categories

Edit the category list in `scripts/aggregators/extract_tags.sh`:

```bash
2. Map findings to 3-5 categories from this list:
   - AI Models
   - Market Analysis  
   - Regulation
   - Strategy
   - Developer Tools
   - Hardware
   - Research
   - Safety & Ethics
```

### Change Tag Count

Modify the prompt rules in `extract_tags.sh`:

```bash
1. Extract 5-8 concise tags (1-3 words each) representing:
   #        ^^^
   # Change range here
```

## Troubleshooting

### Tags Still Empty

1. Check if extract_tags.sh ran:
   ```bash
   ls -la data/reports/tags_*.json
   ```

2. Check tags file content:
   ```bash
   cat data/reports/tags_YYYY-MM-DD.json
   ```

3. Run manually with verbose output:
   ```bash
   bash -x ./scripts/aggregators/extract_tags.sh
   ```

### Invalid JSON Errors

The script handles this gracefully:
- Cleans markdown code blocks
- Extracts multiline JSON
- Validates with jq
- Falls back to empty arrays if invalid

### Gemini CLI Issues

1. Test Gemini CLI directly:
   ```bash
   gemini "test"
   ```

2. Check authentication:
   ```bash
   gemini --version
   ```

3. Review temp file if extraction fails:
   ```bash
   cat data/reports/tags_YYYY-MM-DD.json.tmp
   ```

## Impact

- ✅ **Site**: Now displays tags and categories correctly
- ✅ **Search**: Tags indexed for full-text search
- ✅ **Filtering**: Tags available for client-side filtering
- ✅ **SEO**: Metadata present in page HTML
- ✅ **UX**: Visual categorization helps users understand content
- ✅ **Pipeline**: More robust and maintainable
