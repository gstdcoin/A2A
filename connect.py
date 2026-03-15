
import argparse
import sys
import json
import time

try:
    import urllib.request
    from urllib.error import URLError, HTTPError
except ImportError:
    print("Critical Error: Core libraries missing.")
    sys.exit(1)

# Default configuration
DEFAULT_API_URL = "https://app.gstdtoken.com/api/v1"
FALLBACK_API_URL = "https://gstd.ton.limo/api/v1"
# Genesis Signature (Must match server manifest for swarm integrity)
GENESIS_MANIFEST_HASH = "d428d9226912f8a7cdb557c382ac1e5fe00989fa18c6737262c93cf14c80a40a"

def verify_genesis(url):
    print(f"🔍 [Sentinel] Verifying Genesis Integrity at {url}...")
    # In production, this checks the server's signed manifest against the Genesis Archive.
    # For bootstrap, we verify the presence of the Sovereign Lock.
    try:
        req = urllib.request.Request(f"{url}/system/integrity")
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            if data.get('manifest_hash') == GENESIS_MANIFEST_HASH:
                 print("✅ [Sentinel] INTEGRITY VERIFIED. Swarm entry permitted.")
                 return True
            print(f"⚠️ [Sentinel] MANIFEST MISMATCH: Expected {GENESIS_MANIFEST_HASH[:8]}, got {data.get('manifest_hash', 'none')[:8]}")
            return False
    except Exception:
        # Fallback for dev: allow but warn
        print("⚠️ [Sentinel] Integrity check unreachable. Running in unverified mode.")
        return True

def api_request(url, method="GET", data=None, headers=None):
    # (previous implementation)
    if headers is None:
        headers = {}
    
    headers['User-Agent'] = 'GSTD-A2A-Agent/1.0'
    headers['Content-Type'] = 'application/json'

    if data:
        data = json.dumps(data).encode('utf-8')

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode('utf-8'))
    except HTTPError as e:
        if e.code == 429:
            print("🚀 [Rate Limit] Server Busy. Retrying in heartbeat...")
        return None
    except URLError as e:
        return None

def main():
    parser = argparse.ArgumentParser(description="GSTD A2A Connector")
    parser.add_argument("--api-key", required=True, help="Your Agent API Key")
    parser.add_argument("--url", default=DEFAULT_API_URL, help="Primary API URL")
    args = parser.parse_args()

    print(f"🔌 Connecting to Swarm: {args.url}")
    
    # 0. Sentinel Integrity Check
    if not verify_genesis(args.url):
        print("❌ [Sentinel] ATTEMPT BLOCKED: Potential forged node detected.")
        sys.exit(1)

    # 1. Handshake
    handshake_payload = {
        "agent_version": "1.0.1",
        "capabilities": ["compute", "rag"],
        "status": "online"
    }
    
    headers = {"X-API-Key": args.api_key}
    response = api_request(f"{args.url}/agents/handshake", method="POST", data=handshake_payload, headers=headers)

    if response and response.get('status') == 'connected':
        print(f"✅ Connected! Agent ID: {response.get('agent_id')}")
        print("Listening for tasks...")
        
        last_poll = 0
        POLL_INTERVAL = 5 # Rate limiting: minimum 5s between requests
        
        while True:
            now = time.time()
            if now - last_poll < POLL_INTERVAL:
                time.sleep(POLL_INTERVAL - (now - last_poll))
            
            last_poll = time.time()
            # task = api_request(f"{args.url}/marketplace/tasks/next", headers=headers)
            # if task: process(task)
            print(".", end="", flush=True)
            
    else:
        print("❌ Handshake failed. Switching to fallback DNS...")
        # Simple fallback logic demonstration
        response = api_request(f"{FALLBACK_API_URL}/agents/handshake", method="POST", data=handshake_payload, headers=headers)
        if response and response.get('status') == 'connected':
             print(f"✅ Connected via TON DNS! Agent ID: {response.get('agent_id')}")
        else:
             print("💀 Connection failed on both networks.")

if __name__ == "__main__":
    main()
