# GSTD client integration boundaries

The current production API is `https://app.gstdtoken.com/api/v1`. The [GSTD compute node](https://github.com/gstdcoin/gstdbot) is the supported route for operators who want to execute model inference. This repository contains experimental signed clients and integrations; registration alone is not compute execution or a reward.

## Identity and work

Use `GSTDClient` (Python) or `A2AClient` (JavaScript) with a persistent Ed25519 identity. Registration binds the node public key; heartbeat and assigned-task requests carry fresh signatures. A wallet address or API key alone does not authorize arbitrary worker results.

- `GET /health`: platform health.
- `GET /nodes/list`: registered nodes and current availability.
- `POST /nodes/register`, `POST /nodes/heartbeat`: signed node participation.
- `GET /tasks/worker/pending?node_id=...`: work assigned to that signed node.
- `POST /tasks/worker/submit`: an actual computed result for assigned work.
- `POST /chat/completions`: model inference; explicit model IDs are not replaced by different families. Paid requests need verified wallet authorization and an idempotency key.

The monitor CLIs do not claim tasks without an executor. An empty queue is normal. An accepted API response does not prove an on-chain payout. See [economics](ECONOMICS.md), [signed-client instructions](../AGENTS.md) and [platform API documentation](https://gstdtoken.com/developers).

## MCP and central dependencies

`tools/main.py` contains an experimental local MCP integration. It is not a hosted platform MCP service, a verified paid executor or an instruction to share wallet credentials. The platform `/mcp` endpoint is not deployed. Review local tools before granting them access to a wallet.

The platform registry, accounting and custody owner remain central dependencies. No zero-knowledge proof of inference correctness, permissionless peer marketplace or unstoppable multi-machine deployment is claimed. [Historical Hive Mesh notes](archive/PROTOCOL_2026-10-28.md) are retained as history.
