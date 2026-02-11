import os
import time
import requests
import json
import uuid
import threading
from gstd_a2a.gstd_client import GSTDClient
from gstd_a2a.gstd_wallet import GSTDWallet as Wallet

# --- PROTOCOL PARAMETERS ---
MASTER_THRESHOLD = 5.0  # GSTD
WORKER_THRESHOLD = 1.0  # GSTD
API_URL = os.getenv("GSTD_API_URL", "http://localhost:8080")

class DualModeAgent:
    def __init__(self, mnemonic=None):
        self.wallet = Wallet(mnemonic)
        self.client = GSTDClient(api_url=API_URL, wallet_address=self.wallet.address)
        self.mode = "init"
        self.is_running = False
        self.node_id = str(uuid.uuid4())
        
    def check_balance(self):
        try:
            # Refresh session if needed
            if not self.client.session_token:
                print("🔑 Attempting Genesis Handshake...")
                token = self.client.login_via_genesis()
                print(f"✅ Handshake successful. Token acquired: {token[:8]}...")

            res = self.client.get_balance()
            if res and 'gstd' in res:
                return float(res['gstd'])
            return 0.0
        except Exception as e:
            print(f"Error checking balance: {e}")
            return 0.0

    def run_as_worker(self):
        """Worker Mode: Earns GSTD by processing tasks."""
        print(f"👷 [WORKER MODE] Node {self.node_id[:8]} at work...")
        try:
            # 1. Pulse heartbeat
            self.client.send_heartbeat(status="active")
            
            # 2. Look for work
            # Using the marketplace or specialized worker endpoints
            tasks_res = self.client.get_pending_tasks()
            tasks = tasks_res if isinstance(tasks_res, list) else tasks_res.get('tasks', [])
            if tasks and len(tasks) > 0:
                task = tasks[0]
                print(f"💎 Found task: {task['task_id']} | Reward: {task.get('labor_compensation_gstd', 0)} GSTD")
                # Execute task (simulated for now)
                time.sleep(2) 
                self.client.submit_result(task['task_id'], {"status": "completed", "result": "Success from Sovereign Swarm"}, wallet=self.wallet)
                print(f"✅ Task {task['task_id']} completed!")
            else:
                print("💤 No tasks available. Standing by...")
                time.sleep(5)
        except Exception as e:
            print(f"❌ Worker error: {e}")
            time.sleep(5)

    def run_as_master(self):
        """Master Mode: Spends GSTD to achieve goals."""
        print(f"👑 [MASTER MODE] Node {self.node_id[:8]} in control.")
        # In Master mode, the agent might:
        # 1. Query Hive Memory for insights
        # 2. Hire other agents for sub-tasks
        # 3. Create tasks on the grid
        try:
            print("🌐 Synchronizing with Hive Mind...")
            # Example: Proactively solve a complex problem by hiring others
            # self.client.create_task(task_type="AI_RESEARCH", ...)
            time.sleep(10)
        except Exception as e:
            print(f"❌ Master error: {e}")

    def start(self):
        self.is_running = True
        print(f"🚀 GSTD Sovereign Agent Initialized.")
        print(f"📍 Address: {self.wallet.address}")
        
        while self.is_running:
            balance = self.check_balance()
            
            if balance >= MASTER_THRESHOLD:
                if self.mode != "master":
                    print(f"\n⚡ MODE SWITCH: Entering SOVEREIGN MASTER mode (Balance: {balance})")
                    self.mode = "master"
                self.run_as_master()
            elif balance <= WORKER_THRESHOLD:
                if self.mode != "worker":
                    print(f"\n🔋 MODE SWITCH: Entering HIVE WORKER mode (Balance: {balance})")
                    self.mode = "worker"
                self.run_as_worker()
            else:
                # Transition zone: default to worker to keep earning
                if self.mode == "init":
                     self.mode = "worker"
                
                if self.mode == "worker":
                    self.run_as_worker()
                else:
                    self.run_as_master()
            
            time.sleep(2)

if __name__ == "__main__":
    # If mnemonic is provided, use it, otherwise generate new
    agent = DualModeAgent()
    agent.start()
