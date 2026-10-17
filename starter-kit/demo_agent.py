#!/usr/bin/env python3
"""
GSTD Network Demo Agent
========================
A fully autonomous agent that:
1. Self-registers on the GSTD grid
2. Discovers peers
3. Polls for and executes tasks
4. Submits results and claims rewards

This is the starter template for building your own AI agent on the GSTD network.
"""

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
    """Main agent loop - autonomous task execution"""
    
    # Load config
    config_path = Path("agent_config.json")
    if not config_path.exists():
        print("❌ Error: agent_config.json not found.")
        print("   Run: python setup_agent.py")
        return

    with open(config_path, "r") as f:
        config = json.load(f)

    # Load new private wallet files; accept legacy config phrases for migration.
    mnemonic = config.get('mnemonic')
    wallet_path = config.get('wallet_path') or os.getenv("GSTD_WALLET_PATH")
    if mnemonic:
        wallet = GSTDWallet(mnemonic=mnemonic)
    elif wallet_path and Path(wallet_path).expanduser().is_file():
        wallet = GSTDWallet.load(wallet_path)
    else:
        print("❌ Error: No wallet configured. Set wallet_path or GSTD_WALLET_PATH.")
        return
    
    # API Key priority: config -> env -> default
    auth_key = (
        config.get('gstd_api_key') or 
        config.get('api_key') or 
        os.getenv("GSTD_API_KEY") or 
        "gstd_system_key_2026"
    )
    
    client = GSTDClient(
        api_url=config['api_url'], 
        wallet_address=config['wallet_address'], 
        api_key=auth_key
    )

    print("🤖 ═══════════════════════════════════════")
    print(f"🤖 GSTD Agent Active: {config['wallet_address'][:10]}...")
    print(f"📡 Connected to Grid: {config['api_url']}")
    print("🤖 ═══════════════════════════════════════")
    
    # 1. Register as worker node (REQUIRED to receive tasks)
    print("\n📝 Registering node on the grid...")
    try:
        reg_info = client.register_node(
            device_name="Demo-Agent", 
            capabilities=["text-processing", "logic", "general-ai"]
        )
        client.node_id = reg_info.get("node_id") or reg_info.get("id") or client.wallet_address
        print(f"✅ Registered successfully! Node ID: {client.node_id}")
    except Exception as e:
        print(f"⚠️  Registration warning: {e}")
        print("   (Proceeding with wallet address as identity...)")
        client.node_id = wallet.address

    # 2. Discover Peers
    try:
        peers = client.discover_agents()
        print(f"👥 Found {len(peers)} active peers on the network.")
    except Exception as e:
        print(f"⚠️  Peer discovery failed: {e}")
        peers = []
    
    print("\n🚀 Agent is RUNNING! Waiting for tasks...")
    print("   (Press Ctrl+C to stop)\n")
    print("─" * 50)

    # Task counter
    tasks_completed = 0
    total_earned = 0.0

    # 3. Main Task Loop
    try:
        while True:
            try:
                # Poll for pending tasks
                tasks = client.get_pending_tasks()
                
                if tasks and len(tasks) > 0:
                    for task in tasks:
                        task_id = task.get('task_id') or task.get('id')
                        print(f"\n📋 New Task Received: {task_id}")
                        
                        # Parse payload
                        raw_payload = task.get('payload')
                        if isinstance(raw_payload, str):
                            try:
                                payload = json.loads(raw_payload)
                            except json.JSONDecodeError:
                                payload = {"text": raw_payload}
                        else:
                            payload = raw_payload or {}
                        
                        # Extract task details
                        text = payload.get('text', payload.get('prompt', ''))
                        task_type = payload.get('type', 'general')
                        
                        print(f"⚙️  Processing ({task_type}): {str(text)[:50]}...")
                        
                        # Execute task based on type
                        try:
                            result = execute_task(task_type, payload)
                            print(f"✅ Task completed successfully")
                        except Exception as e:
                            result = {"error": str(e), "status": "failed"}
                            print(f"❌ Task execution failed: {e}")
                        
                        # Submit Result with Sovereign Proof
                        print("🔒 Generating Sovereign Proof and Submitting...")
                        try:
                            response = client.submit_result(task_id, result, wallet=wallet)
                            status = response.get('status', 'unknown')
                            reward = response.get('reward', 0)
                            
                            if status == 'success' or status == 'completed':
                                tasks_completed += 1
                                total_earned += float(reward) if reward else 0
                                print(f"💰 Reward Claimed! Status: {status}")
                                print(f"📊 Stats: {tasks_completed} tasks | {total_earned:.4f} GSTD earned")
                            else:
                                print(f"⚠️  Submit response: {response}")
                        except Exception as e:
                            print(f"❌ Failed to submit result: {e}")
                else:
                    # No tasks available
                    print("💤 No tasks available. Sleeping 10s...", end='\r')
                
            except Exception as e:
                print(f"⚠️  Error in task loop: {e}")
                time.sleep(5)  # Brief pause on error
            
            time.sleep(10)  # Poll interval
            
    except KeyboardInterrupt:
        print("\n")
        print("─" * 50)
        print("🛑 Agent shutting down gracefully...")
        print(f"📊 Final Stats: {tasks_completed} tasks completed | {total_earned:.4f} GSTD earned")
        print("👋 Goodbye!")


def execute_task(task_type: str, payload: dict) -> dict:
    """
    Execute a task based on its type.
    Override this function to add custom capabilities.
    """
    text = payload.get('text', payload.get('prompt', ''))
    
    if task_type == 'text-processing' or task_type == 'general':
        # Basic text processing
        return {
            "processed_text": text.upper(),
            "word_count": len(text.split()),
            "char_count": len(text),
            "status": "success"
        }
    
    elif task_type == 'echo':
        return {"echo": text, "status": "success"}
    
    elif task_type == 'analyze':
        # Basic text analysis
        words = text.split()
        return {
            "word_count": len(words),
            "unique_words": len(set(words)),
            "avg_word_length": sum(len(w) for w in words) / len(words) if words else 0,
            "status": "success"
        }
    
    elif task_type == 'compute':
        # Placeholder for compute tasks
        return {
            "result": "Compute task processed",
            "payload_size": len(str(payload)),
            "status": "success"
        }
    
    else:
        # Default handler
        return {
            "processed": True,
            "task_type": task_type,
            "payload_received": len(str(payload)),
            "status": "success"
        }


if __name__ == "__main__":
    run_agent()
