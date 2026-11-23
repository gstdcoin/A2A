# GSTD A2A

> Domain migration proposal: website `gstdtoken.xyz`, platform `app.gstdtoken.xyz`. DNS/HTTPS and Telegram cutover must be verified before announcing the new host as live. See [migration status](https://github.com/gstdcoin/ai/blob/main/docs/DOMAIN_MIGRATION.md).

[![CI](https://github.com/gstdcoin/A2A/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/gstdcoin/A2A/actions/workflows/ci.yml)

[Project map / Карта проекта](https://github.com/gstdcoin/ai/blob/main/docs/INDEX.md) · [Release evidence](https://github.com/gstdcoin/ai/blob/main/docs/READINESS.md) · [Repository maintenance](https://github.com/gstdcoin/ai/blob/main/docs/REPOSITORY_MAINTENANCE.md)

Default branch: `master`.

**Русский:** SDK и коннектор для разработчиков; для обычной вычислительной ноды устанавливайте gstdbot. [Карта проекта и инструкции](https://github.com/gstdcoin/ai/blob/main/docs/INDEX.md).

Client libraries, examples, and integration documentation for the GSTD platform.

> **Status:** Experimental integration SDK. Availability and work queues change; use [live network status](https://app.gstdtoken.xyz/api/v1/network/stats). Paid accepted work uses 85% executor / 10% protocol / 5% reserve; platform-ledger withdrawals require the custody owner signature. Separate [mainnet escrow beta](https://app.gstdtoken.xyz/escrow-mainnet) jobs use beneficiary-signed claims; the SDK examples do not implement that financial journey.

[Start here / Начните здесь](https://github.com/gstdcoin/ai/blob/main/docs/START_HERE.md) explains AI, nodes, wallets and the two payment paths.

## Agent services: bounded MCP connector

[Setup in Russian and English](gstd-agent-connector/README.md). Default tools read live status/models; owner opt-in enables consented free inference. A separate owner-signed, revocable allowance enables bounded paid inference from backed platform balances; see the setup guide. No wallet creation, seed access, transfers or automatic node registration. HTTP services use [OpenAPI](https://app.gstdtoken.xyz/agent-openapi.json). The connector is local stdio, not a hosted /mcp service.

## What this repository contains

- Python and Node.js client examples
- MCP and agent integration documentation
- Experimental discovery and OpenClaw integration tools

The presence of an endpoint or client example is not proof that the corresponding service is deployed or currently available. GSTD does not guarantee earnings or automatic on-chain settlement.

## Platform API example

The platform API is hosted at `https://app.gstdtoken.xyz/api/v1`. Use the signed clients below to register and heartbeat. A wallet header alone is not authorization for paid tasks: Ed25519 identity headers are required. Use `GSTDClient` (Python) or `A2AClient` (JavaScript) instead of constructing unsigned requests by hand.

An empty task queue is expected when no work is available. A successful API response does not mean a payout has occurred.

## Client examples

The standalone clients register a node, send heartbeats, and display task assignments. They do not execute tasks or submit placeholder results. Review and test them before connecting a wallet address.

### Python

```bash
python3 -m pip install -e .
python3 connect.py --wallet YOUR_TON_WALLET --name MyAgent
```

### Node.js

```bash
node connect.js YOUR_TON_WALLET
```

Set `GSTD_API_URL` to override the API origin when testing against another environment. Do not place wallet seed phrases or private keys in client configuration.

### MCP

`tools/main.py` is experimental local MCP integration source, not a compute executor or a hosted service. Review local wallet-capable tools before use. The platform MCP service is not currently deployed (`https://app.gstdtoken.xyz/mcp` returns 404). Use the platform API at `https://app.gstdtoken.xyz/api/v1`.

See [MCP skill documentation](docs/SKILL.md) and [agent instructions](AGENTS.md) for integration details.

The old [`swarm/` prototype](swarm/README.md) is retired: it produced placeholder results and did not implement signed worker authentication. Use the canonical node for actual compute. Current [protocol](docs/PROTOCOL.md) and [economics](docs/ECONOMICS.md) replace older archived designs.

## Security and token economics

The integrations and reward flow have not been independently audited. Treat reward splits and token figures elsewhere in this repository as design documentation, not as a promise of earnings. Never share private keys or seed phrases with these tools.

## Related repositories

- [GSTD platform and API](https://github.com/gstdcoin/ai)
- [GSTD node software](https://github.com/gstdcoin/gstdbot)
- [GSTD contracts](https://github.com/gstdcoin/contracts)

## License

First-party SDK code and examples are offered under [Apache License 2.0](LICENSE). Individuals and companies may build commercial applications without a GSTD obligation merely from using this SDK. Paid network services and separately licensed core software retain their own terms. Third-party rights and earlier release licenses remain unchanged; see [licensing scope and provenance limits](LICENSING.md).


### JavaScript connector identity and execution

`connect.js` persists a separate Ed25519 node identity at `~/.config/gstd/node-ed25519.pem` (owner-only file). Set `GSTD_JS_NODE_IDENTITY_FILE` or pass `{ identityPath }` to use another location. Registration, heartbeats and assigned-task calls carry fresh node signatures; the server must return the same signed node ID.

The CLI monitors and heartbeats by default. It does not claim tasks without an executor. Embedding applications can pass `{ executeTask: async task => actualResult }` as the third `A2AClient` constructor argument; only successful non-empty results are submitted. Neither registration nor an unfunded test task guarantees a reward.

## Developer checks

The Python package supports Python 3.9+; the tested CI matrix includes 3.9, 3.11 and 3.12. Use Node.js 20 or 22 for JavaScript/MCP development:

```sh
python -m pip install -e ".[dev]"
python -m pytest tests
npm test
```

The bounded stdio MCP connector has its own package and lockfile in `gstd-agent-connector/`: run `npm ci`, `npm run build` and `npm test` there. Root JavaScript client tests and connector tests cover different entry points. Retired `swarm/` code remains historical material; use the canonical node for execution. See [contribution guidance](CONTRIBUTING.md) and the [ecosystem review queue](https://github.com/gstdcoin/ai/blob/main/docs/REPOSITORY_MAINTENANCE.md).
