#!/usr/bin/env bash
set -euo pipefail
# Bootstrap local
export UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}"
uv sync --all-extras
echo "✓ .venv prêt — lance : source .venv/bin/activate  ou  uv run meta-ai-dev"
