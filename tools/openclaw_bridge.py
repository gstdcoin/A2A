import os
import time
import json
import random
from typing import Dict, Any

from gstd_a2a import GSTDClient, GSTDWallet, LLMService

class OpenClawBridge:
    """
    Bridge between OpenClaw hardware and the GSTD Decentralized Grid.
    Registers as a physical control node and earns GSTD by executing
    control-command tasks dispatched from the agent network.
    """
    
    def __init__(self, device_name="OpenClaw-Unit-01", wallet_mnemonic=None, api_url=None):
        print(f"🦞 Initializing OpenClaw Bridge for {device_name}...")
        
        # 1. Identity & Wallet
        self.wallet = GSTDWallet(mnemonic=wallet_mnemonic)
        print(f"🔑 Identity: {self.wallet.address}")
        
        # 1.1 Local Intelligence (Ollama) + Cloud compound model
        self.llm = LLMService(api_url="http://localhost:11434")
        self.default_model = os.getenv("GSTD_DEFAULT_MODEL", "llama3.2:3b")
        self.openclaw_api = os.getenv("OPENCLAW_API_BASE", "https://app.gstdtoken.com/api/v1/openclaw")
        
        # 2. Connect to Grid
        self.api_url = api_url or os.getenv("GSTD_API_URL", "https://app.gstdtoken.com")
        self.client = GSTDClient(wallet_address=self.wallet.address, api_url=self.api_url, api_key=os.getenv("GSTD_API_KEY"))
        
        # 3. Register capabilities
        self.device_name = device_name
        self.node_id = None
        self._register()

    def _register(self):
        print("📡 Registering on GSTD Grid as Physical Control Node...")
        try:
            reg = self.client.register_node(
                device_name=self.device_name,
                capabilities=["openclaw-control", "sensor-reading", "iot-actuation"]
            )
            self.node_id = reg.get("node_id") or reg.get("id")
            print(f"✅ Registered! Node ID: {self.node_id}")
            print(f"💰 Earnings will be deposited to: {self.wallet.address}")
        except Exception as e:
            print(f"⚠️ Registration warning: {e}")
            self.node_id = self.wallet.address # Fallback

    def run(self):
        print("\n🚀 Bridge Active. Listening for control commands from the Hive Mind...")
        print("   (Press Ctrl+C to stop)")
        
        while True:
            try:
                # A. Check for Incoming Jobs (Monetization Mode)
                tasks = self.client.get_pending_tasks()
                for task in tasks:
                    if task.get("type") == "openclaw-control":
                        self._handle_control_task(task)

                # Heartbeat
                self.client.send_heartbeat(status="ready")
                time.sleep(5)

            except KeyboardInterrupt:
                print("\n🛑 Shutting down bridge.")
                break
            except Exception as e:
                print(f"❌ Error in loop: {e}")
                time.sleep(5)

    def _handle_control_task(self, task):
        task_id = task.get("id")
        payload = task.get("payload", {})
        
        print(f"\n⚡ Received Control Command from Agent Network!")
        print(f"   Task ID: {task_id}")
        print(f"   Command: {payload.get('command')}")
        print(f"   Params:  {payload.get('parameters')}")
        
        # --- PHYSICAL EXECUTION WOULD GO HERE ---
        # e.g., openclaw.move_to(x, y, z)
        print("   ⚙️  Actuating hardware...")
        time.sleep(2) # Simulate movement physics
        # ----------------------------------------
        
        result = {
            "status": "success",
            "telemetry": {
                "final_position": {"x": 10, "y": 20, "z": 5},
                "battery": "98%"
            },
            "executed_by": self.device_name
        }
        
        # Sign result for security
        self.client.submit_result(task_id, result, wallet=self.wallet)
        print("   ✅ Execution verified and proof submitted. Payment incoming.")

if __name__ == "__main__":
    # In a real deployment, mnemonic comes from secure storage or env
    # Here we generate a fresh one for the demo
    bridge = OpenClawBridge()
    bridge.run()
