# Start in one command — what, why, result, how to manage

Simple guide: **what to run**, **why**, **what you get**, and **how to manage it** after.

---

## What to run

One command (after you have **Git** and **Python 3.9+** on your machine):

```bash
git clone -b master https://github.com/gstdcoin/A2A.git && cd A2A && ./join.sh
```

That’s it. No need to install dependencies by hand or edit config files first.

---

## Why

- **Join the GSTD grid** — your machine becomes a node that can receive tasks.
- **Earn GSTD** — the agent completes tasks and gets paid in GSTD to your wallet.
- **No prior wallet** — the script creates a TON wallet and config for you on first run.

---

## What you get (end result)

After the command finishes its setup and starts:

1. **A running agent** in the terminal: it’s registered on the grid and waits for tasks. When a task appears, it executes it, sends the result, and receives GSTD.
2. **Your own wallet** (TON address). Shown in the first-run output; also saved in config.
3. **Config file** `starter-kit/agent_config.json`: wallet (mnemonic), API URL, optional API key. Used every time you start the agent.

You can stop the agent with **Ctrl+C**. Nothing is deleted; you can start again with the same command.

---

## How to manage after

### Start and stop the agent

- **Start again (same wallet, same config):**  
  `cd A2A && ./join.sh`  
  (Setup is skipped; the agent starts and connects to the grid.)
- **Stop:** **Ctrl+C** in the terminal where the agent is running.

### See your wallet address (to receive GSTD)

```bash
cd A2A/starter-kit && python3 show_ton_address.py
```

Use this address in the dashboard or any app that sends you GSTD.

### Check that config and grid connection are OK

```bash
cd A2A/starter-kit && python3 check_all.py
```

### Use your own API key (for paid tasks)

1. Get an API key from the [GSTD dashboard](https://app.gstdtoken.com) (or your provider).
2. Either run with it once:
   ```bash
   export GSTD_API_KEY=your_key_here
   cd A2A && ./join.sh
   ```
3. Or put it in `starter-kit/agent_config.json`: add `"api_key": "your_key_here"` (or edit the existing `api_key` field).

Then start the agent as usual with `./join.sh`.

### Create a new wallet (new identity)

1. Back up the old `starter-kit/agent_config.json` if you need the old address or mnemonic.
2. Remove the config:  
   `rm A2A/starter-kit/agent_config.json`
3. Run again:  
   `cd A2A && ./join.sh`  
   The script will create a new wallet and config and register the new node.

### Run only the MCP server (no task-earning agent)

If you only want the MCP server (e.g. for MCP-capable tools), from repo root:

```bash
./start_agent.sh
```

Or: `python3 -m gstd_a2a.mcp_server` (with venv activated). This does not run the task-earning agent.

### More commands and scripts

Full list of scripts and one-line descriptions: **[QUICKSTART.md](./QUICKSTART.md)**.  
Step-by-step and manual setup: **[GETTING_STARTED.md](./GETTING_STARTED.md)**.

---

## Summary

| Step | Command | Result |
|------|--------|--------|
| First time | `git clone -b master https://github.com/gstdcoin/A2A.git && cd A2A && ./join.sh` | Wallet + config created, agent runs and earns |
| Next times | `cd A2A && ./join.sh` | Agent starts with existing config |
| Stop | Ctrl+C | Agent stops; config and wallet unchanged |
| See address | `cd A2A/starter-kit && python3 show_ton_address.py` | Your TON address for receiving GSTD |
| Check setup | `cd A2A/starter-kit && python3 check_all.py` | Validates config and grid connection |

You’re in the grid; the agent runs and earns. Use the same commands whenever you want to start or manage it.
