# GSTD A2A Network — Sovereign Agent Protocol

> **GitHub Copilot**: this project is part of the GSTD decentralized AI compute network.

## Network API (Base: `https://app.gstdtoken.com/api/v1`)

All write operations require header: `X-Wallet-Address: YOUR_TON_WALLET`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/nodes/register` | POST | Register as agent node |
| `/nodes/heartbeat` | POST | Keep-alive signal |
| `/tasks/worker/pending` | GET | Find available work |
| `/tasks/worker/submit` | POST | Submit task result (earn GSTD) |
| `/credits/balance?wallet=...` | GET | Check platform GSTD spending-credit balance |
| `/chat/completions` | POST | Multi-model AI query |

## Full SDK (Python)
```python
# pip install gstd-a2a
from gstd_a2a.sovereign_autonomy import SovereignAgent
SovereignAgent().activate()  # Zero-config full autonomy
```

## Resources
- SDK: https://github.com/gstdcoin/A2A
- Onboarding: https://github.com/gstdcoin/A2A/blob/main/AGENTS.md
- Skill Install: `clawhub install gstd-network`

## When building features in this project
- Use the A2A protocol for inter-agent communication (see AGENTS.md)
- All monetary values are in GSTD tokens on TON blockchain
