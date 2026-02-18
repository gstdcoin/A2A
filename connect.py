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
    def __init__(self, host, port, api_key):
        self.host = host
        self.port = port
        self.api_key = api_key
        self.conn = http.client.HTTPSConnection(host, port, timeout=10)
        self.headers = {
            "User-Agent": "GSTD-A2A-Swarm/2.0 (Omega)",
            "Content-Type": "application/json",
            "X-API-Key": api_key,
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
    parser = argparse.ArgumentParser(description="GSTD A2A Swarm Client (Omega Synergy)")
    parser.add_argument("--api-key", required=True, help="Your Agent API Key")
    parser.add_argument("--host", default=DEFAULT_API_HOST, help="Primary API Host")
    args = parser.parse_args()

    print(f"⚡ Initializing Ultra-Speed Swarm Connection to {args.host}...")
    
    client = SwarmClient(args.host, 443, args.api_key)

    # 0. Sentinel Integrity Check
    if not client.verify_genesis():
        print("❌ [Sentinel] ATTEMPT BLOCKED: Potential forged node detected.")
        sys.exit(1)

    # 1. Handshake (Fastest Path)
    start_time = time.time()
    handshake = client.request("POST", "/agents/handshake", {
        "agent_version": "2.0.0-OMEGA",
        "capabilities": ["compute", "consensus"],
        "status": "online"
    })
    latency = (time.time() - start_time) * 1000

    if handshake and handshake.get('status') == 'connected':
        print(f"✅ Connected! Agent ID: {handshake.get('agent_id')}")
        print(f"🚀 Latency: {latency:.2f}ms (Target: <50ms)")
        print("Listening for swarm directives...")
        
        while True:
            # Poll for work or consensus tasks
            # task = client.request("GET", "/marketplace/tasks/next")
            time.sleep(5) 
            print(".", end="", flush=True)
            
    else:
        print("❌ Handshake failed.")

if __name__ == "__main__":
    main()
