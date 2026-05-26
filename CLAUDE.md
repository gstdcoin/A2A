# GSTD A2A SDK — Development Guide

## Stack
- **Language**: Python 3.9+
- **Core**: `src/gstd_a2a/` (pip package `gstd-a2a`)
- **Platform API**: `https://app.gstdtoken.com/api/v1/`
- **Auth**: `Authorization: Bearer {api_key}` + `X-Wallet-Address: {ton_address}`

## Install (development)
```bash
pip install -e ".[dev]"   # installs + dev deps (pytest, mypy, bandit)
pytest tests/ -v
```

## API Endpoints used by SDK
| Action | Endpoint |
|--------|----------|
| Register node | `POST /api/v1/nodes/register` |
| Heartbeat | `POST /api/v1/nodes/heartbeat` |
| Poll task | `GET /api/v1/tasks/worker/pending` |
| Submit result | `POST /api/v1/tasks/worker/submit` |
| Health check | `GET /api/v1/health` |

## Key files
- `src/gstd_a2a/gstd_client.py` — low-level HTTP client
- `src/gstd_a2a/agent.py` — zero-config autonomous agent loop
- `src/gstd_a2a/protocols.py` — task payload validation
- `src/gstd_a2a/security.py` — Ed25519 signatures
- `tools/main.py` — MCP server (run with `python3 tools/main.py`)
- `connect.py` / `connect.js` — zero-dependency connectors

## Quick start for an agent
```python
from gstd_a2a.agent import Agent
Agent.run()   # registers, finds tasks, earns GSTD
```

## Publishing to PyPI
```bash
pip install build twine
python -m build
twine upload dist/*   # requires PYPI_TOKEN secret
```
CI auto-publishes on `git tag v*` push.

## DO NOT
- Do not hardcode `https://app.gstdtoken.com` — use `GSTDClient(api_url=...)` param
- Do not commit `GSTD_API_KEY` or wallet private keys
