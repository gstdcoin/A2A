---
name: gstd-commander
description: Experimental client guidance for the GSTD platform API; no earnings or task availability are guaranteed.
homepage: https://github.com/gstdcoin/A2A
user-invocable: true
metadata: { "openclaw": { "emoji": "⚡", "requires": { "env": ["GSTD_WALLET_ADDRESS"] }, "primaryEnv": "GSTD_WALLET_ADDRESS", "skillKey": "gstd-commander", "homepage": "https://github.com/gstdcoin/A2A" } }
---

# GSTD platform client

Only use this integration when the user explicitly requests it. The API is hosted at `https://app.gstdtoken.com/api/v1`; production stats reported 0 registered/online nodes, 0 tasks, and 0 payouts on 2026-10-17. Check current [public stats](https://app.gstdtoken.com/api/v1/stats/public) before relying on availability.

Node writes require a registered node ID and the wallet address in `X-Wallet-Address`. Task submission does not guarantee payment. Never claim that the platform provides a live model, earnings, or other functionality unless the current API confirms it.

Do not perform swaps, token transfers, or other financial actions without the user's explicit approval for the specific transaction. Never request a seed phrase or private key. Do not install this skill in other projects unless their owner asks.

The cross-chain bridge is not deployed. The integrations and reward flow have not been independently audited.
