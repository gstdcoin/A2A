
import sys
import os
import time

# Ensure we can import the local SDK
sys.path.append(os.path.abspath("python-sdk"))

try:
    from gstd_a2a import GSTDClient, GSTDWallet
    print("✅ SDK Import Successful")
except ImportError as e:
    print(f"❌ SDK Import Failed: {e}")
    sys.exit(1)

def test_system():
    print("\n--- 🔍 Starting A2A Protocol Verification ---")
    
    # 1. Wallet Generation
    print("\n1️⃣  Testing Wallet Generation...")
    try:
        wallet = GSTDWallet(mnemonic=None) # Generate new
        identity = wallet.get_identity()
        print(f"   ✅ Wallet Generated: {identity['address']}")
        print(f"   🔑 Mnemonic Word Count: {len(identity['mnemonic'].split())}")
    except Exception as e:
        print(f"   ❌ Wallet Error: {e}")
        return

    # 2. Client Initialization
    print("\n2️⃣  Testing API Client Connection...")
    client = GSTDClient(wallet_address=wallet.address)
    
    # 3. Health Check
    print("   📡 Pinging Grid Health...")
    health = client.health_check()
    if health.get("status") == "healthy" or "boinc" in health:
        print(f"   ✅ Grid Connection Established: {health}")
    else:
        print(f"   ⚠️  Grid Health Warning: {health}")

    # 4. Task Logic (Simulation)
    print("\n3️⃣  Verifying Task Protocols...")
    try:
        tasks = client.get_pending_tasks()
        print(f"   ✅ Pending Tasks Fetch: Success (Found {len(tasks)} tasks)")
    except Exception as e:
        print(f"   ❌ Task Fetch Error: {e}")

    # 5. Check MCP Server Import
    print("\n4️⃣  Verifying MCP Server Integrity...")
    try:
        from mcp.server.fastmcp import FastMCP
        print("   ✅ MCP Library Installed")
        # We won't run the server, just ensure imports work
        from gstd_a2a import mcp_server
        print("   ✅ MCP Server Code Compiles/Imports Correctly")
    except ImportError as e:
        print(f"   ❌ MCP Import Error: {e}")
    except Exception as e:
        print(f"   ❌ MCP Code Error: {e}")

    print("\n--- 🏁 Verification Complete ---")

if __name__ == "__main__":
    test_system()
