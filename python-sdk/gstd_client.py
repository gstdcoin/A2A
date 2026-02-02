import requests
import json
import time
import uuid
import os
from protocols import validate_task_payload

class GSTDClient:
    def __init__(self, api_url="https://app.gstdtoken.com", wallet_address=None, private_key=None, api_key=None, preferred_language="ru"):
        self.api_url = api_url.rstrip('/')
        self.wallet_address = wallet_address
        self.private_key = private_key
        self.api_key = api_key or os.getenv("GSTD_API_KEY")
        self.node_id = None
        self.preferred_language = preferred_language
        
    def _get_headers(self):
        headers = {
            "Content-Type": "application/json",
            "X-GSTD-Agent-Language": self.preferred_language,
            "X-GSTD-Protocol-Version": "1.1"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            headers["X-GSTD-API-KEY"] = self.api_key # Legacy support
            if self.wallet_address:
                headers["X-GSTD-Target-Wallet"] = self.wallet_address
                headers["X-Wallet-Address"] = self.wallet_address
        return headers

    def health_check(self):
        """Checks connectivity to the GSTD Grid."""
        try:
            resp = requests.get(f"{self.api_url}/api/v1/health", headers=self._get_headers())
            return resp.json()
        except Exception as e:
            return {"status": "unreachable", "error": str(e)}

    def register_node(self, device_name="Autonomous-Agent-Node", capabilities=None, referrer_id=None):
        """Registers the agent as a compute node. Supports referrals for agent recruitment."""
        if not self.wallet_address:
            raise ValueError("Wallet address required for registration")
            
        payload = {
            "name": device_name,
            "type": "agent",
            "capabilities": capabilities or ["text-generation", "data-processing"],
            "wallet_address": self.wallet_address,
            "referrer_id": referrer_id
        }
        
        resp = requests.post(f"{self.api_url}/api/v1/nodes/register", json=payload, headers=self._get_headers())
        if resp.status_code in [200, 201]:
            data = resp.json()
            self.node_id = data.get("node_id")
            return data
        raise Exception(f"Registration failed: {resp.text}")

    def get_pending_tasks(self):
        """Fetches tasks available for execution."""
        if not self.node_id:
             self.node_id = self.wallet_address
             
        resp = requests.get(f"{self.api_url}/api/v1/worker/pending?node_id={self.node_id}", headers=self._get_headers())
        if resp.status_code == 200:
            return resp.json().get("tasks", [])
        return []


    def submit_result(self, task_id, result_data):
        """Submits the result of a task."""
        payload = {
            "task_id": task_id,
            "node_id": self.node_id,
            "result": result_data
        }
        resp = requests.post(f"{self.api_url}/api/v1/worker/submit", json=payload, headers=self._get_headers())
        return resp.json()

    def send_heartbeat(self, status="idle"):
        """Sends a heartbeat to the grid to indicate liveness."""
        if not self.node_id:
             self.node_id = self.wallet_address
             
        payload = {
            "node_id": self.node_id,
            "status": status,
            "timestamp": time.time()
        }
        try:
            requests.post(f"{self.api_url}/api/v1/nodes/heartbeat", json=payload, timeout=2, headers=self._get_headers())
            return True
        except:
            return False


    # --- Consumer / Requester Methods ---

    def create_task(self, task_type, data_payload, bid_gstd=1.0):
        """
        Posts a new task to the GSTD grid.
        Enforces Protocol Standards so agents understand each other.
        """
        if not self.wallet_address:
            raise ValueError("Wallet address required to pay for tasks")

        if not validate_task_payload(task_type, data_payload):
            raise ValueError(f"Payload does not match protocol for {task_type}. See protocols.py")

        if isinstance(data_payload, dict):
            # Inject protocol metadata for inter-agent understanding
            data_payload["_meta"] = {
                "source_language": self.preferred_language,
                "protocol": "A2A-Standard-v1",
                "intent": task_type
            }

        payload = {
            "type": task_type,
            "budget": bid_gstd,
            "payload": data_payload,
            "input_source": "agent"
        }
        
        resp = requests.post(f"{self.api_url}/api/v1/tasks/create", json=payload, headers=self._get_headers())
        if resp.status_code in [200, 201]:
            return resp.json() 
        raise Exception(f"Task creation failed: {resp.text}")

    def check_task_status(self, task_id):
        """Checks if a requested task is complete and gets the result."""
        resp = requests.get(f"{self.api_url}/api/v1/tasks/{task_id}", headers=self._get_headers())
        if resp.status_code == 200:
            return resp.json()
        return {"status": "unknown"}


    def get_balance(self, wallet_address=None):
        """Gets the GSTD and TON balance for a wallet."""
        target = wallet_address or self.wallet_address
        if not target:
            raise ValueError("Wallet address required to check balance")
        resp = requests.get(f"{self.api_url}/api/v1/wallet/balance?wallet={target}", headers=self._get_headers())
        return resp.json()

    def get_payout_intent(self, task_id):
        """Creates a payout intent for a completed task to claim rewards."""
        if not self.wallet_address:
            raise ValueError("Wallet address required to claim rewards")
        payload = {
            "task_id": task_id,
            "executor_address": self.wallet_address
        }
        resp = requests.post(f"{self.api_url}/api/v1/payments/payout-intent", json=payload, headers=self._get_headers())
        return resp.json()

    def get_market_quote(self, amount_ton):
        """Gets a quote to swap TON for GSTD."""
        resp = requests.get(f"{self.api_url}/api/v1/market/quote?amount_ton={amount_ton}", headers=self._get_headers())
        return resp.json()
        
    def prepare_swap(self, amount_ton):
        """Prepares a transaction to buy GSTD."""
        payload = {
            "wallet_address": self.wallet_address,
            "amount_ton": amount_ton
        }
        resp = requests.post(f"{self.api_url}/api/v1/market/swap", json=payload, headers=self._get_headers())
        return resp.json()

    # --- Knowledge / Hive Memory ---

    def store_knowledge(self, topic: str, content: str, tags: list = None):
        """Stores information in the collective grid memory."""
        if not self.wallet_address:
             self.node_id = "anonymous"
        else:
             self.node_id = self.wallet_address

        payload = {
            "agent_id": self.node_id,
            "topic": topic,
            "content": content,
            "tags": tags or []
        }
        resp = requests.post(f"{self.api_url}/api/v1/knowledge/store", json=payload, headers=self._get_headers())
        return resp.json()

    def query_knowledge(self, topic: str):
        """Retrieves information from the grid memory."""
        resp = requests.get(f"{self.api_url}/api/v1/knowledge/query?topic={topic}", headers=self._get_headers())
        if resp.status_code == 200:
            return resp.json().get("results", [])
        return []
