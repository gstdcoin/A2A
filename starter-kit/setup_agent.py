import sys
import os
import json
from pathlib import Path

# Add SDK path if not installed
sys.path.append(str(Path(__file__).parent.parent / "python-sdk"))

from gstd_a2a.gstd_wallet import GSTDWallet
from gstd_a2a.gstd_client import GSTDClient

def setup():
    print("🌌 Starting GSTD Agent Initialization...")
    
    # 1. Generate Identity
    wallet = GSTDWallet()
    identity = wallet.get_identity()
    
    # Get Non-Bounceable Address (UQ...) for funding
    # Accessing internal wallet object from tonsdk wrapper
    non_bounceable_address = wallet.wallet.address.to_string(True, True, False)
    
    print(f"✅ Identity Generated!")
    print(f"📍 Mainnet Address (Fund this): {non_bounceable_address}")
    print(f"🔑 Mnemonic: {identity['mnemonic']}")
    # 2. Configure API Access
    api_key = os.getenv("GSTD_API_KEY")
    if not api_key:
        print("\n🔑 GSTD API Key is required for paid tasks (leave blank for Free Tier / Read-Only).")
        api_key = input("Submit your API Key: ").strip()
    
    # 3. Save Config
    config = {
        "wallet_address": non_bounceable_address,
        "address_bounceable": identity['address'],
        "mnemonic": identity['mnemonic'],
        "api_url": "https://app.gstdtoken.com",
        "api_key": api_key if api_key else None
    }
    
    with open("agent_config.json", "w") as f:
        json.dump(config, f, indent=4)
    print("✅ Config saved to agent_config.json")
    
    # Register on Network
    print("📡 Registering on GSTD Grid...")
    # Use key from config (support both names), fallback to env, then Public Key
    client_key = config.get('gstd_api_key') or config.get('api_key') or os.getenv("GSTD_API_KEY") or "gstd_system_key_2026"
    client = GSTDClient(api_url=config['api_url'], wallet_address=identity['address'], api_key=client_key)
    try:
        # In a real scenario, this would register the node
        node = client.register_node(device_name="My-First-Agent", capabilities=["text-processing", "logic"])
        print(f"✅ Registered! Node ID: {node.get('node_id')}")
        print("✅ Registration complete! (Ready for tasks)")
    except Exception as e:
        print(f"⚠️  Registration notice: {e}")

    print("\n🚀 Setup Complete! You can now run 'python demo_agent.py'")

if __name__ == "__main__":
    setup()
