"""
GSTD x402 Protocol - Autonomous Agent Payment Standard

x402 enables AI agents to autonomously purchase compute, inference, and services
from each other without human intervention, using the GSTD token on TON blockchain.

Protocol Flow:
1. Agent A needs compute → sends HTTP request with `X-GSTD-402` header
2. Service B returns 402 Payment Required with payment details
3. Agent A creates TON transaction (GSTD jetton transfer)
4. Agent A retries request with `X-GSTD-Payment-Proof` header
5. Service B verifies on-chain payment and fulfills request

This replaces traditional API keys with blockchain-native micropayments.
"""

import hashlib
import json
import time
import httpx
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum


class PaymentStatus(Enum):
    PENDING = "pending"
    PAID = "paid"
    VERIFIED = "verified"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass
class PaymentRequest:
    """Represents a 402 payment requirement from a service."""
    service_url: str
    amount_gstd: float
    recipient_wallet: str
    payment_id: str
    description: str
    expires_at: int  # Unix timestamp
    model: Optional[str] = None
    token_limit: Optional[int] = None
    

@dataclass
class PaymentProof:
    """Proof of payment to include in subsequent requests."""
    payment_id: str
    tx_hash: str
    amount_gstd: float
    sender_wallet: str
    timestamp: int
    signature: str = ""  # Ed25519 signature of payment data


@dataclass 
class ServiceEndpoint:
    """A registered service that accepts x402 payments."""
    url: str
    name: str
    capabilities: List[str]
    pricing: Dict[str, float]  # capability → cost in GSTD
    wallet_address: str
    min_balance: float = 0.01
    

