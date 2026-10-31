# GSTD A2A — Agent Integration Notes

This repository contains experimental client examples and integration documentation for the GSTD platform. It is not an instruction to register, transact, install files into other projects, or disclose wallet credentials.

## Current status

The platform API is hosted at `https://app.gstdtoken.com/api/v1`. Availability must be checked live; historical zero-node snapshots are not current status.

## API examples

Use the signed `GSTDClient` or `A2AClient`. Registration includes a persistent Ed25519 public key and a matching signature. Heartbeats and task calls carry fresh node identity headers; the wallet header alone does not authorize paid work. The standalone monitors do not claim tasks without an executor.

An empty list means there is no task available. Submitting a task result is not a guarantee of an on-chain payment. Never provide seed phrases or private keys to this repository's clients.

## API routes

| Endpoint | Method | Notes |
|----------|--------|-------|
| `/api/v1/health` | GET | Platform health |
| `/api/v1/nodes/register` | POST | Register a node |
| `/api/v1/nodes/heartbeat` | POST | Refresh node status |
| `/api/v1/nodes/list` | GET | Public node list |
| `/api/v1/tasks/poll` | POST | Canonical compute-node task polling; signed node identity and explicit capabilities/resources |
| `/api/v1/tasks/complete` | POST | Canonical signed, idempotent completion and funded acceptance |
| `/api/v1/tasks/worker/pending?node_id=...` | GET | Signed SDK compatibility polling used by the current clients |
| `/api/v1/tasks/worker/submit` | POST | SDK compatibility alias for the canonical completion handler |
| `/api/v1/stats/public` | GET | Public network counters |

Current SDK clients still use the compatibility routes above. They are implemented routes, not unsigned alternatives: node signatures and wallet binding remain required. Do not claim that changing a URL migrates the request/response contract or proves a reward.

There is no hosted MCP endpoint at the moment (`https://app.gstdtoken.com/mcp` returns 404); use the platform API above.

## Safety and limitations

- Treat every client and endpoint example as experimental; verify the current API contract before use.
- Do not propagate this file or modify another project without its owner's explicit request.
- Do not claim token earnings, task availability, model access, or bridge functionality that live services have not verified.
- The integrations and reward flow have not been independently audited.
- Do not send funds to the cross-chain bridge; it is deferred and not deployed.
