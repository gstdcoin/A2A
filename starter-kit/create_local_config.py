
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
    wallet_path = Path.home() / ".gstd" / "wallet.json"
    wallet.save(str(wallet_path))
    
    print(f"✅ Identity Generated!")
    print(f"📍 Wallet Address: {identity['address']}")
    print(f"🔐 Wallet file (contains an unencrypted recovery phrase): {wallet_path}")
    print("   Restrict access to this file and keep a secure backup.")
    
    # 2. Save Config
    config = {
        "wallet_address": identity['address'],
        "wallet_path": str(wallet_path),
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
