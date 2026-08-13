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
            if res and 'balance_gstd' in res:
                return float(res['balance_gstd'])
            return 0.0
        except Exception as e:
            print(f"Error checking balance: {e}")
            return 0.0

    def run_as_worker(self):
        """Worker Mode: watches for tasks, but does NOT execute or submit them.

        This example only demonstrates the balance-based master/worker mode
        switch — it has no real task-execution logic. Earlier versions of
        this file submitted a hardcoded `{"status": "completed", "result":
        "Success from Sovereign Swarm"}` for every task it saw, regardless
        of what the task actually was — that would have claimed a reward
        for work never performed. For real task execution, use
        `gstd_a2a.agent.Agent`, which has genuine task handlers.
        """
        print(f"👷 [WORKER MODE] Node {self.node_id[:8]} at work...")
        try:
            # 1. Pulse heartbeat
            self.client.send_heartbeat(status="active")

            # 2. Look for work
            tasks_res = self.client.get_pending_tasks()
            tasks = tasks_res if isinstance(tasks_res, list) else tasks_res.get('tasks', [])
            if tasks and len(tasks) > 0:
                task = tasks[0]
                print(f"💎 Found task: {task['task_id']} | Reward: {task.get('labor_compensation_gstd', 0)} GSTD")
                print("⚠️  This example does not execute tasks — skipping (see gstd_a2a.agent.Agent for real execution)")
                time.sleep(5)
            else:
                print("💤 No tasks available. Standing by...")
                time.sleep(5)
        except Exception as e:
            print(f"❌ Worker error: {e}")
            time.sleep(5)

    def run_as_master(self):
        """Master Mode: placeholder for spending GSTD once the agent has funds.

        No paid task-marketplace exists on the platform yet (nothing to
        commission sub-tasks to), so this is currently a no-op stub.
        """
        print(f"👑 [MASTER MODE] Node {self.node_id[:8]} in control.")
        try:
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
