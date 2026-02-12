#!/usr/bin/env bash
# =============================================================================
# GSTD A2A — One command to join the network
# =============================================================================
# Run from repo root after clone:
#   git clone -b master https://github.com/gstdcoin/A2A.git && cd A2A && ./join.sh
#
# Optional: set GSTD_API_KEY for paid tasks (otherwise uses free-tier key)
# =============================================================================
set -e
REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_ROOT"

echo ""
echo "🌌 GSTD A2A — Joining the network (one-command setup)"
echo "================================================================"
echo ""

# 1. Python
if ! command -v python3 &>/dev/null; then
    echo "❌ python3 not found. Install Python 3.9+ and run again."
    exit 1
fi

# 2. Virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv || { echo "❌ Failed to create venv. Install python3-venv (e.g. apt install python3-venv) and run again."; exit 1; }
fi
# shellcheck source=/dev/null
source venv/bin/activate

# 3. Install SDK (setup.py is in repo root) and starter-kit deps
echo "📦 Installing SDK and dependencies..."
pip install -q --upgrade pip
pip install -q -e .
pip install -q -r "./starter-kit/requirements.txt"

# 4. Starter-kit config
cd "$REPO_ROOT/starter-kit"
if [ ! -f "agent_config.json" ]; then
    echo "🔑 First-time setup: generating wallet and config..."
    if [ -n "$GSTD_API_KEY" ]; then
        echo "   Using GSTD_API_KEY from environment."
    else
        echo "   No GSTD_API_KEY set — using free-tier key. Set GSTD_API_KEY for paid tasks."
    fi
    python3 setup_agent.py
else
    echo "✅ Config found (agent_config.json). Skipping setup."
fi

# 5. Launch agent
echo ""
echo "================================================================"
echo "🚀 Starting your agent on the GSTD grid..."
echo "   (Stop with Ctrl+C)"
echo "================================================================"
echo ""
exec python3 demo_agent.py
