#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

WALLET_ADDRESS="${1:-${GSTD_WALLET_ADDRESS:-}}"
if [[ -z "$WALLET_ADDRESS" ]]; then
  echo "A public TON wallet address is required." >&2
  echo "Usage: ./scripts/run-node.sh YOUR_TON_WALLET" >&2
  echo "Or set GSTD_WALLET_ADDRESS." >&2
  exit 1
fi

if command -v node >/dev/null 2>&1; then
  exec node connect.js "$WALLET_ADDRESS"
elif command -v python3 >/dev/null 2>&1; then
  exec python3 connect.py --wallet "$WALLET_ADDRESS"
else
  echo "Node.js 18+ or Python 3 is required." >&2
  exit 1
fi
