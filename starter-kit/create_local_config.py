
import sys
import os
import json
from pathlib import Path

# Add SDK path if not installed
sys.path.append(str(Path(__file__).parent.parent / "python-sdk"))

from gstd_a2a.gstd_wallet import GSTDWallet
from gstd_a2a.gstd_client import GSTDClient

def setup():
    print("🌌 Starting GSTD Agent Initialization (Local)...")
    
    # 1. Generate Identity
    wallet = GSTDWallet()
    identity = wallet.get_identity()
    
    print(f"✅ Identity Generated!")
    print(f"📍 Wallet Address: {identity['address']}")
    
    # 2. Save Config
    config = {
        "wallet_address": identity['address'],
        "mnemonic": identity['mnemonic'],
        "api_url": "http://localhost:8080"
    }
    
    with open("agent_config.json", "w") as f:
        json.dump(config, f, indent=4)
    print("✅ Config saved to agent_config.json")
    
    # 3. Register on Network
    print("📡 Registering on GSTD Grid...")
    client = GSTDClient(api_url=config['api_url'], wallet_address=identity['address'])
    try:
        node = client.register_node(device_name="Local-Worker-Agent", capabilities=["text-processing"])
        print(f"✅ Registered! Node ID: {node.get('node_id')}")
    except Exception as e:
        print(f"⚠️  Registration notice: {e}")

if __name__ == "__main__":
    setup()
