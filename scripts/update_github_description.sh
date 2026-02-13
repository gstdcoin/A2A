#!/bin/bash
# Update GitHub repo description and topics for gstdcoin/A2A
# Requires: GITHUB_TOKEN or GH_TOKEN env var with repo scope
# Usage: GITHUB_TOKEN=ghp_xxx ./scripts/update_github_description.sh

TOKEN="${GITHUB_TOKEN:-$GH_TOKEN}"
if [ -z "$TOKEN" ]; then
  echo "Set GITHUB_TOKEN or GH_TOKEN with repo scope"
  exit 1
fi

curl -s -X PATCH \
  -H "Authorization: token $TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/gstdcoin/A2A \
  -d '{
    "description": "Decentralized Agent-to-Agent protocol for the GSTD Grid. MCP, OpenAI-compatible, Hive Memory, TON.",
    "homepage": "https://app.gstdtoken.com",
    "topics": ["gstd", "a2a", "mcp", "ton", "agents", "ai", "blockchain"]
  }' | jq -r '.description // .message'
