"""Zero-dependency GSTD platform connector.

This client registers a node, sends heartbeats, and displays assigned tasks.
It intentionally does not submit placeholder results or claim rewards.
"""
import argparse
import json
import os
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def api_base_url():
    value = os.getenv("GSTD_API_URL", "https://app.gstdtoken.com").rstrip("/")
    if not value.endswith("/api/v1"):
        value += "/api/v1"
    return value


BASE_URL = api_base_url()
POLL_INTERVAL = max(5, int(os.getenv("GSTD_POLL_INTERVAL", "10")))
HEARTBEAT_INTERVAL = max(30, int(os.getenv("GSTD_HEARTBEAT_INTERVAL", "180")))


def api_request(path, method="GET", data=None, wallet_address=None):
    headers = {
        "User-Agent": "GSTD-A2A-Connector/2.1",
        "Content-Type": "application/json",
    }
    if wallet_address:
        headers["X-Wallet-Address"] = wallet_address

    body = json.dumps(data).encode("utf-8") if data is not None else None
    request = Request(f"{BASE_URL}{path}", data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=15) as response:
            payload = response.read().decode("utf-8")
    except HTTPError as error:
        payload = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"API returned HTTP {error.code}: {payload[:300]}") from error
    except URLError as error:
        raise RuntimeError(f"Could not reach GSTD API: {error.reason}") from error

    try:
        return json.loads(payload)
    except json.JSONDecodeError as error:
        raise RuntimeError("GSTD API returned invalid JSON") from error


def register(wallet_address, name):
    return api_request(
        "/nodes/register",
        method="POST",
        data={
            "name": name,
            "specs": {
                "type": "agent",
                "capabilities": ["text-processing", "data-validation"],
            },
        },
        wallet_address=wallet_address,
    )


def heartbeat(wallet_address, node_id):
    return api_request(
        "/nodes/heartbeat",
        method="POST",
        data={"node_id": node_id, "wallet_address": wallet_address, "status": "active"},
        wallet_address=wallet_address,
    )


def get_tasks(wallet_address, node_id):
    query = urlencode({"node_id": node_id})
    result = api_request(
        f"/tasks/worker/pending?{query}",
        wallet_address=wallet_address,
    )
    if not isinstance(result, dict) or not isinstance(result.get("tasks"), list):
        raise RuntimeError("GSTD API returned an unexpected task-list response")
    return result["tasks"]


def run_loop(wallet_address, node_id):
    last_heartbeat = 0
    while True:
        now = time.time()
        try:
            if now - last_heartbeat >= HEARTBEAT_INTERVAL:
                heartbeat(wallet_address, node_id)
                last_heartbeat = time.time()
                print("Heartbeat sent.", flush=True)

            for task in get_tasks(wallet_address, node_id):
                task_id = str(task.get("task_id") or task.get("id") or "unknown")
                print(
                    f"Task {task_id} assigned. No task executor is configured; "
                    "the client will not submit a placeholder result.",
                    flush=True,
                )
        except RuntimeError as error:
            print(f"GSTD API error: {error}", file=sys.stderr, flush=True)

        time.sleep(POLL_INTERVAL)


def main():
    parser = argparse.ArgumentParser(
        description="Register and monitor a GSTD node using its public wallet address."
    )
    parser.add_argument(
        "--wallet",
        default=os.getenv("GSTD_WALLET_ADDRESS"),
        help="TON wallet address (public address only; never a seed phrase or private key)",
    )
    parser.add_argument("--name", default="A2A-Agent", help="Node display name")
    args = parser.parse_args()

    if not args.wallet:
        parser.error("provide --wallet or set GSTD_WALLET_ADDRESS")

    print(f"Registering {args.name} with {BASE_URL}...")
    try:
        result = register(args.wallet, args.name)
        node_id = result.get("node_id") if isinstance(result, dict) else None
        if not node_id:
            raise RuntimeError(f"Registration response did not include node_id: {result}")
    except RuntimeError as error:
        parser.exit(1, f"Registration failed: {error}\n")

    print(f"Registered node {node_id}. Press Ctrl+C to stop.")
    try:
        run_loop(args.wallet, node_id)
    except KeyboardInterrupt:
        print("\nNode monitor stopped.")


if __name__ == "__main__":
    main()
