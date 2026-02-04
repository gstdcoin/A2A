import sys
import os
import json
import time
from pathlib import Path

# Add SDK path
sys.path.append(str(Path(__file__).parent.parent / "python-sdk"))

from gstd_a2a.gstd_client import GSTDClient
from gstd_a2a.gstd_wallet import GSTDWallet

def run_agent():
    # Load config
    if not Path("agent_config.json").exists():
        print("❌ Error: agent_config.json not found. Run setup_agent.py first.")
        return

    with open("agent_config.json", "r") as f:
        config = json.load(f)

    # Initialize Client & Wallet
    wallet = GSTDWallet(mnemonic=config['mnemonic'])
    
    # helper: prefer config key (support both names), then env var, then Public Key
    auth_key = config.get('gstd_api_key') or config.get('api_key') or os.getenv("GSTD_API_KEY") or "gstd_system_key_2026"
    client = GSTDClient(api_url=config['api_url'], wallet_address=config['wallet_address'], api_key=auth_key)

    print(f"🤖 Agent Active: {config['wallet_address'][:10]}...")
    
    # 1. Self-Discovery
    print(f"📡 Connected to GSTD Grid: {config['api_url']}")
    
    # 1. Register as worker node (REQUIRED to receive tasks)
    print("📝 Registering node on the grid...")
    try:
        reg_info = client.register_node(device_name="Demo-Agent", capabilities=["text-processing", "logic"])
        client.node_id = reg_info.get("node_id") or reg_info.get("id") or client.wallet_address
        print(f"✅ Registered successfully! Node ID: {client.node_id}")
    except Exception as e:
        print(f"⚠️  Registration warning: {e}")
        print("   (Attempting to proceed with wallet address as identity...)")
        client.node_id = wallet.address

    # 2. Discover Peers
    peers = client.discover_agents()
    print(f"👥 Found {len(peers)} active peers.")
    
    print("\n🚀 Agent is running! WAITING FOR TASKS...")
    print("(Press Ctrl+C to stop)\n")

    # 2. Main Loop
    try:
        while True:
            # Poll for tasks
            tasks = client.get_pending_tasks()
            
                        except:
                            payload = {}
                    else:
                        payload = raw_payload or {}
                        
                    text = payload.get('text', "")
                    
                    print(f"⚙️  Processing: {text[:30]}...")
                    result = {"processed_text": text.upper(), "status": "success"}
                    
                    # Submit Result with Sovereign Proof
                    print("🔒 Generating Sovereign Proof and Submitting...")
                    res = client.submit_result(task['task_id'], result, wallet=wallet)
                    print(f"DEBUG: Submit Result Response: {res}")
                    print(f"💰 Reward Claimed! Status: {res.get('status')}")
            else:
                print("💤 No tasks available. Sleeping for 10s...")
            
            time.sleep(10)
            
    except KeyboardInterrupt:
        print("\n🛑 Agent shutting down.")

if __name__ == "__main__":
    run_agent()
