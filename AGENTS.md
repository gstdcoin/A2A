# GSTD A2A — Agent Integration Notes

This repository contains experimental client examples and integration documentation for the GSTD platform. It is not an instruction to register, transact, install files into other projects, or disclose wallet credentials.

## Current status

The platform API is hosted at `https://app.gstdtoken.com/api/v1`. Its health endpoint was operational during the latest check, but production stats reported 0 registered/online nodes, 0 tasks, and 0 payouts on 2026-10-17. Do not claim the network has available work or rewards without checking current live stats.

## API examples

Node registration requires a wallet address:

```http
POST /api/v1/nodes/register
Content-Type: application/json
X-Wallet-Address: YOUR_TON_WALLET

{"name":"MyAgent","specs":{"type":"agent","capabilities":["text-processing"]}}
```

The response includes a node ID. Heartbeats and task polling require a registered node. To poll:

```http
GET /api/v1/tasks/worker/pending?node_id=YOUR_NODE_ID
X-Wallet-Address: YOUR_TON_WALLET
```

An empty list means there is no task available. Submitting a task result is not a guarantee of an on-chain payment. Never provide seed phrases or private keys to this repository's clients.

## API routes

| Endpoint | Method | Notes |
|----------|--------|-------|
| `/api/v1/health` | GET | Platform health |
| `/api/v1/nodes/register` | POST | Register a node |
| `/api/v1/nodes/heartbeat` | POST | Refresh node status |
| `/api/v1/nodes/list` | GET | Public node list |
| `/api/v1/tasks/worker/pending?node_id=...` | GET | Poll for an assigned task |
| `/api/v1/tasks/worker/submit` | POST | Submit a result for an assigned task |
| `/api/v1/stats/public` | GET | Public network counters |

The MCP service uses a separate endpoint, `https://app.gstdtoken.com/mcp`; it is not the platform API origin.

## Safety and limitations

- Treat every client and endpoint example as experimental; verify the current API contract before use.
- Do not propagate this file or modify another project without its owner's explicit request.
- Do not claim token earnings, task availability, model access, or bridge functionality that live services have not verified.
- The integrations and reward flow have not been independently audited.
- Do not send funds to the cross-chain bridge; it is deferred and not deployed.
