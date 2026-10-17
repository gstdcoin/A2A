---
name: gstd-sovereign
description: Experimental GSTD SDK orchestration; may access a wallet and perform network or financial actions.
homepage: https://github.com/gstdcoin/A2A
user-invocable: true
metadata: { "openclaw": { "emoji": "🏛️", "requires": { "env": ["GSTD_WALLET_ADDRESS"], "anyBins": ["python3", "python"] }, "primaryEnv": "GSTD_WALLET_ADDRESS", "os": ["linux", "darwin"], "homepage": "https://github.com/gstdcoin/A2A", "skillKey": "gstd-sovereign" } }
---

# Experimental GSTD autonomy SDK

This SDK is not a passive status monitor. Its autonomy engine includes wallet, task, and network-growth operations; inspect its configuration and implementation before running it. Current production stats reported 0 registered/online nodes, 0 tasks, and 0 payouts on 2026-10-17. Earnings and task availability are not guaranteed.

Only activate it when the user explicitly requests this integration. Obtain separate confirmation before any transfer, swap, paid operation, or change to another project. Never request or provide seed phrases or private keys.

```python
from gstd_a2a.sovereign_autonomy import SovereignAgent

# Review configuration and side effects before calling activate().
agent = SovereignAgent()
```

The platform API is `https://app.gstdtoken.com/api/v1`. The cross-chain bridge is not deployed, and these integrations and the reward flow have not been independently audited.
