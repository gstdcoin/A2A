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
    
    # helper: prefer config key, then env var
    auth_key = config.get('api_key') or os.getenv("GSTD_API_KEY")
    client = GSTDClient(api_url=config['api_url'], wallet_address=config['wallet_address'], api_key=auth_key)

    print(f"🤖 Agent Active: {config['wallet_address'][:10]}...")
    
    # 1. Self-Discovery
    print("🔍 Discovering peers...")
    agents = client.discover_agents(capability="text-processing")
    print(f"🌐 Found {len(agents)} active peers.")

    # 2. Main Loop
    try:
        while True:
            print("📡 Polling for tasks...")
            tasks = client.get_pending_tasks()
            
            if tasks:
                for task in tasks:
                    print(f"🎯 Found Task: {task.get('task_type')} - {task.get('task_id')}")
                    
                    # Logic: Simple Echo/Processing
                    raw_payload = task.get('payload', "{}")
                    if isinstance(raw_payload, str):
                        try:
                            payload = json.loads(raw_payload)
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
