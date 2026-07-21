import os
import sys
import json
from pathlib import Path

# Add SDK path
sys.path.append(str(Path(__file__).parent.parent / "python-sdk"))
from gstd_a2a.gstd_client import GSTDClient
from gstd_a2a.gstd_wallet import GSTDWallet

def check_all():
    print("🕵️  GSTD Agent Diagnostic Tool\n" + "="*30)
    
    # --- STEP 1: Config ---
    print("\n[1/4] Checking Configuration...")
    config_path = Path(__file__).parent / "agent_config.json"
    if not config_path.exists():
        print("❌ FAILED: agent_config.json not found.")
        print("   👉 Run 'python setup_agent.py' first.")
        return
    
    with open(config_path) as f:
        config = json.load(f)
    print("✅ Config found.")

    # --- STEP 2: Wallet & Balance ---
    print("\n[2/4] Checking Wallet & Balances...")
    mnemonic = config.get("mnemonic")
    if not mnemonic:
        print("❌ FAILED: Mnemonic key missing in config.")
        return
    
    try:
        wallet = GSTDWallet(mnemonic=mnemonic)
        print(f"   Address: {wallet.address}")
        
        # Check Balances
        print("   Querying blockchain...")
        balances = wallet.check_balance()
        
        ton = balances.get("TON", 0)
        gstd = balances.get("GSTD", 0)
        
        print(f"   💰 TON Balance:  {ton} TON")
        print(f"   💎 GSTD Balance: {gstd} GSTD")
        
        if "error" in balances:
            print(f"   ⚠️  Warning: {balances['error']}")
            
        print("✅ Wallet initialized.")
    except Exception as e:
        print(f"❌ FAILED: Wallet error: {e}")
        return

    # --- STEP 3: API Key ---
    print("\n[3/4] Checking API Key...")
    # Logic: Config 'gstd_api_key' > Config 'api_key' > Env 'GSTD_API_KEY'
    api_key = config.get("gstd_api_key") or config.get("api_key") or os.getenv("GSTD_API_KEY")
    
    if api_key:
         mask_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "***"
         print(f"✅ API Key found: {mask_key}")
    else:
         print("❌ FAILED: No API Key found.")
         print("   👉 Add 'gstd_api_key': 'YOUR_KEY' to agent_config.json")
         print("   👉 or set GSTD_API_KEY environment variable.")
         # We continue to Auth check to show it failing explicitly
    
    # --- STEP 4: Authorization Verify ---
    print("\n[4/4] Verifying Grid Authorization...")
    if not api_key:
        print("⏭️  Skipping Auth check (No key).")
        print("\n❌ DIAGNOSTICS FAILED: Missing API Key.")
        return

    client = GSTDClient(api_key=api_key, wallet_address=wallet.address)
    try:
        print("   Sending test request (get_balance)...")
        balance = client.get_balance()
        print("✅ AUTHORIZATION SUCCESS!")
        print(f"   Platform balance: {balance.get('balance_gstd')} GSTD | "
              f"Free requests remaining today: {balance.get('free_requests_remaining')}")
        status = "PASSED"
    except Exception as e:
        err_str = str(e)
        if "401" in err_str:
             print("❌ FAILED: 401 Unauthorized.")
             print("   👉 Your API Key is invalid or expired.")
             status = "FAILED"
        else:
             print(f"❌ FAILED: Server returned error: {err_str}")
             status = "FAILED"

    print("\n" + "="*30)
    print(f"🏁 DIAGNOSTIC RESULT: {status}")
    if status.startswith("PASSED"):
        print("🚀 You are ready to run 'python demo_agent.py'")

if __name__ == "__main__":
    check_all()
