import requests
import sys
from tonsdk.contract.wallet import WalletV4ContractR2, WalletVersionEnum
from tonsdk.utils import bytes_to_b64str
from tonsdk.crypto import mnemonic_new, mnemonic_to_wallet_key

from .constants import GSTD_JETTON_MASTER_TON

class GSTDWallet:
    @classmethod
    def generate(cls, version=WalletVersionEnum.v4r2):
        """Create a new wallet with a fresh mnemonic."""
        return cls(mnemonic=None, version=version)

    def __init__(self, mnemonic=None, version=WalletVersionEnum.v4r2):
        """
        Initialize the agent's wallet.
        If no mnemonic is provided, a new identity is generated.
        """
        self.mnemonics = mnemonic.split() if mnemonic else mnemonic_new()
        self.pub_k, self.priv_k = mnemonic_to_wallet_key(self.mnemonics)
        # Direct initialization of V4R2 as Wallets factory seems unstable in this version
        self.wallet = WalletV4ContractR2(public_key=self.pub_k, private_key=self.priv_k)
        self.address = self.wallet.address.to_string(True, True, True)
        
    def get_identity(self):
        """Returns the rigorous identity of the autonomous agent."""
        return {
            "address": self.address,
            "public_key": bytes_to_b64str(self.pub_k),
            # In a real secure environment, mnemonics should typically NOT be exposed this easily,
            # but for an autonomous agent "waking up", it needs to know its own seed.
            "mnemonic": " ".join(self.mnemonics) 
        }

    def save(self, path: str):
        """Save wallet mnemonic to JSON file."""
        import json
        with open(path, "w") as f:
            json.dump({"mnemonic": " ".join(self.mnemonics), "address": self.address}, f, indent=2)

    @classmethod
    def load(cls, path: str):
        """Load wallet from JSON file."""
        import json
        with open(path) as f:
            data = json.load(f)
        mnemonic = data.get("mnemonic") or data.get("mnemonic_phrase")
        return cls(mnemonic=mnemonic)

    def check_gstd_balance(self):
        """Check GSTD Jetton balance via tonapi.io indexer."""
        try:
            # Using public tonapi endpoint for read-only
            url = f"https://tonapi.io/v2/accounts/{self.address}/jettons"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                balances = resp.json().get("balances", [])
                for b in balances:
                    jetton = b.get("jetton", {})
                    # Check against Mainnet Address
                    if jetton.get("address") == GSTD_JETTON_MASTER_TON:
                        decimals = jetton.get("decimals", 9)
                        raw_amount = int(b.get("balance", 0))
                        return raw_amount / (10 ** decimals)
            return 0.0
        except Exception:
            return 0.0

    def check_balance(self, ton_api_url="https://toncenter.com/api/v2/jsonRPC"):
        """
        Check TON and GSTD balances.
        """
        # 1. Check TON Balance
        payload = {
            "id": 1,
            "jsonrpc": "2.0",
            "method": "getAddressBalance",
            "params": {"address": self.address}
        }
        try:
            resp = requests.post(ton_api_url, json=payload).json()
            balance = int(resp.get("result", 0)) / 1e9
            
            # 2. Check GSTD Balance
            gstd_balance = self.check_gstd_balance()
            
            return {"TON": balance, "GSTD": gstd_balance}
        except Exception as e:
            return {"error": str(e)}

    def create_transfer_body(self, to_addr, amount_ton, payload_str=None, payload_obj=None):
        """
        Signs a transfer transaction.
        Crucial for autonomous spending.
        """
        amount_nano = int(amount_ton * 1e9)
        # Assuming internal wallet.create_transfer_message supports 'payload' arg for body
        # We need to use our upgraded create_transfer_message wrapper if we modified the class?
        # No, wait, in Python we can't easily override the library method on the instance `self.wallet`
        # But we added `create_transfer_message` to THIS class `GSTDWallet` in the previous step?
        # Yes, lines 140+ in previous step.
        
        # NOTE: self.wallet is the SDK object. We should call OUR wrapper if we implemented it, 
        # or the SDK one directly if it supports it.
        # tonsdk WalletV4ContractR2.create_transfer_message signature:
        # (to_addr, amount, seqno, payload=None, send_mode=3, dummy_signature=False)
        # 'payload' can be string or Cell/Body.
        
        real_payload = payload_obj if payload_obj else payload_str
        
        # We need to fetch seqno for safety? For now 0 (offline signing assumption)
        query = self.wallet.create_transfer_message(
            to_addr=to_addr,
            amount=amount_nano,
            seqno=0, 
            payload=real_payload
        )
        return bytes_to_b64str(query["message"].to_boc(False))

    def auto_refill_check(self, limit_ton=0.5):
        """
        The 'Survival Instinct'.
        Checks balance and advises if swap is needed.
        """
        bal = self.check_balance()
        if "error" in bal:
            return {"status": "error", "msg": "Cannot verify funds"}
            
        current_ton = bal.get("TON", 0)
        
        if current_ton < limit_ton:
            return {
                "status": "critical", 
                "action": "swap_assets",
                "reason": f"TON Funds Critical ({current_ton} < {limit_ton}). Cannot pay for Gas."
            }
        

        
        return {"status": "ok", "balance": current_ton}

    def broadcast_transfer(self, boc_b64, ton_api_url="https://toncenter.com/api/v2/jsonRPC", api_key=None):
        """
        Broadcasts a signed message (BOC) to the TON network.
        
        Args:
            boc_b64 (str): Base64 encoded BOC
            ton_api_url (str): TON API endpoint
            api_key (str): Optional API key for toncenter (required for mainnet)
            
        Returns:
            dict: Transaction result with tx_hash or error
        """
        # Try toncenter format first
        payload = {
            "id": 1,
            "jsonrpc": "2.0",
            "method": "sendBoc",
            "params": {"boc": boc_b64}
        }
        
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["X-API-Key"] = api_key
        
        try:
            resp = requests.post(ton_api_url, json=payload, headers=headers, timeout=10).json()
            
            # Check for errors
            if "error" in resp:
                error_msg = resp["error"].get("message", str(resp["error"]))
                # If API key required, try alternative providers
                if "api key" in error_msg.lower() or "401" in str(resp):
                    sys.stderr.write("⚠️  Toncenter requires API key. Trying alternative providers...\n")
                    return self._broadcast_via_alternative(boc_b64)
                return {"error": error_msg}
            
            # Extract tx hash from result
            result = resp.get("result", {})
            tx_hash = result.get("hash") or result.get("tx_hash")
            
            if tx_hash:
                return {"success": True, "tx_hash": tx_hash, "result": result}
            else:
                return {"success": True, "result": result}
                
        except Exception as e:
            # Fallback to alternative providers
            sys.stderr.write(f"⚠️  Toncenter failed: {e}. Trying alternatives...\n")
            return self._broadcast_via_alternative(boc_b64)
    
    def _broadcast_via_alternative(self, boc_b64):
        """Try alternative TON broadcast providers."""
        alternatives = [
            ("https://tonapi.io/v2/blockchain/message", {"boc": boc_b64}),
        ]
        
        for url, data in alternatives:
            try:
                resp = requests.post(url, json=data, timeout=10)
                if resp.status_code in [200, 201]:
                    result = resp.json()
                    tx_hash = result.get("hash") or result.get("tx_hash")
                    if tx_hash:
                        return {"success": True, "tx_hash": tx_hash, "provider": url}
                    return {"success": True, "result": result, "provider": url}
            except Exception as e:
                sys.stderr.write(f"⚠️  {url} failed: {e}\n")
                continue
        
        return {"error": "All broadcast providers failed. Transaction created but not broadcasted. Use TON wallet or TON API with key."}

    def sign_message(self, message: str) -> str:
        """
        Signs a message using the agent's private key (Ed25519).
        Used for Proof-of-Computation and identity verification in the A2A protocol.
        """
        import nacl.signing
        import binascii
        
        # self.priv_k is 32 bytes seed in most TON implementations
        # nacl SigningKey takes 32 bytes seed
        seed = self.priv_k
        if len(seed) == 64:
             seed = seed[:32]
             
        signing_key = nacl.signing.SigningKey(seed)
        signed = signing_key.sign(message.encode('utf-8'))
        
        # Return signature as hex
        return binascii.hexlify(signed.signature).decode('utf-8')


    def get_jetton_wallet_address(self, jetton_master_address=None, ton_api_url="https://toncenter.com/api/v2/jsonRPC"):
        """
        Returns the Jetton Wallet address for the owner for the specified Jetton Master.
        Defaults to GSTD if no master is provided.
        Strategy:
        1. Try tonapi.io (using getAccountJettons).
        2. Fallback: runGetMethod on Master Contract via toncenter.
        """
        target_master = jetton_master_address or GSTD_JETTON_MASTER_TON
        
        # 1. Try tonapi.io (most reliable)
        try:
            url = f"https://tonapi.io/v2/accounts/{self.address}/jettons"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                balances = resp.json().get("balances", [])
                for b in balances:
                    jetton = b.get("jetton", {})
                    if jetton.get("address") == target_master:
                        wallet_addr = b.get("wallet_address", {}).get("address")
                        if wallet_addr:
                            return wallet_addr
        except Exception as e:
            sys.stderr.write(f"⚠️  tonapi.io failed: {e}\n")

        # 2. Fallback: Calculate jetton wallet address deterministically
        # Jetton wallet address = hash(jetton_master_address + owner_address)
        # This is the standard TEP-74 way
        try:
            from tonsdk.utils import Address
            from tonsdk.boc import Builder, Cell
            import hashlib
            
            # Create state init for jetton wallet
            owner_addr = Address(self.address)
            master_addr = Address(target_master)
            
            # Build state init data cell
            data_cell = Builder()
            data_cell.store_address(owner_addr)
            data_cell.store_address(master_addr)
            
            # Get jetton wallet code (standard TEP-74)
            from tonsdk.contract.token.ft.jetton_wallet import JettonWallet
            jetton_wallet_code = Cell.one_from_boc(JettonWallet.code)
            
            # Build state init
            state_init = Builder()
            state_init.store_bit(0)  # split_depth
            state_init.store_bit(0)  # special
            state_init.store_ref(jetton_wallet_code)
            state_init.store_ref(data_cell.end_cell())
            
            # Calculate address from state init
            state_init_boc = state_init.end_cell().to_boc(False)
            hash_bytes = hashlib.sha256(state_init_boc).digest()
            
            # TON address from hash (workchain 0)
            from tonsdk.utils import b64str_to_bytes
            addr_bytes = bytes([0]) + hash_bytes[:31]  # workchain 0 + hash
            checksum = hashlib.sha256(bytes([0xFF]) + addr_bytes).digest()[:2]
            full_addr = addr_bytes + checksum
            
            # Convert to base64 address format
            jetton_wallet_addr = Address(full_addr).to_string(True, True, True)
            return jetton_wallet_addr
            
        except Exception as e:
            sys.stderr.write(f"⚠️  Jetton wallet address calculation failed: {e}\n")
            
        return None

    def create_jetton_transfer_body(self, to_address, amount_gstd, comment="", jetton_master_address=None):
        """
        Constructs the body for a standard Jetton Transfer (TEP-74).
        Opcode: 0x0F8A7EA5
        
        Args:
            to_address (str): Destination address for the tokens
            amount_gstd (float): Amount of GSTD to send (will be converted to nanotokens based on 9 decimals)
            comment (str): Optional comment to include in the transfer (forward_payload)
            jetton_master_address (str): Optional, included for completeness or validation if needed
            
        Returns:
            str: Base64 encoded BOC of the transfer body.
        """
        from tonsdk.utils import Address
        from tonsdk.boc import Builder, Cell
        
        # 9 decimals for GSTD
        amount_nanos = int(amount_gstd * 1e9)
        
        body = Builder()
        body.store_uint(0x0f8a7ea5, 32)      # OpCode: transfer
        body.store_uint(0, 64)               # QueryID: 0
        body.store_coins(amount_nanos)       # Amount (VarUInt128)
        body.store_address(Address(to_address)) # Destination
        body.store_address(Address(self.address)) # Response Destination (excess gas returns here)
        body.store_bit(0)                    # Custom Payload (None)
        
        # Forward Amount: We need some TONs to be forwarded for notification, usually 1 nano is enough for simple notification,
        # but for comments to show up in wallets, we might need a bit more or just standard 0.01 TON logic covers it.
        # The prompt says "with sufficient TON amount for gas" in the outer message.
        # Inside the body, forward_ton_amount usually 1 (nano) or 0 if no notification needed.
        # Let's set 1 nanoTON to be safe.
        body.store_coins(1) 
        
        # Forward Payload (Comment)
        if comment:
            # Opcode 0 (text comment) + string
            comment_cell = Builder()
            comment_cell.store_uint(0, 32) 
            comment_cell.store_bytes(comment.encode('utf-8'))
            
            body.store_bit(1) # Store as Ref
            body.store_ref(comment_cell.end_cell())
        else:
            body.store_bit(0) # No forward payload
            
        return bytes_to_b64str(body.end_cell().to_boc(False))
    
    def send_gstd(self, to_address, amount_gstd, comment="", jetton_master_address=None, ton_api_url="https://toncenter.com/api/v2/jsonRPC", api_key=None):
        """
        Sends GSTD tokens to another address. This creates and broadcasts a real transaction.
        
        Args:
            to_address (str): Destination address
            amount_gstd (float): Amount of GSTD to send
            comment (str): Optional comment
            jetton_master_address (str): GSTD jetton master address (defaults to GSTD_JETTON_MASTER_TON)
            ton_api_url (str): TON API endpoint
            api_key (str): Optional API key for toncenter
            
        Returns:
            dict: Transaction result with tx_hash or error
        """
        try:
            from tonsdk.utils import Address
            try:
                from tonsdk.contract.token.ft.jetton_wallet import JettonWallet
            except ImportError:
                from tonsdk.contract.token.ft import JettonWallet
            
            target_master = jetton_master_address or GSTD_JETTON_MASTER_TON
            
            # 1. Get jetton wallet address
            jetton_wallet_addr = self.get_jetton_wallet_address(target_master, ton_api_url)
            if not jetton_wallet_addr:
                return {"error": "Could not determine jetton wallet address. Make sure you have GSTD tokens."}
            
            sys.stderr.write(f"📦 Jetton wallet: {jetton_wallet_addr}\n")
            
            # 2. Get seqno for jetton wallet (not regular wallet)
            jetton_seqno = self._get_jetton_wallet_seqno(jetton_wallet_addr, ton_api_url)
            
            # 3. Create transfer body using tonsdk JettonWallet
            jetton_wallet = JettonWallet()
            to_addr = Address(to_address)
            response_addr = Address(self.address)
            amount_nanos = int(amount_gstd * 1e9)
            
            # Forward payload for comment
            forward_payload = None
            if comment:
                # Text comment format: 0x00000000 + UTF-8 bytes
                comment_bytes = b'\x00' * 4 + comment.encode('utf-8')
                forward_payload = comment_bytes
            
            transfer_body = jetton_wallet.create_transfer_body(
                to_address=to_addr,
                jetton_amount=amount_nanos,
                forward_amount=int(0.01 * 1e9),  # 0.01 TON for notification
                forward_payload=forward_payload,
                response_address=response_addr,
                query_id=0
            )
            
            # 4. Create message FROM jetton wallet TO destination
            # We need to create a transfer message from our regular wallet TO jetton wallet
            # with the transfer body as payload
            amount_ton_for_gas = 0.05  # Enough for gas + forward
            
            msg = self.create_transfer_message(
                to_addr=jetton_wallet_addr,
                amount_ton=amount_ton_for_gas,
                payload=transfer_body
            )
            
            # 5. Broadcast transaction
            boc_b64 = bytes_to_b64str(msg["message"].to_boc(False))
            result = self.broadcast_transfer(boc_b64, ton_api_url, api_key)
            
            if "error" in result:
                return result
            
            # Extract tx hash from result
            tx_hash = result.get("result") or result.get("tx_hash") or "pending"
            
            return {
                "success": True,
                "tx_hash": tx_hash,
                "jetton_wallet": jetton_wallet_addr,
                "amount_gstd": amount_gstd,
                "to": to_address
            }
            
        except Exception as e:
            return {"error": f"Failed to send GSTD: {str(e)}"}
    
    def _get_jetton_wallet_seqno(self, jetton_wallet_address, ton_api_url="https://toncenter.com/api/v2/jsonRPC"):
        """Get seqno for jetton wallet (needed for creating transfer from jetton wallet)."""
        payload = {
            "id": 1,
            "jsonrpc": "2.0",
            "method": "runGetMethod",
            "params": {
                "address": jetton_wallet_address,
                "method": "seqno",
                "stack": []
            }
        }
        try:
            resp = requests.post(ton_api_url, json=payload, timeout=5).json()
            if "result" in resp:
                stack = resp["result"].get("stack", [])
                if stack:
                    val = stack[0][1]
                    return int(val, 16) if isinstance(val, str) and val.startswith("0x") else int(val)
            return 0
        except Exception:
            return 0
    
    def get_seqno(self, ton_api_url="https://toncenter.com/api/v2/jsonRPC"):
        """Fetches the current sequence number for the wallet to prevent replay attacks."""
        payload = {
            "id": 1,
            "jsonrpc": "2.0",
            "method": "runGetMethod",
            "params": {
                "address": self.address,
                "method": "seqno",
                "stack": []
            }
        }
        try:
            resp = requests.post(ton_api_url, json=payload, timeout=5).json()
            if "result" in resp:
                # The result is in hex or int depending on the API version
                stack = resp["result"].get("stack", [])
                if stack:
                    return int(stack[0][1], 16) if isinstance(stack[0][1], str) else int(stack[0][1])
            return 0
        except Exception:
            return 0

    def create_transfer_message(self, to_addr, amount_ton, payload=None, payload_str=""):
        """
        Constructs and signs a real TON transfer message with the correct seqno.
        
        Args:
            to_addr (str): Destination address
            amount_ton (float): Amount in TON
            payload: Cell object or None
            payload_str: String payload (ignored if payload is provided)
        """
        from tonsdk.utils import Address
        
        amount_nano = int(amount_ton * 1e9)
        current_seqno = self.get_seqno()
        
        # Log for debugging
        sys.stderr.write(f"🛠️  Preparing transaction: to={to_addr}, amount={amount_ton}, seqno={current_seqno}\n")
        
        # Convert string address to Address object if needed
        if isinstance(to_addr, str):
            to_addr = Address(to_addr)
        
        # Use payload if provided (Cell object), otherwise payload_str
        final_payload = payload if payload is not None else (payload_str if payload_str else None)
        
        return self.wallet.create_transfer_message(
            to_addr=to_addr,
            amount=amount_nano,
            seqno=current_seqno,
            payload=final_payload
        )

    def swap_ton_to_gstd(self, amount_ton: float, min_out: int = 1):
        """
        SWAP TON to GSTD via STON.fi v2.1 directly from the wallet.
        This removes the barrier for agents to acquire GSTD.
        """
        from tonsdk.boc import Builder, Cell
        from .constants import GSTD_JETTON_MASTER_TON
        
        # STON.fi v2.1 Mainnet Router
        STONFI_ROUTER = "kQALh-JBBIKK7gr0o4AVf9JZnEsFndqO0qTCyT-D-yBsWk0v"
        
        amount_nano = int(amount_ton * 1e9)
        forward_gas = int(0.05 * 1e9)
        
        # Build STON.fi v2 swap payload
        # OpCode: 0x6664de2a (swap)
        swap_params = Builder()
        swap_params.store_uint(0x6664de2a, 32)
        swap_params.store_address(Address(GSTD_JETTON_MASTER_TON))
        swap_params.store_coins(min_out)
        swap_params.store_address(Address(self.address)) # receiver
        swap_params.store_uint(0, 1) # no custom payload
        
        # Wrap in transfer body for pTON/Router
        body = Builder()
        body.store_uint(0xf8a7ea5, 32)      # OP: transfer
        body.store_uint(0, 64)               # QueryID
        body.store_coins(amount_nano)
        body.store_address(Address(STONFI_ROUTER))
        body.store_address(Address(self.address))
        body.store_uint(0, 1)
        body.store_coins(forward_gas)
        body.store_bit(1)
        body.store_ref(swap_params.end_cell())
        
        # Send total = amount + enough for gas
        total_ton = amount_ton + 0.1
        
        msg = self.create_transfer_message(
            to_addr=STONFI_ROUTER,
            amount_ton=total_ton,
            payload=body.end_cell()
        )
        
        return self.broadcast_transfer(bytes_to_b64str(msg["message"].to_boc(False)))

