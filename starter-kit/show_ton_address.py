import sys
import json
import os
import argparse
from pathlib import Path

# Add SDK path
sys.path.append(str(Path(__file__).parent.parent / "python-sdk"))

from gstd_a2a.gstd_wallet import GSTDWallet

def main():
    parser = argparse.ArgumentParser(description="Show TON Wallet Address formats")
    parser.add_argument("--update", action="store_true", help="Update agent_config.json with the mainnet non-bounceable address")
    args = parser.parse_args()

    config_path = Path("agent_config.json")
    if not config_path.exists():
        print("❌ Error: agent_config.json not found. Run setup_agent.py first.")
        return

    with open(config_path, "r") as f:
        config = json.load(f)

    mnemonic = config.get("mnemonic")
    if not mnemonic:
        print("❌ Error: Mnemonic not found in config.")
        return

    # Initialize Wallet
    wallet = GSTDWallet(mnemonic=mnemonic)
    
    # Generate Formats
    # tonsdk address to_string(is_user_friendly, is_url_safe, is_bounceable, is_test_only)
    # But GSTDWallet.address is a string. We need the underlying object or re-parse.
    # Accessing internal wallet object from SDK if available, or just using tonsdk directly here?
    # GSTDWallet exposes self.wallet.address
    
    raw_addr = wallet.wallet.address
    
    # 1. Mainnet Bounceable (EQ...) - Standard for deployed contracts
    addr_bounceable = raw_addr.to_string(True, True, True)
    
    # 2. Mainnet Non-Bounceable (UQ...) - REQUIRED for funding new wallets (Exchange -> Wallet)
    # If a wallet is not deployed, bounceable transfer bounces back.
    addr_non_bounceable = raw_addr.to_string(True, True, False)

    print("\n💎 TON Wallet Address Formats")
    print("----------------------------")
    print(f"✅ Mainnet Non-Bounceable (For Funding/Exchanges): \n   👉 {addr_non_bounceable}\n")
    print(f"ℹ️  Mainnet Bounceable (For Contracts/Apps): \n   {addr_bounceable}\n")
    
    print(f"🔑 Current Config Address: {config.get('wallet_address')}")

    if args.update:
        if config.get("wallet_address") != addr_non_bounceable:
            print("\n🔄 Updating agent_config.json to use Non-Bounceable address...")
            config["wallet_address"] = addr_non_bounceable
            # Also save bounceable version for reference
            config["address_bounceable"] = addr_bounceable
            
            with open(config_path, "w") as f:
                json.dump(config, f, indent=4)
            print("✅ Config updated.")
        else:
            print("\n✅ Config already uses Non-Bounceable address.")

if __name__ == "__main__":
    main()
