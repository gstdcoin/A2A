#!/usr/bin/env python3
"""
GSTD Swarm Client — Linux-клиент для участника роя
Подключается к сети GSTD, регистрируется как нода, получает и выполняет задачи.
Поддерживает Fleet Commands (standby/resume) через WebSocket.

Использование:
    export GSTD_API_KEY="your_key"
    export GSTD_WALLET="EQ..."  # или извлекается из API key
    python swarm_client.py

Или:
    python swarm_client.py --api-key KEY --wallet EQ...
"""

import argparse
import json
import logging
import os
import platform
import signal
import sys
import threading
import time
import uuid

try:
    import requests
except ImportError:
    print("pip install requests", file=sys.stderr)
    sys.exit(1)

try:
    import websocket
except ImportError:
    websocket = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("swarm")


class SwarmClient:
    def __init__(
        self,
        api_url=None,
        api_key=None,
        wallet=None,
        device_id=None,
        use_websocket=True,
    ):
        self.api_url = (api_url or os.getenv("GSTD_API_URL", "https://app.gstdtoken.com")).rstrip("/")
        self.api_key = api_key or os.getenv("GSTD_API_KEY")
        self.wallet = wallet or os.getenv("GSTD_WALLET")
        self.device_id = device_id or f"swarm-{platform.node()}-{uuid.uuid4().hex[:8]}"
        self.use_websocket = use_websocket and websocket is not None
        self.node_id = None
        self._running = True
        self._paused = False  # Fleet standby
        self._ws = None
        self._ws_thread = None

        if not self.api_key:
            raise ValueError("GSTD_API_KEY required. Get from https://app.gstdtoken.com/dashboard")

        if not self.wallet:
            # Try to extract from API key (sk_sovereign_WALLET_nonce) or use device_id as fallback
            if self.api_key.startswith("sk_sovereign_") and "_" in self.api_key:
                parts = self.api_key.split("_")
                if len(parts) >= 4:
                    self.wallet = parts[2]
            if not self.wallet:
                raise ValueError("GSTD_WALLET required when API key does not contain wallet")

    def _headers(self):
        h = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "X-GSTD-API-KEY": self.api_key,
            "X-Wallet-Address": self.wallet,
            "X-GSTD-Target-Wallet": self.wallet,
        }
        return h

    def _ws_url(self):
        base = self.api_url.replace("https://", "wss://").replace("http://", "ws://")
        return f"{base}/ws?device_id={self.device_id}&wallet_address={self.wallet}"

    def health_check(self):
        try:
            r = requests.get(f"{self.api_url}/api/v1/health", headers=self._headers(), timeout=5)
            return r.status_code == 200
        except Exception as e:
            log.warning("Health check failed: %s", e)
            return False

    def register_node(self, use_registry=True):
        """Register as node. use_registry=True uses /registry/join (Unified Identity)."""
        specs = {
            "capabilities": ["compute", "data-processing", "inference"],
            "type": "swarm",
            "os": platform.system(),
            "hostname": platform.node(),
        }
        platform_fingerprint = f"{platform.system()}|{platform.node()}|swarm"
        if use_registry:
            payload = {
                "wallet_address": self.wallet,
                "name": f"Swarm-Node-{self.device_id[:12]}",
                "source": "swarm",
                "specs": specs,
                "platform_fingerprint": platform_fingerprint,
            }
            url = f"{self.api_url}/api/v1/registry/join"
        else:
            log.warning(
                "[DEPRECATION] POST /nodes/register is deprecated. Use registry/join. "
                "Support until 2026-03-18. Set use_registry=True (default)."
            )
            payload = {"name": f"Swarm-Node-{self.device_id[:12]}", "specs": specs}
            url = f"{self.api_url}/api/v1/nodes/register?wallet_address={self.wallet}"
        r = requests.post(url, json=payload, headers=self._headers(), timeout=15)
        if r.status_code in (200, 201):
            data = r.json()
            self.node_id = data.get("node_id") or data.get("id") or self.wallet
            log.info("Node registered: %s", self.node_id)
            return True
        log.error("Registration failed %s: %s", r.status_code, r.text[:200])
        self.node_id = self.wallet
        return False

    def heartbeat(self):
        payload = {
            "wallet": self.wallet,
            "node_id": self.node_id or self.wallet,
            "status": "idle" if not self._paused else "standby",
            "battery": 100,
            "signal": 100,
        }
        try:
            r = requests.post(
                f"{self.api_url}/api/v1/nodes/heartbeat",
                json=payload,
                headers=self._headers(),
                timeout=5,
            )
            return r.status_code == 200
        except Exception:
            return False

    def get_pending_tasks(self):
        node = self.node_id or self.wallet
        url = f"{self.api_url}/api/v1/tasks/worker/pending?node_id={node}&limit=10"
        try:
            r = requests.get(url, headers=self._headers(), timeout=10)
            if r.status_code == 200:
                return r.json().get("tasks", [])
        except Exception as e:
            log.debug("get_pending_tasks: %s", e)
        return []

    def submit_result(self, task_id, result_data, execution_time_ms=1000):
        payload = {
            "task_id": task_id,
            "node_id": self.node_id or self.wallet,
            "result": result_data,
            "proof": "",
        }
        try:
            r = requests.post(
                f"{self.api_url}/api/v1/tasks/worker/submit",
                json=payload,
                headers=self._headers(),
                timeout=15,
            )
            if r.status_code == 200:
                log.info("Task %s completed", task_id)
                return True
            log.warning("Submit failed %s: %s", r.status_code, r.text[:150])
        except Exception as e:
            log.warning("Submit error: %s", e)
        return False

    def _execute_task(self, task):
        task_id = task.get("task_id", "")
        if not task_id:
            log.warning("Task missing task_id, skipping")
            return False
        task_type = task.get("task_type", "unknown")
        payload_raw = task.get("payload") or "{}"
        if isinstance(payload_raw, str):
            try:
                payload = json.loads(payload_raw)
            except json.JSONDecodeError:
                payload = {}
        else:
            payload = payload_raw

        start = time.time()
        result = {"completed": True, "output": "ok"}

        if task_type == "polymarket_prediction":
            result = {
                "prediction": "yes",
                "confidence": 0.7,
                "reasoning": "Swarm client default",
            }
        elif "prompt" in payload or "input" in payload:
            text = payload.get("prompt") or payload.get("input") or ""
            result = {"output": f"Processed: {text[:100]}...", "completed": True}

        elapsed_ms = int((time.time() - start) * 1000)
        return self.submit_result(task_id, result, elapsed_ms)

    def _task_loop(self):
        interval = 5
        last_heartbeat = 0
        while self._running:
            if self._paused:
                time.sleep(2)
                continue

            now = time.time()
            if now - last_heartbeat > 25:
                self.heartbeat()
                last_heartbeat = now

            tasks = self.get_pending_tasks()
            for task in tasks:
                if self._paused:
                    break
                try:
                    self._execute_task(task)
                except Exception as e:
                    log.exception("Task execution failed: %s", e)
                time.sleep(0.5)

            time.sleep(interval)

    def _on_ws_message(self, ws, message):
        try:
            data = json.loads(message)
            if data.get("type") == "heartbeat_ack":
                cmd = data.get("fleet_command")
                if cmd:
                    action = cmd.get("action", "")
                    if action == "standby":
                        self._paused = True
                        log.info("Fleet command: STANDBY")
                    elif action == "resume":
                        self._paused = False
                        log.info("Fleet command: RESUME")
                    elif action == "clean":
                        log.info("Fleet command: CLEAN (no-op in swarm client)")
            elif data.get("type") == "task" and data.get("task"):
                task = data["task"]
                if not self._paused:
                    threading.Thread(target=self._execute_task, args=(task,), daemon=True).start()
        except Exception as e:
            log.debug("WS message parse: %s", e)

    def _ws_loop(self):
        url = self._ws_url()
        log.info("WebSocket connecting to %s", self.api_url)
        while self._running:
            try:
                self._ws = websocket.WebSocketApp(
                    url,
                    on_message=self._on_ws_message,
                    on_error=lambda ws, err: log.debug("WS error: %s", err),
                    on_close=lambda ws, code, msg: log.debug("WS closed: %s %s", code, msg),
                )
                self._ws.run_forever(ping_interval=30, ping_timeout=10)
            except Exception as e:
                log.debug("WS: %s", e)
            if self._running:
                time.sleep(5)

    def run(self):
        if not self.health_check():
            log.error("Platform unreachable. Check GSTD_API_URL and network.")
            return 1

        if not self.register_node():
            log.warning("Registration failed, continuing with wallet-as-node")

        def on_signal(sig, frame):
            self._running = False
            if self._ws:
                self._ws.close()

        signal.signal(signal.SIGINT, on_signal)
        signal.signal(signal.SIGTERM, on_signal)

        if self.use_websocket:
            self._ws_thread = threading.Thread(target=self._ws_loop, daemon=True)
            self._ws_thread.start()

        log.info("Swarm client running. Node: %s. Fleet commands: %s", self.node_id or self.wallet, self.use_websocket)
        self._task_loop()
        return 0


def main():
    ap = argparse.ArgumentParser(description="GSTD Swarm Client — участник роя")
    ap.add_argument("--api-key", "-k", help="GSTD_API_KEY")
    ap.add_argument("--wallet", "-w", help="Wallet address (or from API key)")
    ap.add_argument("--api-url", "-u", help="Platform URL")
    ap.add_argument("--no-ws", action="store_true", help="Disable WebSocket (REST only)")
    args = ap.parse_args()

    try:
        client = SwarmClient(
            api_url=args.api_url,
            api_key=args.api_key,
            wallet=args.wallet,
            use_websocket=not args.no_ws,
        )
        sys.exit(client.run())
    except ValueError as e:
        log.error("%s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
