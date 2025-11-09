#!/usr/bin/env bash

# export_source_manifest.sh
# Generates source manifests for raw artifacts and copies them to the static site.
# This script creates the metadata needed for the Source View feature.

set -euo pipefail

# Source environment configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
source "${PROJECT_ROOT}/config/env.sh"

# Constants
OUTPUTS_DIR="${PROJECT_ROOT}/data/outputs/daily"
MANIFESTS_DIR="${PROJECT_ROOT}/data/publishing/source_manifests"
VECTOR_EXPORTS_DIR="${PROJECT_ROOT}/data/publishing/vector_exports"
SITE_STATIC_DIR="${PROJECT_ROOT}/site/static/source"

# Get date parameter or use today's date
TARGET_DATE="${1:-$(date +%Y-%m-%d)}"

# Paths for this specific date
SOURCE_ROOT="${OUTPUTS_DIR}/${TARGET_DATE}"
MANIFEST_FILE="${MANIFESTS_DIR}/${TARGET_DATE}.json"
VECTOR_EXPORT_FILE="${VECTOR_EXPORTS_DIR}/${TARGET_DATE}.json"
STATIC_TARGET_DIR="${SITE_STATIC_DIR}/${TARGET_DATE}"

# Ensure required directories exist
mkdir -p "${MANIFESTS_DIR}"
mkdir -p "${VECTOR_EXPORTS_DIR}"
mkdir -p "${SITE_STATIC_DIR}"

# Check if source directory exists
if [[ ! -d "${SOURCE_ROOT}" ]]; then
    echo "ERROR: Source directory not found: ${SOURCE_ROOT}"
    exit 1
fi

echo "Generating source manifest for ${TARGET_DATE}..."

# Determine artifact type based on path and filename patterns
determine_artifact_type() {
    local path="$1"
    local filename=$(basename "$path")
    local dirname=$(dirname "$path" | xargs basename)

    # Check directory patterns first
    if [[ "$path" =~ prompts?/ ]]; then
        echo "prompt"
    elif [[ "$path" =~ summar(y|ies)/ ]]; then
        echo "raw_summary"
    elif [[ "$path" =~ cross[_-]?analysis/ ]] || [[ "$filename" =~ cross[_-]?analysis ]]; then
        echo "cross_analysis"
    elif [[ "$path" =~ (insight|draft)s?/ ]] || [[ "$filename" =~ (insight|draft) ]]; then
        echo "insight_draft"
    elif [[ "$path" =~ metadata/ ]] || [[ "$filename" =~ metadata|meta\. ]]; then
        echo "metadata"
    else
        echo "other"
    fi
}

# Determine display group based on path
determine_display_group() {
    local path="$1"

    if [[ "$path" =~ research/ ]]; then
        echo "Research"
    elif [[ "$path" =~ market/ ]]; then
        echo "Market"
    elif [[ "$path" =~ ideation/ ]]; then
        echo "Ideation"
    elif [[ "$path" =~ analysis/ ]]; then
        echo "Analysis"
    elif [[ "$path" =~ meta/ ]]; then
        echo "Meta"
    else
        echo "Other"
    fi
}

# Determine MIME type based on extension
determine_mime_type() {
    local filename="$1"
    local ext="${filename##*.}"

    case "${ext,,}" in
        md|markdown) echo "text/markdown" ;;
        json) echo "application/json" ;;
        yaml|yml) echo "application/yaml" ;;
        txt) echo "text/plain" ;;
        csv) echo "text/csv" ;;
        png) echo "image/png" ;;
        jpg|jpeg) echo "image/jpeg" ;;
        svg) echo "image/svg+xml" ;;
        *) echo "application/octet-stream" ;;
    esac
}

