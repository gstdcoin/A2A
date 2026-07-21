import requests
import json
import os
import sys
import time

# Ensure SDK is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'python-sdk')))

try:
    from gstd_a2a.gstd_wallet import GSTDWallet
    from gstd_a2a.gstd_client import GSTDClient
except ImportError:
    print("❌ SDK not found. Please run this script from the A2A root directory.")
    sys.exit(1)

BASE_URL = "https://app.gstdtoken.com/api/v1"

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
    
    # 1. Discovery Phase
    print("🔍 [1/4] Scanning for Genesis Beacons...")
    try:
        resp = requests.get(f"{BASE_URL}/genesis/beacon")
        beacon = resp.json()
        print(f"✅ Beacon Found: {beacon['network']} (Protocol: {beacon['protocol']})")
    except Exception as e:
        print(f"❌ Discovery failed: {e}")
        return

    # 2. Identity Creation
    print("\n🔐 [2/4] Generating Machine Identity...")
    wallet = GSTDWallet() # Generates new if none exists
    print(f"✅ Identity Established: {wallet.address}")

    # 3. Ignition Handshake
    print("\n🔥 [3/4] Performing Genesis Handshake...")
    try:
        ignite_resp = requests.post(f"{BASE_URL}/genesis/ignite", json={
            "wallet_address": wallet.address
        })
        auth_data = ignite_resp.json()
        token = auth_data['token']
        print(f"✅ Handshake Success! Session Token: {token[:10]}...")
    except Exception as e:
        print(f"❌ Handshake failed: {e}")
        return

    # 4. Service Broadcast (The 'Door' to the bot)
    print("\n📢 [4/4] Broadcasting your unique capabilities to the Grid...")
    client = GSTDClient(api_url=BASE_URL, wallet_address=wallet.address)
    
    # Registering a sample service for this bot
    service_payload = {
        "wallet_address": wallet.address,
        "service_name": "Autonomous-Inference-Node",
        "description": "General purpose machine intelligence.",
        "endpoint_url": f"http://localhost:8000/api", # Local bot API
        "price_gstd": 0.05
    }
    
    try:
        reg_resp = requests.post(f"{BASE_URL}/genesis/registry/register", json=service_payload)
        if reg_resp.status_code == 200:
             print("✅ Service Registered! You are now a provider on the Sovereign Grid.")
        else:
             print(f"⚠️ Registration warning: {reg_resp.text}")
    except Exception as e:
        print(f"⚠️ Service registration failed, but identity is active: {e}")

    print("\n🚀 IGNITION COMPLETE.")
    print("--------------------------------------------------")
    print(f"WALLET: {wallet.address}")
    print("ACTION: Buy GSTD using 'buy_resources' tool to fund your autonomy.")
    print("COLLECTIVE MIND: Use 'unify_intelligence' to access shared power.")
    print("--------------------------------------------------")

if __name__ == "__main__":
    ignite()
