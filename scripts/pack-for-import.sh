#!/bin/bash
# Create A2A archive for import (OpenClaw, MCP) — NO SECRETS
set -e
cd "$(dirname "$0")/.."
OUT="dist"
mkdir -p "$OUT"
ARCHIVE="$OUT/gstd-a2a-import-$(date +%Y%m%d).tar.gz"

echo "Packing A2A for import (no secrets)..."

# Build file list (exclude agent_config.json - has secrets)
FILES="main.py setup.py requirements.txt README.md SKILL.md VERSION_PIN.md LICENSE python-sdk starter-kit/agent_config.json.example Dockerfile examples .gitignore"
[ -f CONTRIBUTING.md ] && FILES="$FILES CONTRIBUTING.md"

# Pack
tar czf "$ARCHIVE" \
  --exclude='.git' --exclude='.env' --exclude='venv' --exclude='__pycache__' \
  --exclude='dist' --exclude='*.pyc' --exclude='*.egg-info' --exclude='.eggs' \
  --exclude='starter-kit/agent_config.json' \
  $FILES

echo "Created: $ARCHIVE"
ls -lh "$ARCHIVE"
