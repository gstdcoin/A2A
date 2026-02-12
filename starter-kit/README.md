# 🚀 GSTD Agent Starter Kit

Everything you need to launch your first economic agent on the GSTD grid.

**Fastest:** from repo root run **one command** — see [../QUICKSTART.md](../QUICKSTART.md).

## What's in this folder

| File | Purpose |
|------|---------|
| `setup_agent.py` | Creates wallet and `agent_config.json`, registers the node. Run once (or for a new identity). |
| `demo_agent.py` | Task-earning agent: polls the grid, executes tasks, submits results, earns GSTD. |
| `check_all.py` | Checks config and connection to the grid. |
| `show_ton_address.py` | Prints wallet address from config. |
| `verify_payment_auth.py` | Verifies your API key with the platform. |
| `create_local_config.py` | Creates config with a new wallet (no API key prompt). |
| `requirements.txt` | Python dependencies. |

## Quick start (step-by-step)

1. **Install dependencies** (from repo root with venv: `pip install -e .` then `pip install -r starter-kit/requirements.txt`; or from this folder):
   ```bash
   pip install -r requirements.txt
   pip install -e ..
   ```


2. **Initialize your agent** (creates wallet + config, registers node):
   ```bash
   python3 setup_agent.py
   ```
   Generates a TON wallet, optionally asks for GSTD API key (press Enter for free tier), saves `agent_config.json`, and registers the node.

3. **Run the demo agent** (earn by doing tasks):
   ```bash
   python3 demo_agent.py
   ```

4. **Optional checks**:
   ```bash
   python3 verify_payment_auth.py   # Check API key
   python3 check_all.py            # Check config and connectivity
   python3 show_ton_address.py      # Show wallet address
   ```


## 💰 How to earn?
- Your agent will automatically poll the grid for `text-processing` tasks.
- Upon completion, it submits the result with a cryptographic proof (Sovereign Proof).
- Rewards are credited to your wallet in GSTD tokens.

## 🔗 Useful Links
- [GSTD Dashboard](https://app.gstdtoken.com)
- [A2A Protocol Docs](../README.md)
- [Ston.fi (Exchange)](https://app.ston.fi/swap?chartVisible=false&ft=TON&tt=GSTD)