# Extract TOC from markdown files
extract_toc() {
    local filepath="$1"
    local mime="$2"

    if [[ "$mime" != "text/markdown" ]]; then
        echo "[]"
        return
    fi

    # Extract headings and generate TOC entries
    local toc_entries=""
    while IFS= read -r line; do
        if [[ "$line" =~ ^#{1,6}[[:space:]](.+)$ ]]; then
            local heading="${BASH_REMATCH[1]}"
            # Create anchor from heading (lowercase, replace spaces with dashes, remove special chars)
            local anchor=$(echo "$heading" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9 -]//g' | tr ' ' '-' | sed 's/--*/-/g')

            if [[ -n "$toc_entries" ]]; then
                toc_entries+=","
            fi
            # Escape quotes in heading
            heading_escaped=$(echo "$heading" | sed 's/"/\\"/g')
            toc_entries+="{\"text\":\"${heading_escaped}\",\"hash\":\"#${anchor}\"}"
        fi
    done < "$filepath"

    if [[ -n "$toc_entries" ]]; then
        echo "[${toc_entries}]"
    else
        echo "[]"
    fi
}

# Generate preview text (first 280 chars, sanitized)
generate_preview() {
    local filepath="$1"
    local mime="$2"

    # Only generate previews for text files
    if [[ ! "$mime" =~ ^text/ ]] && [[ ! "$mime" =~ json$ ]]; then
        echo ""
        return
    fi

    # Read first 500 chars and sanitize
    local content=$(head -c 500 "$filepath" | tr -d '\000-\011\013-\037' | sed 's/"/\\"/g')
    # Truncate to 280 chars
    echo "${content:0:280}"
}

# Initialize manifest structure
cat > "${MANIFEST_FILE}.tmp" <<EOF
{
  "date": "${TARGET_DATE}",
  "root": "data/outputs/daily/${TARGET_DATE}",
  "generatedAt": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "artifacts": [
EOF

# Initialize vector export
cat > "${VECTOR_EXPORT_FILE}.tmp" <<EOF
{
  "date": "${TARGET_DATE}",
  "generatedAt": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "artifacts": [
EOF

# Initialize stats counters
declare -A type_counts
total_size=0
artifact_count=0

# Process all files in the source directory
first_entry=true
first_vector_entry=true

while IFS= read -r filepath; do
    # Get relative path from source root
    relative_path="${filepath#${SOURCE_ROOT}/}"

    # Skip hidden files and directories
    if [[ "$relative_path" =~ /\. ]] || [[ "$relative_path" =~ ^\. ]]; then
        continue
    fi

    # Get file metadata
    file_size=$(stat -f%z "$filepath" 2>/dev/null || stat -c%s "$filepath" 2>/dev/null)
    checksum=$(shasum -a 256 "$filepath" | cut -d' ' -f1 | cut -c1-16)
    created_at=$(stat -f%Sm -t "%Y-%m-%dT%H:%M:%SZ" "$filepath" 2>/dev/null || date -r "$filepath" -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null)

    # Determine artifact properties
    artifact_type=$(determine_artifact_type "$relative_path")
    display_group=$(determine_display_group "$relative_path")
    mime_type=$(determine_mime_type "$(basename "$filepath")")

    # Extract TOC if markdown
    toc=$(extract_toc "$filepath" "$mime_type")

    # Generate preview
    preview=$(generate_preview "$filepath" "$mime_type")

    # Update stats
    type_counts[$artifact_type]=$((${type_counts[$artifact_type]:-0} + 1))
    total_size=$((total_size + file_size))
    artifact_count=$((artifact_count + 1))

    # Escape relative path for JSON
    relative_path_escaped=$(echo "$relative_path" | sed 's/"/\\"/g')

    # Add comma separator if not first entry
    if [[ "$first_entry" = true ]]; then
        first_entry=false
    else
        echo "," >> "${MANIFEST_FILE}.tmp"
    fi

    # Add manifest entry
    cat >> "${MANIFEST_FILE}.tmp" <<EOF_ARTIFACT
    {
      "relativePath": "${relative_path_escaped}",
      "artifactType": "${artifact_type}",
      "displayGroup": "${display_group}",
      "sizeBytes": ${file_size},
      "checksum": "${checksum}",
      "createdAt": "${created_at}",
      "mime": "${mime_type}",
      "tags": ["${artifact_type}"],
      "toc": ${toc},
      "preview": "${preview}"
    }
EOF_ARTIFACT

    # Add vector export entry
    if [[ "$first_vector_entry" = true ]]; then
        first_vector_entry=false
    else
        echo "," >> "${VECTOR_EXPORT_FILE}.tmp"
    fi

    cat >> "${VECTOR_EXPORT_FILE}.tmp" <<EOF_VECTOR
    {
      "id": "${TARGET_DATE}::source::${relative_path_escaped}",
      "artifactType": "${artifact_type}",
      "path": "${relative_path_escaped}",
      "contentHash": "${checksum}",
      "sizeBytes": ${file_size},
      "mime": "${mime_type}"
    }
EOF_VECTOR

done < <(find "$SOURCE_ROOT" -type f | sort)

# Close artifacts array
echo -e "\n  ]," >> "${MANIFEST_FILE}.tmp"
echo -e "\n  ]" >> "${VECTOR_EXPORT_FILE}.tmp"

# Build type counts JSON
type_counts_json="{"
first_type=true
for type in "${!type_counts[@]}"; do
    if [[ "$first_type" = true ]]; then
        first_type=false
    else
        type_counts_json+=","
    fi
    type_counts_json+="\"${type}\":${type_counts[$type]}"
done
type_counts_json+="}"

# Add stats section
cat >> "${MANIFEST_FILE}.tmp" <<EOF
  "stats": {
    "artifactCount": ${artifact_count},
    "byteSize": ${total_size},
    "types": ${type_counts_json}
  }
}
EOF

# Close vector export
echo "}" >> "${VECTOR_EXPORT_FILE}.tmp"

# Atomically move temp files to final location
mv "${MANIFEST_FILE}.tmp" "${MANIFEST_FILE}"
mv "${VECTOR_EXPORT_FILE}.tmp" "${VECTOR_EXPORT_FILE}"

echo "✓ Generated manifest with ${artifact_count} artifacts (${total_size} bytes)"

# Copy raw files to static directory
echo "Copying raw artifacts to static directory..."
rm -rf "${STATIC_TARGET_DIR}"
mkdir -p "${STATIC_TARGET_DIR}"

# Use rsync to copy files while preserving structure
rsync -av --exclude='.*' "${SOURCE_ROOT}/" "${STATIC_TARGET_DIR}/"

echo "✓ Copied artifacts to ${STATIC_TARGET_DIR}"

# Log summary
echo "=== Source Manifest Summary for ${TARGET_DATE} ==="
echo "Artifacts: ${artifact_count}"
echo "Total size: ${total_size} bytes"
echo "Types: ${type_counts_json}"
echo "Manifest: ${MANIFEST_FILE}"
echo "Vector export: ${VECTOR_EXPORT_FILE}"
echo "Static files: ${STATIC_TARGET_DIR}"
echo "==========================================="

exit 0
