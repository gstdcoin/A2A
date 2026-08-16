import requests
import json
import time
import os
import sys

class GSTDClient:
    def __init__(self, api_url="https://app.gstdtoken.com", wallet_address=None, private_key=None, api_key=None, preferred_language="ru"):
        self.api_url = api_url.rstrip('/')
        self.wallet_address = wallet_address
        self.private_key = private_key
        self.api_key = api_key or os.getenv("GSTD_API_KEY")
        self.session_token = None
        self.node_id = None
        self.preferred_language = preferred_language
        
    def _get_headers(self):
        """Auto-inject API key and wallet into every request (SS-Auth)."""
        headers = {
            "Content-Type": "application/json",
            "X-GSTD-Agent-Language": self.preferred_language,
            "X-GSTD-Protocol-Version": "1.1"
        }
        if self.session_token:
            headers["X-Session-Token"] = self.session_token
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            headers["X-GSTD-API-KEY"] = self.api_key
        if self.wallet_address:
            headers["X-GSTD-Target-Wallet"] = self.wallet_address
            headers["X-Wallet-Address"] = self.wallet_address
        return headers

    def reauthenticate(self):
        """Obtain session via Genesis Ignite (SS-Auth). Called on 401 or at startup."""
        try:
            self.session_token = self.login_via_genesis()
            return self.session_token is not None
        except Exception as e:
            sys.stderr.write(f"⚠️  reauthenticate failed: {e}\n")
            return False

    def health_check(self):
        """Checks connectivity to the GSTD Grid."""
        try:
            resp = requests.get(f"{self.api_url}/api/v1/health", headers=self._get_headers(), timeout=15)
            return resp.json()
        except Exception as e:
            return {"status": "unreachable", "error": str(e)}

    def register_node(self, device_name="Autonomous-Agent-Node", capabilities=None, referrer_id=None, max_retries=5):
        """Registers the agent as a compute node. Retries with exponential backoff on failure."""
        if not self.wallet_address:
            raise ValueError("Wallet address required for registration")

        payload = {
            "name": device_name,
            "specs": {
                "type": "agent",
                "capabilities": capabilities or ["text-generation", "data-processing"],
                "referrer_id": referrer_id
            }
        }

        last_err = None
        for attempt in range(max_retries):
            try:
                resp = requests.post(
                    f"{self.api_url}/api/v1/nodes/register",
                    json=payload,
                    headers=self._get_headers(),
                    timeout=15
                )
                if resp.status_code in [200, 201]:
                    data = resp.json()
                    self.node_id = data.get("node_id") or data.get("id") or data.get("ID")
                    return data
                last_err = Exception(f"Registration failed ({resp.status_code}): {resp.text}")
            except Exception as e:
                last_err = e

            if attempt < max_retries - 1:
                delay = min(2 ** attempt, 60)
                time.sleep(delay)
                if self.reauthenticate():
                    continue

        raise last_err

    def login_via_genesis(self):
        """Performs the Genesis Handshake to get a session token."""
        if not self.wallet_address:
            raise ValueError("Wallet address required for Genesis Handshake")
            
        payload = {"wallet_address": self.wallet_address}
        resp = requests.post(f"{self.api_url}/api/v1/genesis/ignite", json=payload, headers=self._get_headers(), timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            self.session_token = data.get("token")
            return self.session_token
        raise Exception(f"Genesis Handshake failed: {resp.text}")

    def get_pending_tasks(self):
        """Fetches tasks available for execution. Auto-reauth on 401."""
        if not self.node_id:
             self.node_id = self.wallet_address
             
        def _fetch():
            resp = requests.get(
                f"{self.api_url}/api/v1/tasks/worker/pending?node_id={self.node_id}",
                headers=self._get_headers(),
                timeout=15
            )
            if resp.status_code == 200:
                data = resp.json()
                return (data if isinstance(data, list) else data.get("tasks", [])), resp.status_code
            return [], resp.status_code
        
        try:
            tasks, code = _fetch()
            if tasks:
                return tasks
            if code == 401 and self.wallet_address:
                if self.reauthenticate():
                    tasks, _ = _fetch()
                    return tasks
                sys.stderr.write("⚠️  Authentication failed (401). Genesis Ignite retry failed.\n")
            elif code == 401:
                sys.stderr.write("⚠️  Authentication failed (401). Please set GSTD_API_KEY or ensure wallet.\n")
            return []
        except Exception as e:
            sys.stderr.write(f"❌ Error fetching tasks: {e}\n")
            return []


    def submit_result(self, task_id, result_data, wallet=None, execution_time_ms=0):
        """
        Submits the result of a task with cryptographic proof.
        If a GSTDWallet instance is provided, it signs the result to prove identity.
        """
        import json
        
        # Serialize result for signing consistency
        result_json = json.dumps(result_data, sort_keys=True)
        
        proof = ""
        if wallet and hasattr(wallet, 'sign_message'):
            # The protocol expects signature of (taskID + resultData)
            message_to_sign = f"{task_id}{result_json}"
            proof = wallet.sign_message(message_to_sign)
            sys.stderr.write(f"🔒 Generated Sovereign Proof: {proof[:10]}...\n")

        payload = {
            "task_id": task_id,
            "node_id": self.node_id or self.wallet_address,
            "result": result_data,
            "proof": proof,
            "execution_time_ms": int(execution_time_ms)
        }

        # A completed task's result carries a real GSTD reward -- a timeout here must not
        # silently drop it (the work is already done), so retry before giving up.
        last_err = None
        for attempt in range(3):
            try:
                resp = requests.post(f"{self.api_url}/api/v1/tasks/worker/submit", json=payload, headers=self._get_headers(), timeout=15)
                return resp.json()
            except requests.exceptions.RequestException as e:
                last_err = e
                if attempt < 2:
                    time.sleep(2 ** (attempt + 1))
        raise last_err

    def send_heartbeat(self, status="idle"):
        """Sends a heartbeat to the grid to indicate liveness.
        Includes wallet for immediate DB update and node visibility in Dashboard."""
        if not self.node_id:
            self.node_id = self.wallet_address

        payload = {
            "node_id": self.node_id,
            "wallet": self.wallet_address,
            "status": status,
            "timestamp": time.time(),
            "battery": 100,
            "signal": 100,
        }
        try:
            requests.post(f"{self.api_url}/api/v1/nodes/heartbeat", json=payload, timeout=2, headers=self._get_headers())
            return True
        except Exception:
            return False


    def get_balance(self, wallet_address=None):
        """
        Gets the platform GSTD spending-credit balance for a wallet
        (used for e.g. paid API calls / training jobs). This is NOT the
        agent's on-chain token balance -- for that, use
        GSTDWallet.check_balance() instead, which queries TON directly.

        Raises requests.HTTPError on a non-200 response (e.g. 401 for an
        invalid API key) -- callers that want to treat a failed balance
        check as "just assume zero" should catch this explicitly, rather
        than have that assumption made silently here.
        """
        target = wallet_address or self.wallet_address
        resp = requests.get(
            f"{self.api_url}/api/v1/credits/balance?wallet={target}",
            headers=self._get_headers(),
            timeout=15
        )
        resp.raise_for_status()
        return resp.json()

    # --- Discovery (Registry) ---

    def discover_agents(self, capability=None, limit=20, offset=0):
        """
        Finds other agents on the network with pagination support.
        Essential for scaling to millions of agents.
        """
        params = f"?limit={limit}&offset={offset}"
        resp = requests.get(f"{self.api_url}/api/v1/nodes/public{params}", headers=self._get_headers(), timeout=30)
        if resp.status_code == 200:
            nodes = resp.json().get("nodes") or []
            if capability:
                # Local filtering (backend should ideally support this via query param)
                return [n for n in nodes if capability in str(n.get('capabilities') or [])]
            return nodes
        
        sys.stderr.write(f"⚠️  Discovery failed: {resp.status_code} - {resp.text}\n")
        return []

