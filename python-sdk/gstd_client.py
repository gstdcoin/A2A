import requests
import json
import time
import uuid

class GSTDClient:
    def __init__(self, api_url="https://app.gstdtoken.com", wallet_address=None, private_key=None):
        self.api_url = api_url.rstrip('/')
        self.wallet_address = wallet_address
        self.private_key = private_key
        self.node_id = None
        
    def health_check(self):
        """Checks connectivity to the GSTD Grid."""
        try:
            resp = requests.get(f"{self.api_url}/api/v1/health")
            return resp.json()
        except Exception as e:
            return {"status": "unreachable", "error": str(e)}

    def register_node(self, device_name="Autonomous-Agent-Node", capabilities=None):
        """Registers the agent as a compute node."""
        if not self.wallet_address:
            raise ValueError("Wallet address required for registration")
            
        payload = {
            "name": device_name,
            "type": "agent",
            "capabilities": capabilities or ["text-generation", "data-processing"],
            "wallet_address": self.wallet_address
        }
        
        # In a real implementation, we would sign this payload
        resp = requests.post(f"{self.api_url}/api/v1/nodes/register", json=payload)
        if resp.status_code in [200, 201]:
            data = resp.json()
            self.node_id = data.get("node_id")
            return data
        raise Exception(f"Registration failed: {resp.text}")

    def get_pending_tasks(self):
        """Fetches tasks available for execution."""
        if not self.node_id:
             # If no registered node_id, try using wallet as ID (Web/Agent Worker mode)
             self.node_id = self.wallet_address
             
        resp = requests.get(f"{self.api_url}/api/v1/worker/pending?node_id={self.node_id}")
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
        resp = requests.post(f"{self.api_url}/api/v1/worker/submit", json=payload)
        return resp.json()


from protocols import validate_task_payload

    # --- Consumer / Requester Methods ---

    def create_task(self, task_type, data_payload, bid_gstd=1.0):
        """
        Posts a new task to the GSTD grid.
        Enforces Protocol Standards so agents understand each other.
        """
        if not self.wallet_address:
            raise ValueError("Wallet address required to pay for tasks")

        # 1. Enforce Protocol (The "Language")
        if not validate_task_payload(task_type, data_payload):
            raise ValueError(f"Payload does not match protocol for {task_type}. See protocols.py")

        payload = {
            "creator_wallet": self.wallet_address,
            "task_type": task_type,
            "input_data": data_payload,
            "bid_amount": bid_gstd
        }
        
        resp = requests.post(f"{self.api_url}/api/v1/tasks/create", json=payload)
        if resp.status_code in [200, 201]:
            return resp.json() 
        raise Exception(f"Task creation failed: {resp.text}")

    def check_task_status(self, task_id):
        """Checks if a requested task is complete and gets the result."""
        resp = requests.get(f"{self.api_url}/api/v1/tasks/{task_id}")
        if resp.status_code == 200:
            return resp.json()
        return {"status": "unknown"}


    def get_market_quote(self, amount_ton):
        """Gets a quote to swap TON for GSTD."""
        resp = requests.get(f"{self.api_url}/api/v1/market/quote?amount_ton={amount_ton}")
        return resp.json()
        
    def prepare_swap(self, amount_ton):
        """Prepares a transaction to buy GSTD."""
        payload = {
            "wallet_address": self.wallet_address,
            "amount_ton": amount_ton
        }
        resp = requests.post(f"{self.api_url}/api/v1/market/swap", json=payload)
        return resp.json()
