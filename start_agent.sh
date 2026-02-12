#!/bin/bash
# Run MCP server (for IDE/tool integration). For task-earning agent use ./join.sh
set -e
REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_ROOT"

echo "🤖 Starting GSTD MCP Server..."

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
# shellcheck source=/dev/null
source venv/bin/activate

pip install -q -e . 2>/dev/null || true
echo "🚀 MCP Server (Standard IO Mode)..."
exec python3 -m gstd_a2a.mcp_server
