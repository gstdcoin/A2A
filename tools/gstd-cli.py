#!/usr/bin/env python3
import argparse
import sys
import json
import http.client
import os

DEFAULT_API_HOST = "app.gstdtoken.com"

class GSTDClient:
    def __init__(self, api_key=None):
        self.host = DEFAULT_API_HOST
        self.api_key = api_key or os.environ.get("GSTD_API_KEY")
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "GSTD-CLI/1.0",
        }
        if self.api_key:
            self.headers["X-API-Key"] = self.api_key

    def request(self, method, endpoint, body=None):
        conn = http.client.HTTPSConnection(self.host, 443)
        try:
            conn.request(method, f"/api/v1{endpoint}", body=json.dumps(body) if body else None, headers=self.headers)
            resp = conn.getresponse()
            data = resp.read().decode()
            if resp.status >= 400:
                print(f"Error {resp.status}: {data}", file=sys.stderr)
                return None
            return json.loads(data) if data else {}
        except Exception as e:
            print(f"Request failed: {e}", file=sys.stderr)
            return None
        finally:
            conn.close()

def main():
    parser = argparse.ArgumentParser(description="GSTD Sovereign CLI - Unified Intelligence Toolkit")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Status Command
    status_parser = subparsers.add_parser("status", help="Check network and agent status")
    
    # Task Command
    task_parser = subparsers.add_parser("task", help="Manage swarm tasks")
    task_parser.add_argument("action", choices=["list", "create", "info"])
    task_parser.add_argument("--prompt", help="Prompt for the task")
    task_parser.add_argument("--id", help="Task ID")

    # Wallet Command
    wallet_parser = subparsers.add_parser("wallet", help="Check GSTD balance and rewards")
    wallet_parser.add_argument("address", help="TON Wallet Address")

    args = parser.parse_args()
    client = GSTDClient()

    if args.command == "status":
        res = client.request("GET", "/system/integrity")
        if res:
            print(f"Network: {DEFAULT_API_HOST}")
            print(f"Status: Sovereign Swarm Online")
            print(f"Integrity Hash: {res.get('manifest_hash')[:16]}...")
        else:
            print("Status: Offline or Unreachable")

    elif args.command == "wallet":
        res = client.request("GET", f"/payments/balance/{args.address}")
        if res:
            print(f"Wallet: {args.address}")
            print(f"GSTD Balance: {res.get('balance_gstd', 0):.2f}")
            print(f"Total Staked: {res.get('staked_gstd', 0):.2f}")
        else:
            print("Failed to fetch wallet info.")

    elif args.command == "task":
        if args.action == "list":
            res = client.request("GET", "/marketplace/tasks")
            if res:
                print(f"{'ID':<10} {'Type':<15} {'Status':<10} {'Reward':<10}")
                for t in res[:10]:
                    print(f"{t.get('task_id', '')[:8]:<10} {t.get('task_type', '')[:15]:<15} {t.get('status', '')[:10]:<10} {t.get('reward', {}).get('amount_gstd', 0):<10}")
        elif args.action == "create":
            if not args.prompt:
                print("Error: --prompt required for task creation")
                return
            body = {
                "task_type": "chat_completion",
                "model": "gstd-swarm-v1",
                "input": {"prompt": args.prompt},
                "reward": {"amount_gstd": 1.0}
            }
            res = client.request("POST", "/tasks", body)
            if res:
                print(f"Task Created Successfully! ID: {res.get('task_id')}")
        elif args.action == "info":
            if not args.id:
                 print("Error: --id required")
                 return
            res = client.request("GET", f"/marketplace/tasks/{args.id}")
            if res:
                print(json.dumps(res, indent=2))

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
