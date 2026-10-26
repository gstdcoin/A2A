"""Signed GSTD node monitor. Install this repository first: pip install -e ."""
import argparse
import os
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from gstd_a2a.gstd_client import GSTDClient


def create_client(wallet, api_url=None):
    origin = (api_url or os.getenv("GSTD_API_URL", "https://app.gstdtoken.com")).rstrip("/")
    if origin.endswith("/api/v1"):
        origin = origin[:-7]
    client = GSTDClient(api_url=origin, wallet_address=wallet)
    # Identity belongs to this installation, not to every device using the wallet.
    client.node_id = "a2a-py-" + client._get_node_signing_key().verify_key.encode().hex()[:24]
    return client


def main():
    parser = argparse.ArgumentParser(description="Monitor a signed GSTD node; does not claim tasks without an executor.")
    parser.add_argument("--wallet", default=os.getenv("GSTD_WALLET_ADDRESS"))
    parser.add_argument("--name", default="A2A-Agent")
    args = parser.parse_args()
    if not args.wallet:
        parser.error("provide --wallet or GSTD_WALLET_ADDRESS (public TON address only)")
    client = create_client(args.wallet)
    try:
        client.register_node(device_name=args.name, max_retries=1)
        print("Registered signed node. No executor configured: task polling is disabled.", flush=True)
        while True:
            if not client.send_heartbeat():
                print("Heartbeat failed; retrying after 180 seconds.", file=sys.stderr, flush=True)
            time.sleep(180)
    except KeyboardInterrupt:
        print("Node monitor stopped.")
    except Exception as error:
        parser.exit(1, str(error) + "\n")


if __name__ == "__main__":
    main()
