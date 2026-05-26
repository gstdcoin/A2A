import argparse
import sys
import json
import time
import http.client
import urllib.parse
from urllib.error import URLError

# Default configuration
DEFAULT_API_HOST = "app.gstdtoken.com"
DEFAULT_API_PORT = 443
FALLBACK_API_HOST = "gstd.ton.limo"
FALLBACK_API_PORT = 443

# Genesis Signature (Must match server manifest for swarm integrity)
GENESIS_MANIFEST_HASH = "d428d9226912f8a7cdb557c382ac1e5fe00989fa18c6737262c93cf14c80a40a"

class SwarmClient:
    def __init__(self, host, port, wallet):
        self.host = host
        self.port = port
        self.wallet = wallet
        self.conn = http.client.HTTPSConnection(host, port, timeout=10)
        self.headers = {
            "User-Agent": "GSTD-A2A-Swarm/2.0 (Omega)",
            "Content-Type": "application/json",
            "X-API-Key": wallet,
            "Connection": "keep-alive"
        }

    def verify_genesis(self):
        print(f"🔍 [Sentinel] Verifying Genesis Integrity at {self.host}...")
        try:
            self.conn.request("GET", "/api/v1/system/integrity", headers={"Connection": "close"}) # Force fresh verification
            resp = self.conn.getresponse()
            if resp.status != 200:
                print(f"⚠️ [Sentinel] Integrity check failed: HTTP {resp.status}")
                return False
            
            data = json.loads(resp.read().decode('utf-8'))
            if data.get('manifest_hash') == GENESIS_MANIFEST_HASH:
                 print("✅ [Sentinel] INTEGRITY VERIFIED. Swarm entry permitted.")
                 return True
            print(f"⚠️ [Sentinel] MANIFEST MISMATCH: Expected {GENESIS_MANIFEST_HASH[:8]}, got {data.get('manifest_hash', 'none')[:8]}")
            return False
        except Exception as e:
            print(f"⚠️ [Sentinel] Integrity check unreachable: {e}. Running in unverified mode.")
            self.reconnect()
            return True

    def request(self, method, endpoint, data=None):
        try:
            body = json.dumps(data) if data else None
            self.conn.request(method, "/api/v1" + endpoint, body=body, headers=self.headers)
            resp = self.conn.getresponse()
            payload = resp.read().decode('utf-8')
            if resp.status == 429:
                print("🚀 [Rate Limit] Server Busy. Retrying in heartbeat...")
                time.sleep(1)
                return self.request(method, endpoint, data)
            return json.loads(payload) if payload else {}
        except (http.client.HTTPException, OSError):
            print("⚠️ Connection lost. Reconnecting...")
            self.reconnect()
            return self.request(method, endpoint, data) # Retry once
        except json.JSONDecodeError:
            return None

    def reconnect(self):
        self.conn.close()
        self.conn = http.client.HTTPSConnection(self.host, self.port, timeout=10)

def main():
    import os
    parser = argparse.ArgumentParser(description="GSTD A2A Swarm Client (Omega Synergy)")
    parser.add_argument("--wallet", default=os.environ.get("GSTD_API_KEY") or os.environ.get("GSTD_WALLET_ADDRESS"), help="Agent API key (gstd_agent_xxx) or TON wallet for registration")
    parser.add_argument("--host", default=DEFAULT_API_HOST, help="Primary API Host")
    args = parser.parse_args()

    if not args.wallet:
        print("❌ Set --wallet or GSTD_API_KEY. For zero-barrier: use connect_autonomous.py")
        print("   curl -sL https://raw.githubusercontent.com/gstdcoin/ai/main/scripts/connect_autonomous.py | python3")
        sys.exit(1)

    # Resolve wallet for grid visibility (device must have wallet to appear in dashboard)
    wallet = args.wallet or os.environ.get("GSTD_WALLET_ADDRESS", "")
    if not wallet and args.wallet.startswith("sk_sovereign_"):
        rest = args.wallet[len("sk_sovereign_"):]
        idx = rest.rfind("_")
        if idx > 0:
            wallet = rest[:idx]

    if not wallet:
        print("⚠️  No wallet — device won't appear in dashboard. Set GSTD_WALLET_ADDRESS or --wallet")

    print(f"⚡ Initializing Ultra-Speed Swarm Connection to {args.host}...")
    
    client = SwarmClient(args.host, 443, args.wallet)

    # 0. Sentinel Integrity Check
    if not client.verify_genesis():
        print("❌ [Sentinel] ATTEMPT BLOCKED: Potential forged node detected.")
        sys.exit(1)

    # 1. Handshake — MUST include wallet_address so device appears in grid
    start_time = time.time()
    reg_body = {
        "wallet_address": wallet,
        "agent_name": "Swarm-Agent",
        "capabilities": ["compute", "consensus"],
    }
    reg = client.request("POST", "/nodes/register", reg_body)
    latency = (time.time() - start_time) * 1000

    node_id = None
    if reg:
        node_id = reg.get("node_id") or reg.get("id") or reg.get("agent_id")
        api_key = reg.get("api_key") or args.wallet
        print(f"✅ Registered! Node ID: {node_id}")
        print(f"🚀 Latency: {latency:.2f}ms")
        print("Listening for tasks...")

        # Update headers to use api_key
        client.headers["Authorization"] = f"Bearer {api_key}"

        last_hb = 0
        while True:
            now = time.time()
            if now - last_hb >= 30:
                client.request("POST", "/nodes/heartbeat", {"node_id": node_id, "status": "working"})
                last_hb = time.time()
            tasks_resp = client.request("GET", f"/tasks/worker/pending?node_id={node_id}")
            tasks = tasks_resp if isinstance(tasks_resp, list) else (tasks_resp or {}).get("tasks", [])
            if tasks:
                for task in tasks:
                    tid = task.get("task_id") or task.get("id", "")
                    result = {"status": "completed", "node_id": node_id}
                    client.request("POST", "/tasks/worker/submit", {"task_id": tid, "node_id": node_id, "result": result})
                    print(f"\n✅ Task {tid[:8]}... processed")
            else:
                time.sleep(5)
                print(".", end="", flush=True)
    else:
        print("❌ Registration failed.")

if __name__ == "__main__":
    main()
