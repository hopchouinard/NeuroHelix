#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

cd "$REPO_ROOT/orchestrator"

if command -v poetry >/dev/null 2>&1; then
  poetry run pytest
else
  python3 -m pytest
fi
