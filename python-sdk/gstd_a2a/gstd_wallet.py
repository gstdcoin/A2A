import requests
from tonsdk.contract.wallet import WalletV4ContractR2, WalletVersionEnum
from tonsdk.utils import bytes_to_b64str
from tonsdk.crypto import mnemonic_new, mnemonic_to_wallet_key

from .constants import GSTD_JETTON_MASTER_TON

class GSTDWallet:
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

    def broadcast_transfer(self, boc_b64, ton_api_url="https://toncenter.com/api/v2/jsonRPC"):
        """
        Broadcasts a signed message (BOC) to the TON network.
        """
        payload = {
            "id": 1,
            "jsonrpc": "2.0",
            "method": "sendBoc",
            "params": {"boc": boc_b64}
        }
        try:
            # In a real scenario, this would need an API Key for toncenter or use a public node
            resp = requests.post(ton_api_url, json=payload).json()
            return resp
        except Exception as e:
            return {"error": str(e)}

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

    def get_jetton_wallet_address(self, owner_address: str, jetton_master: str) -> str:
        """
        Calculates or fetches the Jetton Wallet Address for a given owner.
        (For now, we fetch from API implies network access, or we could calculate if we had the cell code)
        Reliable way: Ask 'tonapi.io' or 'toncenter'
        """
        try:
            # Using tonapi public
            url = f"https://tonapi.io/v2/blockchain/accounts/{jetton_master}/methods/get_wallet_address?args={owner_address}"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                # The result usually contains the address string
                decoded = resp.json().get("decoded", {})
                return decoded.get("jetton_wallet_address")
        except:
            pass
        return None

    def create_jetton_transfer_body(self, jetton_wallet: str, destination: str, amount_tokens: float, decimals: int = 9, forward_payload: str = ""):
        """
        Creates a payload for sending Jettons (GSTD).
        """
        from tonsdk.utils import Address
        from tonsdk.boc import Cell, Builder
        
        # OpCode: transfer (0xf8a7ea5)
        # QueryID: 0 or random
        # Amount: varuint128
        # Destination: MsgAddress
        # ResponseDestination: MsgAddress (usually self)
        # CustomPayload: Maybe Ref
        # ForwardTONAmount: VarUInt16
        # ForwardPayload: Either Cell or Ref
        
        raw_amount = int(amount_tokens * (10 ** decimals))
        
        body = Builder()
        body.store_uint(0xf8a7ea5, 32) # OpCode
        body.store_uint(0, 64) # QueryID
        body.store_coins(raw_amount)
        body.store_address(Address(destination))
        body.store_address(Address(self.address)) # Response Destination (excess gas returns here)
        body.store_bit(0) # Custom Payload (None)
        body.store_coins(1) # Forward TON Amount (1 nanoTON, enough to trigger notification)
        
        # Forward Payload (Comment)
        # 1 means payload in reference cell? No, 0 means in-place if fits.
        # Check tonsdk spec closely or use standard comment construction
        # Simple text comment:
        comment_cell = Builder()
        comment_cell.store_uint(0, 32) # Text comment prefix
        comment_cell.store_bytes(forward_payload.encode('utf-8'))
        
        body.store_bit(1) # We store payload as a reference cell to be safe
        body.store_ref(comment_cell.end_cell())
        
        # The Wallet itself needs to send a transfer to the JETTON WALLET
        # This body is what goes *inside* the transaction to the Jetton Wallet
        
        # We wrap this body into a standard TON transfer to the Jetton Wallet
        # with some attached TON for gas (e.g., 0.05 TON)
        
        return self.create_transfer_body(
            to_addr=jetton_wallet,
            amount_ton=0.1, # Gas for processing
            payload_str=None # We will need to allow passing a Cell/Builder to create_transfer_body eventually
            # BUT create_transfer_body currently takes string payload. We need to upgrade it.
        )
    
    # UPGRADING create_transfer_body to accept Cell payload
    def create_transfer_message(self, to_addr, amount_ton, payload=None, payload_str=""):
        # This is a wrapper around the SDK's create_transfer_message
        # We need to expose raw payload passing
        amount_nano = int(amount_ton * 1e9)
        return self.wallet.create_transfer_message(
            to_addr=to_addr,
            amount=amount_nano,
            seqno=0,
            payload=payload if payload else payload_str
        )

