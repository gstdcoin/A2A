import os
import sys
import json
from pathlib import Path

# Add SDK path
sys.path.append(str(Path(__file__).parent.parent / "python-sdk"))
from gstd_a2a.gstd_client import GSTDClient

def verify_auth():
    print("🔐 Verifying GSTD API Authorization...")

    # 1. Get API Key strategy: Env Var -> Config File
    api_key = os.getenv("GSTD_API_KEY")
    
    config_path = Path(__file__).parent / "agent_config.json"
    wallet_address = "UQ_DEMO_WALLET_ADDRESS_FOR_TEST" 

    if config_path.exists():
        with open(config_path) as f:
            cfg = json.load(f)
            wallet_address = cfg.get("wallet_address", wallet_address)
            # If env var missing, try config (support both naming conventions)
            if not api_key:
                api_key = cfg.get("gstd_api_key") or cfg.get("api_key")

    if not api_key:
        print("❌ Error: GSTD_API_KEY not found in environment or agent_config.json.")
        print("   Run: python setup_agent.py (to save in config)")
        print("   OR: export GSTD_API_KEY='your_key'")
        return
    
    print(f"👤 Wallet: {wallet_address}")
    print(f"🔑 API Key: {api_key[:4]}****{api_key[-4:] if len(api_key)>8 else '****'}")

    # 3. Test Authenticated Request
    client = GSTDClient(api_key=api_key, wallet_address=wallet_address)

    try:
        print("📡 Sending authenticated request (get_balance)...")
        balance = client.get_balance()

        print("\n✅ AUTHORIZATION SUCCESS!")
        print(f"   Balance: {balance.get('balance_gstd')} GSTD")
        print(f"   Free requests remaining today: {balance.get('free_requests_remaining')}")
        print("   The server accepted the Authorization header.")

    except Exception as e:
        print("\n❌ AUTHORIZATION/REQUEST FAILED")
        print(f"   Error: {e}")
        if "401" in str(e):
            print("   👉 Cause: Invalid API Key. Check your key on gstdtoken.com")

if __name__ == "__main__":
    verify_auth()
