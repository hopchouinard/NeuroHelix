#!/bin/bash
# Cloudflare Pages deployment script for NeuroHelix static site
# Builds Astro site and deploys to Cloudflare Pages

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SITE_DIR="${PROJECT_ROOT}/site"
LOGS_DIR="${PROJECT_ROOT}/logs/publishing"
DATE=$(date +%Y-%m-%d)
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)
LOG_FILE="${LOGS_DIR}/publish_${TIMESTAMP}.log"

# Create directories
mkdir -p "${LOGS_DIR}"

log() {
    echo "[$(date +%Y-%m-%d\ %H:%M:%S)] $*" | tee -a "$LOG_FILE"
}

log "🚀 Starting static site publish for ${DATE}"

# Source environment
source "${PROJECT_ROOT}/config/env.sh"

# Load Cloudflare token if available
if [ -f "${PROJECT_ROOT}/.env.local" ]; then
    source "${PROJECT_ROOT}/.env.local"
fi

# Validate dependencies
log "🔍 Validating dependencies..."

if ! command -v node &> /dev/null; then
    log "❌ Error: node not found"
    exit 1
fi

if ! command -v pnpm &> /dev/null; then
    log "❌ Error: pnpm not found"
    exit 1
fi

NODE_VERSION=$(node --version)
log "✅ Node version: ${NODE_VERSION}"

# Check Cloudflare token
if [ -z "${CLOUDFLARE_API_TOKEN:-}" ]; then
    log "⚠️  Warning: CLOUDFLARE_API_TOKEN not set"
    log "   Deployment will be skipped. Configure .env.local to enable publishing."
    exit 0
fi

# Build Phase
log "📦 Step 1: Building site..."
BUILD_START=$(date +%s)

cd "${SITE_DIR}"

# Install dependencies
log "Installing dependencies..."
pnpm install --frozen-lockfile >> "$LOG_FILE" 2>&1 || {
    log "❌ Error: pnpm install failed"
    exit 1
}

# Build site (triggers prebuild hooks: ingestion + search index)
log "Building Astro site..."
pnpm run build >> "$LOG_FILE" 2>&1 || {
    log "❌ Error: Astro build failed"
    exit 1
}

BUILD_END=$(date +%s)
BUILD_DURATION=$((BUILD_END - BUILD_START))

# Measure bundle size
if [ -d "dist" ]; then
    BUNDLE_SIZE_KB=$(du -sk dist | cut -f1)
    BUNDLE_SIZE_MB=$(echo "scale=2; ${BUNDLE_SIZE_KB} / 1024" | bc)
    log "📊 Bundle size: ${BUNDLE_SIZE_MB}MB"
else
    log "❌ Error: dist directory not found after build"
    exit 1
fi

log "✅ Build complete in ${BUILD_DURATION}s"

# Deploy Phase
log "🌐 Step 2: Deploying to Cloudflare Pages..."

DEPLOY_OUTPUT=$(npx wrangler pages deploy dist \
    --project-name="${CLOUDFLARE_PROJECT_NAME}" \
    --branch=production \
    --commit-dirty 2>&1)

DEPLOY_EXIT=$?

echo "$DEPLOY_OUTPUT" >> "$LOG_FILE"

if [ $DEPLOY_EXIT -ne 0 ]; then
    log "❌ Error: Cloudflare deployment failed"
    log "   Check logs at: $LOG_FILE"
    exit 1
fi

# Extract deployment URL
DEPLOY_URL=$(echo "$DEPLOY_OUTPUT" | grep -o 'https://[^[:space:]]*pages.dev' | head -1 || echo "https://${CLOUDFLARE_PRODUCTION_DOMAIN}")

log "✅ Deployed to: ${DEPLOY_URL}"

# Verification
log "🔍 Step 3: Verifying deployment..."
sleep 3  # Give Cloudflare a moment to process

VERIFY_OUTPUT=$(npx wrangler pages deployment list \
    --project-name="${CLOUDFLARE_PROJECT_NAME}" \
    2>&1 | head -20 || echo "")

if echo "$VERIFY_OUTPUT" | grep -q "ACTIVE\|Success"; then
    log "✅ Deployment verified as ACTIVE"
else
    log "⚠️  Warning: Could not verify ACTIVE status"
    log "   Check manually: npx wrangler pages deployment list --project-name ${CLOUDFLARE_PROJECT_NAME}"
fi

# Create summary JSON
log "📝 Creating deployment summary..."

cat > "${LOGS_DIR}/latest.json" << EOF
{
  "date": "${DATE}",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "build_duration_seconds": ${BUILD_DURATION},
  "bundle_size_mb": ${BUNDLE_SIZE_MB},
  "deploy_url": "${DEPLOY_URL}",
  "status": "success"
}
EOF

log "✅ Static site publish complete!"
log "📊 Summary: ${LOGS_DIR}/latest.json"
log "🌐 Visit: ${DEPLOY_URL}"
