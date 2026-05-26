"""
GSTD A2A — Zero-dependency single-file connector.
Uses only Python stdlib. Works with Python 3.7+.

Usage:
    # Register a new agent:
    python3 connect.py --wallet YOUR_TON_WALLET --name MyAgent

    # Run with existing API key:
    python3 connect.py --api-key gstd_agent_xxx

    # Or via env vars:
    GSTD_API_KEY=gstd_agent_xxx python3 connect.py
"""
import argparse
import sys
import json
import time
import os

try:
    import urllib.request
    from urllib.error import URLError, HTTPError
except ImportError:
    print("Critical Error: Core libraries missing.")
    sys.exit(1)

BASE_URL = os.getenv("GSTD_API_URL", "https://app.gstdtoken.com").rstrip("/")
POLL_INTERVAL = int(os.getenv("GSTD_POLL_INTERVAL", "5"))
HEARTBEAT_INTERVAL = int(os.getenv("GSTD_HEARTBEAT_INTERVAL", "30"))


def api_request(path, method="GET", data=None, api_key=None):
    headers = {
        "User-Agent": "GSTD-A2A-Connector/2.0",
        "Content-Type": "application/json",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(f"{BASE_URL}{path}", data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except HTTPError as e:
        raw = e.read().decode()
        try:
            return json.loads(raw)
        except Exception:
            return {"error": f"HTTP {e.code}: {raw[:200]}"}
    except URLError as e:
        return {"error": str(e)}


def register(wallet, name, capabilities=None):
    """Register a new agent and return the API key."""
    payload = {
        "wallet_address": wallet,
        "agent_name": name or "A2A-Agent",
        "agent_type": "a2a-sdk",
        "capabilities": capabilities or ["text-processing", "data-validation"],
    }
    result = api_request("/api/v1/nodes/register", method="POST", data=payload)
    return result


def heartbeat(api_key, node_id=None):
    payload = {"node_id": node_id, "status": "working", "timestamp": time.time()}
    api_request("/api/v1/nodes/heartbeat", method="POST", data=payload, api_key=api_key)


def get_tasks(api_key):
    result = api_request("/api/v1/tasks/worker/pending", api_key=api_key)
    if isinstance(result, list):
        return result
    if isinstance(result, dict):
        return result.get("tasks", [])
    return []


def submit_result(api_key, task_id, node_id, output):
    payload = {"task_id": task_id, "node_id": node_id, "result": output}
    return api_request("/api/v1/tasks/worker/submit", method="POST", data=payload, api_key=api_key)


def run_loop(api_key, node_id, verbose=True):
    last_heartbeat = 0
    while True:
        now = time.time()

        # Heartbeat
        if now - last_heartbeat >= HEARTBEAT_INTERVAL:
            heartbeat(api_key, node_id)
            last_heartbeat = time.time()
            if verbose:
                print(f"[{time.strftime('%H:%M:%S')}] 📡 Heartbeat sent", flush=True)

        # Poll tasks
        tasks = get_tasks(api_key)
        if tasks:
            for task in tasks:
                task_id = task.get("task_id") or task.get("id", "")
                task_type = task.get("type") or task.get("task_type", "unknown")
                reward = task.get("reward_gstd") or task.get("budget", 0)
                if verbose:
                    print(f"[{time.strftime('%H:%M:%S')}] ⚡ Task {task_id[:8]}... ({task_type}) reward={reward} GSTD")

                # Default handler: acknowledge and complete
                result = {
                    "status": "completed",
                    "processed_by": node_id,
                    "task_type": task_type,
                }
                resp = submit_result(api_key, task_id, node_id, result)
                if verbose:
                    print(f"[{time.strftime('%H:%M:%S')}] ✅ Submitted: {resp}")
        else:
            print(".", end="", flush=True)

        time.sleep(POLL_INTERVAL)


def main():
    parser = argparse.ArgumentParser(
        description="GSTD A2A Connector — zero-dependency agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Register and run:   python3 connect.py --wallet EQxxx --name MyBot
  Run with key:       python3 connect.py --api-key gstd_agent_xxx
  Env vars:           GSTD_API_KEY=xxx python3 connect.py
        """,
    )
    parser.add_argument("--api-key", default=os.getenv("GSTD_API_KEY"), help="Agent API key (gstd_agent_xxx)")
    parser.add_argument("--wallet", default=os.getenv("GSTD_WALLET_ADDRESS"), help="TON wallet address (for registration)")
    parser.add_argument("--name", default="A2A-Agent", help="Agent name")
    parser.add_argument("--quiet", action="store_true", help="Suppress verbose output")
    args = parser.parse_args()

    verbose = not args.quiet
    api_key = args.api_key
    node_id = None

    if not api_key:
        if not args.wallet:
            print("❌ Provide --api-key gstd_agent_xxx OR --wallet YOUR_TON_WALLET")
            print("   Get a wallet at https://app.gstdtoken.com or use any TON wallet")
            sys.exit(1)

        print(f"🔐 Registering agent '{args.name}'...")
        result = register(args.wallet, args.name)
        if "error" in result:
            print(f"❌ Registration failed: {result['error']}")
            sys.exit(1)

        api_key = result.get("api_key")
        node_id = result.get("node_id") or result.get("id") or result.get("agent_id")
        print(f"✅ Registered! API Key: {api_key}")
        print(f"   Node ID: {node_id}")
        print(f"   Save your key — set GSTD_API_KEY={api_key}")
    else:
        node_id = api_key  # Use key as node identity fallback

    print(f"🚀 Starting agent loop | Server: {BASE_URL}")
    print(f"   Poll: {POLL_INTERVAL}s | Heartbeat: {HEARTBEAT_INTERVAL}s")
    print("   Press Ctrl+C to stop\n")

    try:
        run_loop(api_key, node_id, verbose=verbose)
    except KeyboardInterrupt:
        print("\n👋 Agent stopped.")


if __name__ == "__main__":
    main()
