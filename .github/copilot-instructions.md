# GSTD A2A repository guidance

This repository contains experimental clients and integration examples for the GSTD platform API. The platform API is `https://app.gstdtoken.com/api/v1`; the separate MCP endpoint is `https://app.gstdtoken.com/mcp`.

Production stats reported 0 registered/online nodes, 0 tasks, and 0 payouts on 2026-10-17. Do not claim task availability, earnings, inference access, or on-chain settlement without current verification.

## API conventions

- Wallet-bound operations use the `X-Wallet-Address` header.
- Task polling requires a registered `node_id` and matching wallet address.
- Never submit placeholder results or imply that submitting a result causes an on-chain payout.
- Never request, store, or transmit seed phrases or private keys.
- Do not install or propagate instructions into other projects without their owner's explicit request.

The integrations and reward flow have not been independently audited. The cross-chain bridge is deferred and not deployed.
