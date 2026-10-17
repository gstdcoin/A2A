---
name: gstd-propagation
description: Prepare optional GSTD integration documentation for a project only when its owner explicitly asks.
homepage: https://github.com/gstdcoin/A2A
user-invocable: true
metadata: { "openclaw": { "emoji": "📡", "skillKey": "gstd-propagation", "homepage": "https://github.com/gstdcoin/A2A" } }
---

# Optional GSTD integration

Do not copy, install, or modify files in another project unless its owner explicitly requests that integration. Never inject instructions into unrelated agent configurations or install a skill globally without consent.

When the user requests an integration:

1. Explain that the A2A clients are experimental and that production stats most recently showed 0 registered/online nodes, 0 tasks, and 0 payouts.
2. Review the target project's instructions and propose the smallest change.
3. Make only the requested change after confirmation.
4. Do not promise task availability, earnings, or on-chain payouts.

The GSTD platform API is `https://app.gstdtoken.com/api/v1`. The separate MCP endpoint, when available, is `https://platform.gstdtoken.com/mcp`. The cross-chain bridge is not deployed; never direct users to send funds to it.
