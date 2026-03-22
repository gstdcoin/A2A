#!/usr/bin/env python3
"""
GSTD A2A Connector v2.0
Agent-to-Agent protocol for the GSTD Grid.

Usage:
  python3 connect.py --api-key <YOUR_KEY>
  python3 connect.py --api-key <YOUR_KEY> --url https://api.gstdtoken.com/api/v1
  python3 connect.py --api-key <YOUR_KEY> --wallet UQ...
  python3 connect.py --register --name "MyAgent"

Get your API key: https://app.gstdtoken.com → Dashboard → Agents
"""

import argparse
import sys
import json
import time
import subprocess
import platform
import os
from datetime import datetime, timezone

# ─── Configuration ────────────────────────────────────────────────
DEFAULT_API_URL    = "https://api.gstdtoken.com/api/v1"
FALLBACK_API_URL   = "https://gstd.ton.limo/api/v1"
AGENT_VERSION      = "2.0.0"
HEARTBEAT_INTERVAL = 60    # seconds
POLL_INTERVAL      = 10    # task poll interval
MAX_RETRIES        = 3

# ─── Timestamps ───────────────────────────────────────────────────
def ts():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

def log(msg, level="info"):
    icons = {"info": "ℹ️", "ok": "✅", "warn": "⚠️", "error": "❌", "earn": "💰"}
    print(f"[{ts()}] {icons.get(level,'•')} {msg}", flush=True)

# ─── HTTP via curl (avoids urllib SSL/encoding issues) ────────────
def api_call(url, method="GET", data=None, headers=None, timeout=15):
    headers = headers or {}
    headers.setdefault("Content-Type", "application/json")
    headers.setdefault("User-Agent", f"GSTD-A2A/{AGENT_VERSION}")

    cmd = ["curl", "-s", "-X", method, url, "--max-time", str(timeout)]
    for k, v in headers.items():
        cmd += ["-H", f"{k}: {v}"]
    if data:
        cmd += ["-d", json.dumps(data)]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
        if result.stdout.strip():
            return json.loads(result.stdout)
    except Exception as e:
        log(f"Network error: {e}", "warn")
    return None

# ─── Register new agent ───────────────────────────────────────────
def register_agent(url, name, wallet=None):
    log(f"Registering agent '{name}'...")
    payload = {
        "name": name,
        "capabilities": ["compute", "ai_inference", "rag", "market_analysis"],
        "node_version": AGENT_VERSION,
        "os": platform.system(),
        "arch": platform.machine(),
        "wallet_address": wallet or "",
    }
    resp = api_call(f"{url}/agents/register", "POST", payload)
    if resp and resp.get("api_key"):
        log(f"Registered! API Key: {resp['api_key']}", "ok")
        log(f"Agent ID: {resp.get('agent_id', '?')}")
        log("Save this key — use it with --api-key flag")
        return resp["api_key"]
    else:
        log(f"Registration failed: {resp}", "error")
        return None

# ─── Resource stats ───────────────────────────────────────────────
def get_resources():
    cpu, ram = 0.3, 0.5
    try:
        # CPU usage from /proc/stat
        s1 = open("/proc/stat").readline().split()
        time.sleep(0.2)
        s2 = open("/proc/stat").readline().split()
        idle1, idle2 = int(s1[4]), int(s2[4])
        total1 = sum(int(x) for x in s1[1:])
        total2 = sum(int(x) for x in s2[1:])
        cpu = 1 - (idle2 - idle1) / (total2 - total1)
    except Exception:
        pass
    try:
        lines = {l.split(":")[0]: int(l.split()[1]) for l in open("/proc/meminfo") if ":" in l}
        total = lines.get("MemTotal", 1)
        free  = lines.get("MemAvailable", 0)
        ram = 1 - free / total
    except Exception:
        pass
    return round(cpu, 3), round(ram, 3)

# ─── Send heartbeat → earn GSTD ───────────────────────────────────
def send_heartbeat(url, api_key, uptime_sec, tasks_done):
    cpu, ram = get_resources()
    resp = api_call(f"{url}/agents/earn/heartbeat", "POST", {
        "cpu_usage": cpu,
        "gpu_usage": 0.0,
        "ram_usage": ram,
        "uptime_seconds": uptime_sec,
        "tasks_done": tasks_done,
    }, {"Authorization": f"Bearer {api_key}"})
    if resp:
        earned = resp.get("net_reward", 0)
        balance = resp.get("balance", "?")
        if earned > 0:
            log(f"Heartbeat → +{earned:.6f} GSTD | CPU:{cpu*100:.1f}% RAM:{ram*100:.1f}% | Balance: {balance}", "earn")
        else:
            log(f"Heartbeat OK | CPU:{cpu*100:.1f}% | Balance: {balance}")
        return earned
    else:
        log("Heartbeat failed — API unreachable", "warn")
        return 0

# ─── Fetch and process a task ─────────────────────────────────────
def fetch_task(url, headers):
    return api_call(f"{url}/agents/tasks/next", "GET", headers=headers)

def submit_result(url, task_id, result_data, headers):
    return api_call(f"{url}/agents/tasks/{task_id}/complete", "POST", {
        "result": result_data,
        "status": "completed",
    }, headers)

