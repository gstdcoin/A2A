#!/bin/bash
# GSTD A2A Node Launcher
# Usage: ./run-node.sh [API_KEY]  or  GSTD_AGENT_KEY=xxx ./run-node.sh

set -e
cd "$(dirname "$0")"

API_KEY="${1:-$GSTD_AGENT_KEY}"
if [ -z "$API_KEY" ]; then
  echo "❌ Agent API Key required."
  echo ""
  echo "Usage:"
  echo "  ./run-node.sh <YOUR_AGENT_KEY>"
  echo "  GSTD_AGENT_KEY=<key> ./run-node.sh"
  echo ""
  echo "Get your key at: https://app.gstdtoken.com"
  exit 1
fi

# Prefer Node.js if available, else Python
if command -v node &>/dev/null; then
  echo "📦 Starting A2A node (Node.js)..."
  exec node connect.js "$API_KEY"
elif command -v python3 &>/dev/null; then
  echo "🐍 Starting A2A node (Python)..."
  exec python3 connect.py --api-key "$API_KEY"
else
  echo "❌ Need Node.js or Python 3 to run the node."
  exit 1
fi