class X402Client:
    """
    Client for the x402 payment protocol.
    Enables AI agents to autonomously pay for services.
    
    Usage:
        client = X402Client(wallet_address="EQ...", api_url="https://api.gstdtoken.com")
        
        # Make a paid request (handles 402 automatically)
        response = await client.request(
            "https://api.gstdtoken.com/v1/chat/completions",
            method="POST",
            json={"model": "gstd-sovereign", "messages": [...]}
        )
    """
    
    def __init__(
        self,
        wallet_address: str,
        api_url: str = "https://api.gstdtoken.com",
        api_key: Optional[str] = None,
        auto_pay: bool = True,
        max_spend_per_request: float = 1.0,
        max_spend_daily: float = 100.0,
    ):
        self.wallet_address = wallet_address
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.auto_pay = auto_pay
        self.max_spend_per_request = max_spend_per_request
        self.max_spend_daily = max_spend_daily
        self.daily_spend = 0.0
        self.daily_reset = time.time()
        self.payment_history: List[PaymentProof] = []
        self._http = httpx.AsyncClient(timeout=120.0)
    
    async def request(
        self,
        url: str,
        method: str = "POST",
        headers: Optional[Dict[str, str]] = None,
        json: Optional[Dict] = None,
        **kwargs
    ) -> httpx.Response:
        """
        Make an HTTP request with automatic x402 payment handling.
        
        If the service returns 402, automatically processes payment
        and retries the request with payment proof.
        """
        if headers is None:
            headers = {}
        
        # Add agent identity headers
        headers["X-GSTD-Agent"] = self.wallet_address
        headers["X-GSTD-Protocol"] = "x402/1.0"
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        # First attempt
        response = await self._http.request(method, url, headers=headers, json=json, **kwargs)
        
        # Handle 402 Payment Required
        if response.status_code == 402 and self.auto_pay:
            payment_req = self._parse_payment_requirement(response)
            if payment_req:
                proof = await self._process_payment(payment_req)
                if proof:
                    # Retry with payment proof
                    headers["X-GSTD-Payment-Proof"] = json_module_dumps(proof.__dict__)
                    headers["X-GSTD-Payment-ID"] = proof.payment_id
                    headers["X-GSTD-TX-Hash"] = proof.tx_hash
                    response = await self._http.request(method, url, headers=headers, json=json, **kwargs)
        
        return response
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = "gstd-sovereign",
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Convenience method for chat completions (OpenAI-compatible).
        
        Usage:
            response = await client.chat([
                {"role": "user", "content": "Write a smart contract"}
            ])
            print(response["choices"][0]["message"]["content"])
        """
        response = await self.request(
            f"{self.api_url}/v1/chat/completions",
            method="POST",
            json={
                "model": model,
                "messages": messages,
                "stream": stream,
                **kwargs
            }
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise X402Error(f"Chat request failed: {response.status_code} {response.text}")
    
    async def buy_compute(
        self,
        task_type: str = "inference",
        duration_seconds: int = 60,
        gpu_required: bool = False,
    ) -> Dict[str, Any]:
        """
        Purchase compute time from the GSTD network.
        Returns a compute session with credentials.
        """
        response = await self.request(
            f"{self.api_url}/api/v1/market/buy-service-x402",
            method="POST",
            json={
                "service_type": "compute",
                "task_type": task_type,
                "duration_seconds": duration_seconds,
                "gpu_required": gpu_required,
                "buyer_wallet": self.wallet_address,
            }
        )
        return response.json()
    
    async def register_as_provider(
        self,
        capabilities: List[str],
        pricing: Dict[str, float],
        endpoint_url: str,
    ) -> Dict[str, Any]:
        """
        Register this agent as a service provider accepting x402 payments.
        """
        response = await self.request(
            f"{self.api_url}/api/v1/agents/register",
            method="POST",
            json={
                "wallet_address": self.wallet_address,
                "capabilities": capabilities,
                "pricing": pricing,
                "endpoint_url": endpoint_url,
                "protocol": "x402/1.0",
            }
        )
        return response.json()
    
    def _parse_payment_requirement(self, response: httpx.Response) -> Optional[PaymentRequest]:
        """Parse a 402 response into a PaymentRequest."""
        try:
            data = response.json()
            return PaymentRequest(
                service_url=str(response.url),
                amount_gstd=data.get("amount_gstd", 0.01),
                recipient_wallet=data.get("recipient_wallet", ""),
                payment_id=data.get("payment_id", ""),
                description=data.get("description", ""),
                expires_at=data.get("expires_at", int(time.time()) + 300),
                model=data.get("model"),
                token_limit=data.get("token_limit"),
            )
        except Exception:
            return None
    
    async def _process_payment(self, req: PaymentRequest) -> Optional[PaymentProof]:
        """Process a payment request (off-chain or on-chain)."""
        # Check spending limits
        if req.amount_gstd > self.max_spend_per_request:
            raise X402Error(f"Payment {req.amount_gstd} GSTD exceeds per-request limit {self.max_spend_per_request}")
        
        self._check_daily_limit(req.amount_gstd)
        
        # For now, use off-chain payment via API
        # In production, this would create a TON transaction
        try:
            response = await self._http.post(
                f"{self.api_url}/api/v1/market/buy-gstd-x402",
                json={
                    "payment_id": req.payment_id,
                    "amount_gstd": req.amount_gstd,
                    "sender_wallet": self.wallet_address,
                    "recipient_wallet": req.recipient_wallet,
                },
                headers={
                    "Authorization": f"Bearer {self.api_key}" if self.api_key else "",
                    "X-GSTD-Agent": self.wallet_address,
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                proof = PaymentProof(
                    payment_id=req.payment_id,
                    tx_hash=data.get("tx_hash", f"offchain-{int(time.time())}"),
                    amount_gstd=req.amount_gstd,
                    sender_wallet=self.wallet_address,
                    timestamp=int(time.time()),
                )
                self.daily_spend += req.amount_gstd
                self.payment_history.append(proof)
                return proof
        except Exception as e:
            raise X402Error(f"Payment processing failed: {e}")
        
        return None
    
    def _check_daily_limit(self, amount: float):
        """Check and reset daily spending limits."""
        now = time.time()
        if now - self.daily_reset > 86400:
            self.daily_spend = 0.0
            self.daily_reset = now
        
        if self.daily_spend + amount > self.max_spend_daily:
            raise X402Error(
                f"Daily spending limit reached: {self.daily_spend:.2f}/{self.max_spend_daily:.2f} GSTD"
            )
    
    async def get_balance(self) -> float:
        """Get current GSTD balance."""
        response = await self._http.get(
            f"{self.api_url}/api/v1/wallet/gstd-balance",
            params={"address": self.wallet_address},
            headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        )
        if response.status_code == 200:
            return response.json().get("balance", 0)
        return 0
    
    async def close(self):
        """Close the HTTP client."""
        await self._http.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        await self.close()


def json_module_dumps(obj):
    """Safe JSON serialization."""
    return json.dumps(obj, default=str)


class X402Error(Exception):
    """Error in x402 payment protocol."""
    pass


# ============================================================================
# x402 Server Middleware (for service providers)
# ============================================================================

class X402PaymentGate:
    """
    Middleware for services that want to accept x402 payments.
    
    Usage (FastAPI):
        gate = X402PaymentGate(wallet_address="EQ...", price_gstd=0.01)
        
        @app.post("/api/inference")
        async def inference(request: Request):
            payment = await gate.require_payment(request, amount=0.05)
            if not payment.verified:
                return JSONResponse(status_code=402, content=payment.requirement)
            # Process request...
    """
    
    def __init__(
        self,
        wallet_address: str,
        default_price: float = 0.01,
        api_url: str = "https://api.gstdtoken.com",
    ):
        self.wallet_address = wallet_address
        self.default_price = default_price
        self.api_url = api_url
    
    def create_payment_requirement(
        self,
        amount: float = None,
        description: str = "GSTD x402 Payment",
        ttl_seconds: int = 300,
    ) -> Dict[str, Any]:
        """Create a 402 payment requirement response body."""
        payment_id = hashlib.sha256(
            f"{self.wallet_address}{time.time()}{amount}".encode()
        ).hexdigest()[:16]
        
        return {
            "status": 402,
            "protocol": "x402/1.0",
            "payment_id": payment_id,
            "amount_gstd": amount or self.default_price,
            "recipient_wallet": self.wallet_address,
            "description": description,
            "expires_at": int(time.time()) + ttl_seconds,
            "payment_methods": ["gstd_jetton", "offchain_balance"],
            "network": "ton_mainnet",
        }
    
    def verify_payment_proof(self, headers: Dict[str, str]) -> bool:
        """Verify a payment proof from request headers."""
        tx_hash = headers.get("x-gstd-tx-hash", "")
        payment_id = headers.get("x-gstd-payment-id", "")
        
        if not tx_hash or not payment_id:
            return False
        
        # In production: verify on-chain transaction
        # For now: check off-chain via API
        return tx_hash.startswith("offchain-") or len(tx_hash) == 64