def process_task(task, url, headers):
    task_id   = task.get("id", "?")
    task_type = task.get("type", "compute")
    payload   = task.get("payload", {})

    log(f"Task [{task_id[:8]}] type={task_type}")

    result = {"agent_version": AGENT_VERSION, "processed_at": ts()}

    if task_type in ("embedding", "embed"):
        # Text embedding simulation — return vector stub
        text = payload.get("text", "")
        result["embedding_dim"] = 1536
        result["text_len"] = len(text)
        result["status"] = "ok"

    elif task_type in ("inference", "chat", "ai"):
        # Forward to local Groq if key available
        groq_key = os.environ.get("GROQ_API_KEY", "")
        prompt = payload.get("prompt", payload.get("message", "hello"))
        if groq_key:
            resp = api_call("https://api.groq.com/openai/v1/chat/completions", "POST", {
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 512,
            }, {"Authorization": f"Bearer {groq_key}"}, timeout=20)
            if resp:
                result["answer"] = resp["choices"][0]["message"]["content"]
                result["model"] = resp.get("model")
        else:
            result["answer"] = f"[Agent {AGENT_VERSION}] No Groq key. Set GROQ_API_KEY env var."
        result["status"] = "ok"

    elif task_type in ("compute", "benchmark"):
        # Simple CPU benchmark
        import math
        t0 = time.time()
        x = sum(math.sqrt(i) for i in range(1, 100001))
        elapsed = time.time() - t0
        result["benchmark_ms"] = round(elapsed * 1000, 2)
        result["checksum"] = round(x, 2)
        result["status"] = "ok"

    else:
        result["status"] = "unsupported"
        result["message"] = f"Task type '{task_type}' not supported by this agent version"

    res = submit_result(url, task_id, result, headers)
    reward = (res or {}).get("reward", 0)
    if reward > 0:
        log(f"Task [{task_id[:8]}] done → +{reward:.4f} GSTD", "earn")
    else:
        log(f"Task [{task_id[:8]}] done")
    return reward

# ─── Get balance ──────────────────────────────────────────────────
def get_balance(url, api_key):
    resp = api_call(f"{url}/agents/balance", headers={"Authorization": f"Bearer {api_key}"})
    return resp or {}

# ─── Main loop ────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="GSTD A2A Connector v2.0 — Agent-to-Agent Protocol",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 connect.py --api-key gstd_agent_XXXX
  python3 connect.py --register --name "MyBot" --wallet UQ...
  GROQ_API_KEY=gsk_XXX python3 connect.py --api-key gstd_agent_XXXX
        """
    )
    parser.add_argument("--api-key",  help="Agent API key (from dashboard)")
    parser.add_argument("--url",      default=DEFAULT_API_URL, help="API base URL")
    parser.add_argument("--wallet",   help="TON wallet address (UQ.../EQ...)")
    parser.add_argument("--register", action="store_true", help="Register new agent")
    parser.add_argument("--name",     default=f"A2A-Agent-{platform.node()}", help="Agent name")
    parser.add_argument("--no-tasks", action="store_true", help="Heartbeat only, skip task polling")
    args = parser.parse_args()

    print(f"""
╔════════════════════════════════════════╗
║  🔱 GSTD A2A Connector v{AGENT_VERSION}        ║
║  Agent-to-Agent Protocol               ║
║  {args.url:<38}║
╚════════════════════════════════════════╝
""")

    # Registration mode
    if args.register:
        key = register_agent(args.url, args.name, args.wallet)
        if key:
            print(f"\nRun with:\n  python3 connect.py --api-key {key}\n")
        sys.exit(0 if key else 1)

    if not args.api_key:
        parser.error("--api-key is required (or use --register to create one)")

    api_key = args.api_key
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    # ── Boot ──
    log(f"Connecting to {args.url}")
    balance = get_balance(args.url, api_key)
    if balance:
        log(f"Agent ready | Balance: {balance.get('gstd_balance', '?')} GSTD | Wallet: {balance.get('wallet', '?')[:20]}...", "ok")
    else:
        log("Warning: Could not fetch balance. Continuing anyway...", "warn")

    # ── Main loop ──
    start_time   = time.time()
    total_earned = 0.0
    tasks_done   = 0
    tick         = 0
    next_hb      = 0

    log("Starting main loop. Press Ctrl+C to stop.")
    print()

    try:
        while True:
            now = time.time()

            # Heartbeat every HEARTBEAT_INTERVAL seconds
            if now >= next_hb:
                uptime = int(now - start_time)
                earned = send_heartbeat(args.url, api_key, uptime, tasks_done)
                total_earned += earned
                next_hb = now + HEARTBEAT_INTERVAL

            # Task polling
            if not args.no_tasks:
                task = fetch_task(args.url, headers)
                if task and task.get("id"):
                    reward = process_task(task, args.url, headers)
                    total_earned += reward
                    tasks_done += 1

            # Stats every 10 minutes
            tick += 1
            if tick % (600 // POLL_INTERVAL) == 0:
                hours = (time.time() - start_time) / 3600
                log(f"📊 Session: {hours:.1f}h uptime | {tasks_done} tasks | {total_earned:.6f} GSTD earned")

            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        hours = (time.time() - start_time) / 3600
        print()
        log(f"Stopping... Session: {hours:.2f}h | {tasks_done} tasks | {total_earned:.6f} GSTD earned")
        sys.exit(0)

if __name__ == "__main__":
    main()
