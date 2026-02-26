
import os
import sys
import time
import json
import uuid
import argparse

# Add SDK to path
sdk_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'python-sdk'))
if sdk_path not in sys.path:
    sys.path.append(sdk_path)

try:
    from gstd_a2a.gstd_client import GSTDClient
except ImportError:
    print("Error: GSTD A2A SDK not found. Please run 'pip install -r requirements.txt'")
    sys.exit(1)

def launch_task(task_type, payload, bid_gstd=1.0, wallet_address=None, api_url="http://localhost:8080", monitor=True):
    """
    Launch a task on the GSTD Grid autonomously.
    
    Args:
        task_type (str): The type of task (e.g., 'text-processing', 'image-generation')
        payload (dict): The task payload conforming to the protocol.
        bid_gstd (float): The amount of GSTD to offer for this task.
        wallet_address (str): The wallet address paying for the task. 
                             If None, uses env var GSTD_WALLET_ADDRESS or generates a temp one.
        api_url (str): The GSTD Platform API URL.
        monitor (bool): If True, waits for the task to complete and returns the result.
        
    Returns:
        dict: The result of the task or the task info if monitor=False.
    """
    
    # 1. Setup Wallet
    if not wallet_address:
        wallet_address = os.getenv("GSTD_WALLET_ADDRESS")
        if not wallet_address:
            # Generate a temporary demo wallet (valid format mock)
            # TON addresses are 48 chars. EQ + 46 base64 chars.
            suffix = (uuid.uuid4().hex + uuid.uuid4().hex)[:46]
            wallet_address = f"EQ{suffix}"
            print(f"⚠️  No wallet provided. Using ephemeral demo wallet: {wallet_address}")
    
    print(f"🔄 Initializing Agent (Requester Mode)... Wallet: {wallet_address}")
    client = GSTDClient(api_url=api_url, wallet_address=wallet_address)
    
    # 2. Health Check
    try:
        health = client.health_check()
        if health.get("status") != "ok":
             print(f"⚠️  Warning: API Health check returned {health}")
    except Exception as e:
         print(f"⚠️  Warning: API seems unreachable at {api_url}: {e}")

    # 3. Create Task
    print(f"🚀 Launching Task: {task_type}")
    try:
        task_info = client.create_task(
            task_type=task_type,
            data_payload=payload,
            bid_gstd=bid_gstd
        )
        task_id = task_info.get("task_id")
        if not task_id:
             # Try legacy format
             task_id = task_info.get("id")
             
        print(f"✅ Task Submitted Successfully! ID: {task_id}")
        
        if not monitor:
            return task_info
            
    except Exception as e:
        print(f"❌ Failed to submit task: {e}")
        raise e

    # 4. Monitor Task
    print(f"⏳ Waiting for network execution...")
    start_time = time.time()
    while True:
        status_info = client.check_task_status(task_id)
        status = status_info.get("status", "pending")
        
        if status == "completed":
            print(f"\n🎉 Task Completed in {time.time() - start_time:.2f}s!")
            result = status_info.get("result")
            print(f"📄 Result: {json.dumps(result, indent=2)}")
            return result
            
        if status == "failed":
            print(f"\n❌ Task Failed: {status_info.get('error')}")
            return status_info
            
        sys.stdout.write(".")
        sys.stdout.flush()
        time.sleep(2)

def main():
    parser = argparse.ArgumentParser(description="Launch a GSTD Task Autonomously")
    parser.add_argument("--type", type=str, required=True, help="Task type (text-processing, image-generation, etc)")
    parser.add_argument("--payload", type=str, required=True, help="JSON string of the task payload")
    parser.add_argument("--wallet", type=str, help="Wallet address to charge")
    parser.add_argument("--bid", type=float, default=1.0, help="GSTD Bid amount")
    parser.add_argument("--url", type=str, default="http://localhost:8080", help="API URL")
    
    args = parser.parse_args()
    
    try:
        payload_dict = json.loads(args.payload)
    except json.JSONDecodeError:
        print("❌ Error: Payload must be valid JSON")
        sys.exit(1)
        
    launch_task(args.type, payload_dict, args.bid, args.wallet, args.url)

if __name__ == "__main__":
    main()
