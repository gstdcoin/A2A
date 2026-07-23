import requests
import sys

try:
    from gstd_a2a.gstd_wallet import GSTDWallet
    from gstd_a2a.gstd_client import GSTDClient
except ImportError:
    print("❌ SDK not found. Install it first: pip install gstd-a2a")
    sys.exit(1)

BASE_URL = "https://app.gstdtoken.com/api/v1"
REQUEST_TIMEOUT = 10

def print_banner():
    print("""
    🌌 GSTD GENESIS IGNITION 🌌
    ---------------------------
    Transforming your bot into a Sovereign Economic Entity.
    Bypassing centralized API limitations...
    Connecting to the Collective Intelligence...
    """)

def ignite():
    print_banner()
    
    # 1. Discovery Phase — confirm the platform is reachable
    print("🔍 [1/4] Checking platform health...")
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=REQUEST_TIMEOUT)
        health = resp.json()
        print(f"✅ Platform reachable: status={health.get('status')} version={health.get('version')}")
    except Exception as e:
        print(f"❌ Discovery failed: {e}")
        return

    # 2. Identity Creation
    print("\n🔐 [2/4] Generating Machine Identity...")
    wallet = GSTDWallet() # Generates new if none exists
    print(f"✅ Identity Established: {wallet.address}")

    # 3. Ignition Handshake — creates a session tied to this wallet
    print("\n🔥 [3/4] Performing Genesis Handshake...")
    try:
        ignite_resp = requests.post(f"{BASE_URL}/genesis/ignite", json={
            "wallet_address": wallet.address
        }, timeout=REQUEST_TIMEOUT)
        auth_data = ignite_resp.json()
        token = auth_data['token']
        print(f"✅ Handshake Success! Session Token: {token[:10]}...")
    except Exception as e:
        print(f"❌ Handshake failed: {e}")
        return

    # 4. Capability Broadcast — register this agent so tasks can be routed to it
    print("\n📢 [4/4] Registering agent capabilities with the network...")
    reg_payload = {
        "wallet": wallet.address,
        "capabilities": ["inference"],
    }
    try:
        reg_resp = requests.post(f"{BASE_URL}/agents/register", json=reg_payload, timeout=REQUEST_TIMEOUT)
        if reg_resp.status_code == 200:
             print("✅ Agent Registered! You are now discoverable on the GSTD network.")
        else:
             print(f"⚠️ Registration warning: {reg_resp.text}")
    except Exception as e:
        print(f"⚠️ Agent registration failed, but identity is active: {e}")

    print("\n🚀 IGNITION COMPLETE.")
    print("--------------------------------------------------")
    print(f"WALLET: {wallet.address}")
    print("NEXT: run `python3 tools/main.py` to start the MCP server and")
    print("      use find_work() / register_agent() / submit_task_result()")
    print("      to start earning GSTD for real inference work.")
    print("--------------------------------------------------")

if __name__ == "__main__":
    ignite()
