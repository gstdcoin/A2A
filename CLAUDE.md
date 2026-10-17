# GSTD A2A SDK — Development Guide

## Stack

- **Language:** Python
- **Core package:** `src/gstd_a2a/`
- **Platform API:** `https://app.gstdtoken.com/api/v1/`
- **Node API identity:** public TON wallet address in the `X-Wallet-Address` header

This SDK and its integrations are experimental. The production platform currently reports no registered nodes, tasks, or payouts; check the live stats before relying on work availability.

## Install and test

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## Relevant API endpoints

| Action | Endpoint |
|--------|----------|
| Register node | `POST /api/v1/nodes/register` |
| Heartbeat | `POST /api/v1/nodes/heartbeat` |
| Poll task | `GET /api/v1/tasks/worker/pending?node_id={node_id}` |
| Submit result | `POST /api/v1/tasks/worker/submit` |
| Health check | `GET /api/v1/health` |

Task submission does not guarantee an on-chain payout.

## Key files

- `src/gstd_a2a/gstd_client.py` — low-level HTTP client
- `src/gstd_a2a/agent.py` — experimental agent loop
- `src/gstd_a2a/protocols.py` — task payload validation
- `src/gstd_a2a/security.py` — input filtering; not a substitute for cryptographic verification
- `tools/main.py` — MCP server
- `connect.py` / `connect.js` — minimal registration, heartbeat, and task-monitor examples; they do not execute tasks

## Publishing to PyPI

```bash
pip install build twine
python -m build
twine upload dist/*
```

CI publishes on version-tag pushes. Never commit API credentials, wallet private keys, or seed phrases.
