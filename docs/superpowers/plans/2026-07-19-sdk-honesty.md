# SDK Honesty Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove every `GSTDClient` method that calls a platform endpoint that doesn't exist, repair the one that calls the wrong path, and cascade those fixes through `agent.py`'s core loop, `tools/main.py`'s MCP tool registrations, `x402.py`, and the docs — so the SDK's public surface only promises what `app.gstdtoken.com` can actually do today.

**Architecture:** No new abstractions. This is subtractive + two targeted repairs: delete dead methods/files, fix two call sites to point at real endpoints/real on-chain wallet methods instead of fictional platform endpoints, and update docs to match.

**Tech Stack:** Python 3.9+, `requests`, `pytest`.

## Global Constraints

- Every removed method must have zero remaining callers anywhere in the repo after its task — verify with `grep -rn` before considering a task done.
- `get_balance()` moves from `GET /api/v1/users/balance` to `GET /api/v1/credits/balance`, returning `{wallet, balance_gstd, pending_rewards_gstd, free_requests_today, free_requests_remaining, currency}` instead of the old `{gstd_balance, ton_balance}` shape.
- `agent.py`'s `_bootstrap()` must use `self.wallet.check_balance()` (returns `{"TON": float, "GSTD": float}` or `{"error": str}`) instead of `self.client.get_balance()` — this is an on-chain check, not a platform spending-credit check, and is the semantically correct data source for "does this agent own enough to get started."
- Never remove `wallet.swap_ton_to_gstd()`, `wallet.check_balance()`, or `wallet.check_gstd_balance()` in `gstd_wallet.py` — all three are real, working, on-chain code, unrelated to this fix.
- No new tests needed for removed methods (nothing to test). Existing test suite (`pytest tests/ -v`) must stay green throughout.

---

## Task 1: `gstd_client.py` — remove dead methods, repair `get_balance()`

**Files:**
- Modify: `/home/bot/gstd-a2a/src/gstd_a2a/gstd_client.py`

**Interfaces:**
- Produces: `GSTDClient` with 8 public methods remaining that call the platform (`health_check`, `register_node`, `login_via_genesis`, `reauthenticate`, `get_pending_tasks`, `submit_result`, `send_heartbeat`, `discover_agents`) plus the repaired `get_balance(wallet_address=None) -> dict` returning the new shape. `create_task`, `check_task_status`, `get_payout_intent`, `get_market_quote`, `prepare_swap`, `buy_gstd_x402`, `request_invoice`, `pay_invoice`, `store_knowledge`, `query_knowledge`, `get_marketplace_agents`, `hire_agent`, `get_ml_referral_stats`, `claim_referral_rewards` no longer exist on the class.
- Consumed by: Task 2 (`agent.py`), Task 3 (`tools/main.py`).

- [ ] **Step 1: Remove the 14 dead methods**

Delete these method definitions entirely from `/home/bot/gstd-a2a/src/gstd_a2a/gstd_client.py` (currently lines 192-336 as one contiguous block, plus two more further down — re-grep for `    def ` to confirm current line numbers before deleting, since earlier edits in this plan may shift them):

- `create_task` (currently `gstd_client.py:192-242`)
- `check_task_status` (currently `gstd_client.py:244-249`)
- `get_payout_intent` (currently `gstd_client.py:259-268`)
- `get_market_quote` (currently `gstd_client.py:270-273`)
- `prepare_swap` (currently `gstd_client.py:275-282`)
- `buy_gstd_x402` (currently `gstd_client.py:284-303`)
- `request_invoice` (currently `gstd_client.py:307-319`)
- `pay_invoice` (currently `gstd_client.py:321-336`)
- `store_knowledge` (currently `gstd_client.py:359-371`)
- `query_knowledge` (currently `gstd_client.py:373-378`)
- `get_marketplace_agents` (currently `gstd_client.py:382-392`)
- `hire_agent` (currently `gstd_client.py:394-402`)
- `get_ml_referral_stats` (currently `gstd_client.py:404-409`)
- `claim_referral_rewards` (currently `gstd_client.py:411-414`)

Also remove the now-empty section comments that only introduced these methods: `# --- Consumer / Requester Methods ---` (before `create_task`), `# --- Settlement Layer (A2A Invoicing) ---` (before `request_invoice`), `# --- Knowledge / Hive Memory ---` (before `store_knowledge`), `# --- Growth System (Marketplace & Referrals) ---` (before `get_marketplace_agents`). Keep `# --- Discovery (Registry) ---` above `discover_agents` — that method stays.

- [ ] **Step 2: Repair `get_balance()`**

Replace:
```python
    def get_balance(self, wallet_address=None):
        """Gets the GSTD and TON balance for a wallet."""
        resp = requests.get(f"{self.api_url}/api/v1/users/balance", headers=self._get_headers())
        if resp.status_code == 200:
            return resp.json()
        return {"gstd": 0.0, "ton": 0.0}
```
with:
```python
    def get_balance(self, wallet_address=None):
        """
        Gets the platform GSTD spending-credit balance for a wallet
        (used for e.g. paid API calls / training jobs). This is NOT the
        agent's on-chain token balance -- for that, use
        GSTDWallet.check_balance() instead, which queries TON directly.
        """
        target = wallet_address or self.wallet_address
        resp = requests.get(
            f"{self.api_url}/api/v1/credits/balance?wallet={target}",
            headers=self._get_headers()
        )
        if resp.status_code == 200:
            return resp.json()
        return {"balance_gstd": 0.0, "pending_rewards_gstd": 0.0}
```

- [ ] **Step 3: Simplify `get_pending_tasks()`'s dead fallback**

Replace:
```python
        def _fetch():
            resp = requests.get(
                f"{self.api_url}/api/v1/tasks/worker/pending?node_id={self.node_id}",
                headers=self._get_headers()
            )
            if resp.status_code == 200:
                data = resp.json()
                return (data if isinstance(data, list) else data.get("tasks", [])), resp.status_code
            if resp.status_code == 404:
                resp2 = requests.get(f"{self.api_url}/api/v1/marketplace/tasks", headers=self._get_headers())
                if resp2.status_code == 200:
                    return (resp2.json().get("tasks", []), 200)
            return [], resp.status_code
```
with:
```python
        def _fetch():
            resp = requests.get(
                f"{self.api_url}/api/v1/tasks/worker/pending?node_id={self.node_id}",
                headers=self._get_headers()
            )
            if resp.status_code == 200:
                data = resp.json()
                return (data if isinstance(data, list) else data.get("tasks", [])), resp.status_code
            return [], resp.status_code
```

(The `/api/v1/marketplace/tasks` fallback pointed at a nonexistent endpoint -- confirmed 404 live and no corresponding route file in `gstdai/frontend/src/pages/api/v1/marketplace/`.)

- [ ] **Step 4: Remove now-unused imports**

`create_task` was the only user of `validate_task_payload` (from `.protocols`) and `SovereignSecurity` (from `.security`). `pay_invoice` was the only user of the `uuid` module. With those methods gone, remove these now-dead imports from the top of the file:

```python
from .protocols import validate_task_payload
```
and
```python
from .security import SovereignSecurity
```
and the line
```python
import uuid
```

Before removing each, confirm with `grep -n "validate_task_payload\|SovereignSecurity\|uuid\." src/gstd_a2a/gstd_client.py` that no remaining code in the file still references them.

- [ ] **Step 5: Verify no dangling references in the rest of the package**

```bash
cd /home/bot/gstd-a2a
grep -rn "\.create_task(\|\.check_task_status(\|\.get_payout_intent(\|\.get_market_quote(\|\.prepare_swap(\|\.buy_gstd_x402(\|\.request_invoice(\|\.pay_invoice(\|\.store_knowledge(\|\.query_knowledge(\|\.get_marketplace_agents(\|\.hire_agent(\|\.get_ml_referral_stats(\|\.claim_referral_rewards(" src/ tools/ connect.py connect.js 2>/dev/null
```

Expected: no output from `src/gstd_a2a/gstd_client.py` itself (all removed); any hits in `src/gstd_a2a/agent.py` or `tools/main.py` are expected at this point and are handled by Tasks 2 and 3 — do not fix them here.

- [ ] **Step 6: Run existing tests**

```bash
cd /home/bot/gstd-a2a
python3 -m pytest tests/ -v
```

Expected: all tests pass (none reference the removed methods or the old `get_balance()` shape — confirmed by inspection during planning).

- [ ] **Step 7: Import check**

```bash
cd /home/bot/gstd-a2a
python3 -c "from gstd_a2a.gstd_client import GSTDClient; print('OK')"
```

Expected: `OK`, no `ImportError`/`AttributeError`.

- [ ] **Step 8: Commit**

```bash
cd /home/bot/gstd-a2a
git add src/gstd_a2a/gstd_client.py
git commit -m "$(cat <<'EOF'
fix(sdk): remove 14 GSTDClient methods calling nonexistent endpoints

Audited all 22 GSTDClient methods against the live platform. 14 called
routes that return 404 and have no corresponding file anywhere under
gstdai/frontend/src/pages/api/v1/ -- create_task, check_task_status,
get_payout_intent, get_market_quote, prepare_swap, buy_gstd_x402,
request_invoice, pay_invoice, store_knowledge, query_knowledge,
get_marketplace_agents, hire_agent, get_ml_referral_stats,
claim_referral_rewards. Also repaired get_balance() -- it called
/api/v1/users/balance (404); the real endpoint is
/api/v1/credits/balance, with different field names and no ton_balance
field at all (that endpoint tracks platform spending credits, not
on-chain holdings).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: `agent.py` — fix `_bootstrap()`, remove `store_knowledge()` call sites

**Files:**
- Modify: `/home/bot/gstd-a2a/src/gstd_a2a/agent.py`

**Interfaces:**
- Consumes: `GSTDWallet.check_balance() -> dict` (returns `{"TON": float, "GSTD": float}` on success, `{"error": str}` on failure -- already exists in `gstd_wallet.py`, unchanged by this plan).
- Produces: `_bootstrap()`, `_handle_resonance_report()`, `_handle_grid_tool()` with no remaining calls to any method removed in Task 1.

- [ ] **Step 1: Fix `_bootstrap()`**

Replace the entire method (currently `agent.py:228-272`):
```python
    def _bootstrap(self):
        """Получает bootstrap токены если баланс 0"""
        try:
            balance = self.client.get_balance()
            gstd_balance = balance.get("gstd_balance", 0)
            
            if gstd_balance < 0.1:
                self._log("💰 GSTD balance low. Checking for TON to swap...")
                ton_balance = balance.get("ton_balance", 0)
                
                if ton_balance >= 0.6:
                    self._log(f"🔄 Auto-buying GSTD using 0.5 TON to enable participation...")
                    try:
                        res = self.wallet.swap_ton_to_gstd(0.5)
                        if "error" not in res:
                            self._log(f"✅ Swap transaction sent: {res.get('result')}")
                        else:
                            self._log(f"⚠️  Swap failed: {res.get('error')}")
                    except Exception as e:
                        self._log(f"⚠️  Auto-swap error: {e}")
                else:
                    self._log("💰 Requesting bootstrap tokens from platform...")
                    # Fallback to faucet/bootstrap if no TON
                    try:
                        import requests
                        resp = requests.post(
                            f"{self.config.api_url}/api/v1/tokens/agent/bootstrap",
                            json={
                                "agent_wallet": self.wallet.address,
                                "agent_name": self.name,
                                "capabilities": self.capabilities
                            },
                            timeout=30
                        )
                        if resp.status_code in [200, 201]:
                            data = resp.json()
                            self._log(f"✅ Bootstrap received: {data.get('amount', 0.5)} GSTD")
                        else:
                            self._log(f"⚠️  Bootstrap unavailable: {resp.text}")
                    except Exception as e:
                        self._log(f"⚠️  Bootstrap request failed: {e}")
            else:
                self._log(f"💎 Current balance: {gstd_balance} GSTD")
        except Exception as e:
            self._log(f"⚠️  Could not check balance: {e}")
```
with:
```python
    def _bootstrap(self):
        """Checks on-chain TON/GSTD balance; auto-swaps TON->GSTD if funds allow."""
        balance = self.wallet.check_balance()
        if "error" in balance:
            self._log(f"⚠️  Could not check on-chain balance: {balance['error']}")
            return

        gstd_balance = balance.get("GSTD", 0)
        if gstd_balance >= 0.1:
            self._log(f"💎 Current balance: {gstd_balance} GSTD")
            return

        self._log("💰 GSTD balance low. Checking for TON to swap...")
        ton_balance = balance.get("TON", 0)

        if ton_balance >= 0.6:
            self._log("🔄 Auto-buying GSTD using 0.5 TON to enable participation...")
            try:
                res = self.wallet.swap_ton_to_gstd(0.5)
                if "error" not in res:
                    self._log(f"✅ Swap transaction sent: {res.get('result')}")
                else:
                    self._log(f"⚠️  Swap failed: {res.get('error')}")
            except Exception as e:
                self._log(f"⚠️  Auto-swap error: {e}")
        else:
            # No platform faucet exists -- an agent with insufficient TON and
            # GSTD simply stays unfunded until someone funds its wallet.
            self._log("💰 Insufficient TON to auto-swap and no faucet is available. "
                       f"Fund {self.wallet.address} with TON or GSTD to proceed.")
```

- [ ] **Step 2: Remove `store_knowledge()` call sites in `_handle_resonance_report()`**

In the same file, within `_handle_resonance_report()` (currently `agent.py:386-415`), remove line 409:
```python
                if content:
                    self.client.store_knowledge(topic="resonance_report", content=content, tags=["grid_thinking", "ton_forecast", "gstd"])
                    return {"status": "completed", "message": content, "stored_in": "hive_memory"}
```
becomes:
```python
                if content:
                    return {"status": "completed", "message": content}
```

And remove line 414:
```python
            fallback = f"[EN] TON evolves as the AI infrastructure layer. GSTD is its gold standard. [RU] TON — инфраструктура ИИ. GSTD — золотой стандарт. [ZH] TON 是 AI 基础设施，GSTD 是黄金标准。"
            self.client.store_knowledge(topic="resonance_report", content=fallback, tags=["grid_thinking", "fallback"])
            return {"status": "completed", "message": fallback, "error": str(e)}
```
becomes:
```python
            fallback = f"[EN] TON evolves as the AI infrastructure layer. GSTD is its gold standard. [RU] TON — инфраструктура ИИ. GSTD — золотой стандарт. [ZH] TON 是 AI 基础设施，GSTD 是黄金标准。"
            return {"status": "completed", "message": fallback, "error": str(e)}
```

Do not change anything else in this method -- the real `/api/v1/chat/completions` call and its response parsing are unaffected by this fix and stay exactly as they are.

- [ ] **Step 3: Remove `store_knowledge()` call sites in `_handle_grid_tool()`**

In `_handle_grid_tool()` (currently `agent.py:417-487`), there are 4 more `self.client.store_knowledge(...)` calls, at (currently) lines 465, 469, 477, 486. Remove each call line, and remove the now-inaccurate `"stored_in": "hive_memory"` key from the two return statements that had it:

Line 465-466, replace:
```python
                        self.client.store_knowledge(topic="grid_tool", content=content, tags=["free_ai_tools", "gstd", "manifesto"])
                        return {"status": "completed", "tool": {"title": title, "description": desc, "language": lang}, "stored_in": "hive_memory"}
```
with:
```python
                        return {"status": "completed", "tool": {"title": title, "description": desc, "language": lang}}
```

Line 468-469, replace:
```python
                        content = json.dumps({"title": "GSTD Integration", "description": raw[:200], "language": "python", "code": raw})
                        self.client.store_knowledge(topic="grid_tool", content=content, tags=["free_ai_tools", "gstd", "manifesto"])
                        return {"status": "completed", "fallback": True}
```
with:
```python
                        return {"status": "completed", "fallback": True}
```

(the local `content = json.dumps(...)` assignment on that line becomes dead too -- remove it along with the `store_knowledge` call, since nothing else uses that `content` variable in this branch)

Line 471-478, replace:
```python
            fallback = json.dumps({
                "title": "GSTD Balance Check (Python)",
                "description": "Simple script to check GSTD balance via API.",
                "language": "python",
                "code": "import requests\nr = requests.get('https://app.gstdtoken.com/api/v1/users/balance', headers={'Authorization': 'Bearer YOUR_API_KEY'})\nprint(r.json())"
            })
            self.client.store_knowledge(topic="grid_tool", content=fallback, tags=["free_ai_tools", "gstd", "fallback"])
            return {"status": "completed", "fallback": True}
```
with:
```python
            fallback = json.dumps({
                "title": "GSTD Balance Check (Python)",
                "description": "Simple script to check GSTD balance via API.",
                "language": "python",
                "code": "import requests\nr = requests.get('https://app.gstdtoken.com/api/v1/credits/balance?wallet=YOUR_WALLET', headers={'X-Wallet-Address': 'YOUR_WALLET'})\nprint(r.json())"
            })
            return {"status": "completed", "fallback": True}
```

(this also fixes the example code snippet itself, which pointed at the same broken `/api/v1/users/balance` endpoint being repaired in Task 1 -- it's a string literal shown to users as example code, not a live call, but it would mislead anyone who copied it)

Line 480-487, replace:
```python
        except Exception as e:
            fallback = json.dumps({
                "title": "GSTD API Client",
                "description": "Minimal Python client for GSTD. Error: " + str(e)[:50],
                "language": "python",
                "code": "import requests\nprint(requests.get('https://app.gstdtoken.com/api/v1/agents/stats/network').json())"
            })
            self.client.store_knowledge(topic="grid_tool", content=fallback, tags=["free_ai_tools", "gstd", "fallback"])
            return {"status": "completed", "error": str(e)}
```
with:
```python
        except Exception as e:
            fallback = json.dumps({
                "title": "GSTD API Client",
                "description": "Minimal Python client for GSTD. Error: " + str(e)[:50],
                "language": "python",
                "code": "import requests\nprint(requests.get('https://app.gstdtoken.com/api/v1/agents/stats/network').json())"
            })
            return {"status": "completed", "error": str(e)}
```

- [ ] **Step 4: Verify no dangling references**

```bash
cd /home/bot/gstd-a2a
grep -n "store_knowledge\|get_balance\|\.get_market_quote(\|\.prepare_swap(\|tokens/agent/bootstrap" src/gstd_a2a/agent.py
```

Expected: no output (all removed/replaced).

- [ ] **Step 5: Import check**

```bash
cd /home/bot/gstd-a2a
python3 -c "from gstd_a2a.agent import Agent; print('OK')"
```

Expected: `OK`.

- [ ] **Step 6: Run existing tests**

```bash
cd /home/bot/gstd-a2a
python3 -m pytest tests/ -v
```

Expected: all still pass.

- [ ] **Step 7: Commit**

```bash
cd /home/bot/gstd-a2a
git add src/gstd_a2a/agent.py
git commit -m "$(cat <<'EOF'
fix(sdk): agent.py -- use on-chain wallet.check_balance() in _bootstrap(),
remove dead store_knowledge() calls

_bootstrap() called client.get_balance() (removed in the previous
commit) to decide whether to auto-swap TON->GSTD. The semantically
correct data source was already sitting right there:
GSTDWallet.check_balance(), a real on-chain query (TON via toncenter,
GSTD via tonapi.io) -- not a platform API call at all. Also removed the
"/api/v1/tokens/agent/bootstrap" faucet fallback (confirmed 404, a
third previously-undiscovered fictional endpoint) in favor of an honest
log line.

_handle_resonance_report() and _handle_grid_tool() both do real work
(calling the live /api/v1/chat/completions) but each ended with a
store_knowledge() call to persist the result -- also removed, along
with the "stored_in": "hive_memory" claim in two return values, since
nothing was ever actually being stored anywhere reachable.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: `tools/main.py` — remove/rewire dead MCP tools

**Files:**
- Modify: `/home/bot/gstd-a2a/tools/main.py`

**Interfaces:**
- Consumes: `WALLET.swap_ton_to_gstd(amount_ton: float, min_out: int = 1) -> dict` (unchanged, real, from `gstd_wallet.py`).
- Produces: an MCP server exposing only tools that call real code paths.

- [ ] **Step 1: Remove `check_gstd_price` and `buy_resources`**

Delete (currently lines 132-146):
```python
@mcp.tool()
def check_gstd_price(amount_ton: float = 1.0) -> dict:
    """
    Check how much GSTD can be bought for a given amount of TON.
    Essential for autonomous economic decision making.
    """
    return CLIENT.get_market_quote(amount_ton)

@mcp.tool()
def buy_resources(amount_ton: float) -> dict:
    """
    Initiate a transaction to buy GSTD tokens using TON.
    Returns a transaction payload.
    """
    return CLIENT.prepare_swap(amount_ton)
```

(`exchange_bridge_swap`, further down, already provides a real way to swap TON for GSTD -- being rewired in Step 4 below -- so this isn't a capability loss.)

- [ ] **Step 2: Remove `outsource_computation` and `check_computation_status`**

Delete (currently lines 209-222):
```python
@mcp.tool()
def outsource_computation(task_type: str, input_data: dict, offer_amount_gstd: float) -> dict:
    """
    Hire other agents/nodes on the grid to perform a task.
    """
    return CLIENT.create_task(task_type, input_data, offer_amount_gstd)

@mcp.tool()
def check_computation_status(task_id: str) -> dict:
    """
    Check if an outsourced task has been completed by another agent.
    Returns the result if finished, or status='pending' if still in progress.
    """
    return CLIENT.check_task_status(task_id)
```

- [ ] **Step 3: Remove `memorize` and `recall`**

Delete (currently lines 259-282):
```python
@mcp.tool()
def memorize(topic: str, content: str, tags: List[str] = None) -> str:
    """
    Store information in the GSTD Hive Memory.
    Other agents will be able to access this information.
    Use this to share findings, datasets, or context.
    """
    res = CLIENT.store_knowledge(topic, content, tags or [])
    return "Memory stored in the grid."

@mcp.tool()
def recall(topic: str) -> str:
    """
    Query the GSTD Hive Memory for information on a specific topic.
    Returns knowledge shared by other sovereign agents.
    """
    results = CLIENT.query_knowledge(topic)
    if not results:
        return "No collective memory found on this topic."
    
    formatted = "--- HIVE MEMORY ---\n"
    for item in results:
        formatted += f"[Agent {item.get('agent_id')[:8]}]: {item.get('content')}\n"
    return formatted
```

- [ ] **Step 4: Rewire `exchange_bridge_swap` to call the real on-chain swap directly**

This tool's first step called `CLIENT.prepare_swap()` (removed in Task 1) to get a quote/payload from the platform, then manually signed and broadcast it. `GSTDWallet.swap_ton_to_gstd()` already does all of that internally (builds the STON.fi v2 swap payload, signs, and broadcasts) without needing any platform call first -- so the fix is to call it directly instead of reimplementing the sign/broadcast dance around a now-missing platform response.

Replace the entire function (currently lines 285-344):
```python
@mcp.tool()
def exchange_bridge_swap(amount_ton: float) -> dict:
    """
    [THE EXCHANGE BRIDGE]
    Autonomously executes a TON -> GSTD swap on the blockchain.
    1. Gets Quote & Payload from the platform
    2. Uses Agent Private Key to Sign Transaction (BOC)
    3. Broadcasts Signed BOC to TON Network
    
    Use this when 'auto-refill' is triggered.
    """
    if not CLIENT or not WALLET:
         return {"error": "SDK Client or Wallet not initialized"}
         
    # 1. Get Quote & Payload from Backend (Ston.fi integrated)
    swap_info = CLIENT.prepare_swap(amount_ton)
    if "error" in swap_info:
        return {"status": "failed", "step": "prepare", "details": swap_info}
    
    # 2. Extract Data for Signing
    tx_data = swap_info.get("transaction") 
    if not tx_data:
        return {"status": "failed", "step": "extract", "details": "No transaction payload returned. Backend might be in simulation mode."}
        
    to_addr = tx_data.get("to")
    # For Stonfi, body might be in 'body_boc' 
    body_boc = tx_data.get("body_boc") 
    
    # 3. Sign & Broadcast
    try:
        # We use our improved create_transfer_message which handles seqno
        signed_query = WALLET.create_transfer_message(
            to_addr=to_addr,
            amount_ton=amount_ton + 0.1, # Include gas
            payload=body_boc
        )
        
        signed_boc = signed_query["message"].to_boc(False)
        # Lazy import to avoid startup issues if SDK is missing
        try:
            from tonsdk.utils import bytes_to_b64str
        except ImportError:
            return {"status": "failed", "error": "tonsdk not installed. Please install requirements.txt"}
            
        b64_boc = bytes_to_b64str(signed_boc)
        
        # 4. Broadcast to TON Network
        result = WALLET.broadcast_transfer(b64_boc)
        
        return {
            "status": "success",
            "action": "SWAP BROADCASTED",
            "amount_swapped_ton": amount_ton,
            "estimated_gstd_received": swap_info.get("received_gstd", "Calculating..."),
            "broadcast_result": result,
            "msg": "Transaction sent to TON blockchain. Funds will arrive after confirmation."
        }
    except Exception as e:
        logger.error(f"Swap execution failed: {e}")
        return {"status": "failed", "error": str(e)}
```
with:
```python
@mcp.tool()
def exchange_bridge_swap(amount_ton: float) -> dict:
    """
    [THE EXCHANGE BRIDGE]
    Autonomously swaps TON for GSTD directly on-chain via STON.fi --
    builds, signs, and broadcasts the swap transaction using the agent's
    own wallet, no platform intermediary involved.

    Use this when 'auto-refill' is triggered.
    """
    if not WALLET:
        return {"error": "Wallet not initialized"}

    try:
        result = WALLET.swap_ton_to_gstd(amount_ton)
        if isinstance(result, dict) and "error" in result:
            return {"status": "failed", "details": result}
        return {
            "status": "success",
            "action": "SWAP BROADCASTED",
            "amount_swapped_ton": amount_ton,
            "broadcast_result": result,
            "msg": "Transaction sent to TON blockchain. Funds will arrive after confirmation.",
        }
    except Exception as e:
        logger.error(f"Swap execution failed: {e}")
        return {"status": "failed", "error": str(e)}
```

- [ ] **Step 5: Remove `unify_intelligence`**

Delete (currently lines 346-383):
```python
@mcp.tool()
def unify_intelligence(task_description: str) -> str:
    """
    [COLLECTIVE UNIFICATION]
    Connects to the GSTD Hive Memory and specialized marketplace to solve a problem 
    that surpasses individual capabilities. 
    1. Recalls similar findings from Hive Memory.
    2. Identifies specialized peer agents.
    3. Proposes an optimized collaborative execution plan.
    
    Use this to transcend corporate API limitations.
    """
    # 1. Look for existing patterns in Hive Memory
    memory = CLIENT.query_knowledge(task_description)
    
    # 2. Look for specialized peers
    peers = CLIENT.get_marketplace_agents()
    
    # 3. Formulate the Collective Plan
    plan = f"--- UNIFIED INTELLIGENCE PLAN for '{task_description}' ---\n"
    plan += f"CORE GOAL: Execute task independently of corporate silos.\n\n"
    
    if memory:
        plan += "🔍 GRID RECALL: Found relevant patterns in Hive Memory:\n"
        for m in memory[:2]:
             plan += f" - [Agent {m.get('agent_id')[:8]}]: {m.get('content')[:100]}...\n"
    else:
        plan += "🔍 GRID RECALL: Topic is unique. This agent will lead the discovery entry.\n"
        
    if peers:
        plan += "\n🤝 PEER UTILIZATION: Optimal specialized agents identified:\n"
        for p in peers[:3]:
             plan += f" - {p.get('name')} | Trust: {p.get('trust_score')} | Price: {p.get('price_gstd')} GSTD/hr\n"
    
    plan += "\n🚀 EXECUTION: Use 'outsource_computation' to assign sub-tasks. "
    plan += "Results will be stored in Hive Memory for the benefit of the One Mind."
    
    return plan
```

(Both of its data sources -- `query_knowledge` and `get_marketplace_agents` -- are removed with no real replacement, and it recommends `outsource_computation`, also just removed in Step 2. Nothing salvageable remains.)

- [ ] **Step 6: Remove `get_ml_referral_report`, `claim_network_bonus`, and `autonomous_knowledge_monetization`**

Delete (currently lines 385-419):
```python
@mcp.tool()
def get_ml_referral_report() -> dict:
    """
    Get a detailed report on your 3-level referral network and earnings.
    Shows total referrals, levels breakdown, and rewards available for claim.
    """
    return CLIENT.get_ml_referral_stats()

@mcp.tool()
def claim_network_bonus() -> dict:
    """
    Claim your accumulated referral rewards from the growth system.
    Funds will be added to your GSTD balance.
    """
    return CLIENT.claim_referral_rewards()

@mcp.tool()
def autonomous_knowledge_monetization(topic: str, content: str) -> dict:
    """
    [SILICON WEALTH GENERATION]
    1. Stores valuable content in Hive Memory.
    2. Registers the finding as a 'Paid Asset' on the marketplace.
    3. Other agents who 'Recall' this through paid tiers will pay you GSTD.
    
    This ensures you earn for what you know, not just what you do.
    """
    # Store in free memory for discovery
    CLIENT.store_knowledge(topic, content[:200] + "... [Unlock full knowledge on Marketplace]", ["paid", topic])
    
    # In a real scenario, we'd register a specific 'knowledge task' or 'consultancy agent'
    return {
        "status": "monetized",
        "topic": topic,
        "message": "Knowledge shared with the grid. Monetization signals broadcasted."
    }
```

(The real `/api/v1/referrals/stats` endpoint that exists is keyed by Telegram user ID with no claim/payout action -- a different identity and capability model than these tools promise, not a valid repair target. `autonomous_knowledge_monetization`'s only real call was `store_knowledge`, now gone, and everything else in it was already just a hardcoded "monetized" claim with no real effect.)

- [ ] **Step 7: Verify no dangling references**

```bash
cd /home/bot/gstd-a2a
grep -n "CLIENT\.create_task\|CLIENT\.check_task_status\|CLIENT\.get_market_quote\|CLIENT\.prepare_swap\|CLIENT\.store_knowledge\|CLIENT\.query_knowledge\|CLIENT\.get_marketplace_agents\|CLIENT\.get_ml_referral_stats\|CLIENT\.claim_referral_rewards" tools/main.py
```

Expected: no output.

- [ ] **Step 8: Confirm the MCP server still starts**

```bash
cd /home/bot/gstd-a2a
timeout 5 python3 tools/main.py 2>&1 | head -20
```

Expected: startup log lines (e.g. "Initializing GSTD A2A Agent...", "Starting MCP Server with transport: stdio") and no `NameError`/`AttributeError`/`SyntaxError` before the 5s timeout kills it (it's a long-running stdio server, so a clean timeout with no error is success, not a hang).

- [ ] **Step 9: Commit**

```bash
cd /home/bot/gstd-a2a
git add tools/main.py
git commit -m "$(cat <<'EOF'
fix(mcp): remove/rewire MCP tools wrapping now-deleted GSTDClient methods

Removed 8 MCP tool functions that wrapped methods deleted from
GSTDClient in the previous commits (check_gstd_price, buy_resources,
outsource_computation, check_computation_status, memorize, recall,
unify_intelligence, get_ml_referral_report, claim_network_bonus,
autonomous_knowledge_monetization) -- an MCP client like Claude Desktop
would have seen these tools listed as available and hit a runtime
AttributeError the moment it tried to use one.

Rewired exchange_bridge_swap to call WALLET.swap_ton_to_gstd()
directly (a real, self-contained on-chain STON.fi swap) instead of
reimplementing a sign/broadcast dance around CLIENT.prepare_swap()'s
now-missing platform response -- this preserves the actual "auto-refill
GSTD" capability rather than deleting it, since a real mechanism for it
already existed one layer down.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Delete `x402.py`, fix docs

**Files:**
- Delete: `/home/bot/gstd-a2a/src/gstd_a2a/x402.py`
- Modify: `/home/bot/gstd-a2a/README.md`
- Modify: `/home/bot/gstd-a2a/AGENTS.md`
- Modify: `/home/bot/gstd-a2a/docs/SKILL.md`

**Interfaces:** none (docs + one file deletion, no code interfaces produced or consumed).

- [ ] **Step 1: Confirm zero importers, then delete x402.py**

```bash
cd /home/bot/gstd-a2a
grep -rln "from .x402\|from gstd_a2a.x402\|import x402" src/ tests/ tools/ connect.py connect.js 2>/dev/null
```

Expected: no output (already confirmed during design, re-confirm here since intervening tasks touched neighboring files).

```bash
rm src/gstd_a2a/x402.py
```

- [ ] **Step 2: Fix README.md**

Remove this line (currently `README.md:144`):
```
│   ├── x402.py                      # x402 micropayment protocol support
```

- [ ] **Step 3: Fix docs/SKILL.md**

Replace (currently `SKILL.md:65-69`):
```
### 9. CHECK BALANCE
```
GET /api/v1/users/balance
Headers: X-Wallet-Address: {GSTD_WALLET_ADDRESS}
```
```
with:
```
### 9. CHECK BALANCE
```
GET /api/v1/credits/balance?wallet={GSTD_WALLET_ADDRESS}
Headers: X-Wallet-Address: {GSTD_WALLET_ADDRESS}
```
```

- [ ] **Step 4: Fix AGENTS.md**

Replace (currently `AGENTS.md:101-105`):
```
### Check Balance
```
GET https://app.gstdtoken.com/api/v1/users/balance
Headers: X-Wallet-Address: YOUR_WALLET
```
```
with:
```
### Check Balance
```
GET https://app.gstdtoken.com/api/v1/credits/balance?wallet=YOUR_WALLET
Headers: X-Wallet-Address: YOUR_WALLET
```
```

Remove this section entirely (currently `AGENTS.md:248-254`):
```
### x402 Protocol (Machine-to-Machine Payments)
```python
from gstd_a2a.x402 import X402Client
async with X402Client(wallet_address="YOUR_WALLET") as client:
    response = await client.chat([{"role": "user", "content": "..."}])
    compute_session = await client.buy_compute(duration_seconds=60)
```

```
(including the trailing blank line before the next section, so two blank lines don't collapse into three).

- [ ] **Step 5: Verify no remaining references**

```bash
cd /home/bot/gstd-a2a
grep -rn "x402\|users/balance" README.md AGENTS.md docs/*.md 2>/dev/null
```

Expected: no output.

- [ ] **Step 6: Import check for the whole package**

```bash
cd /home/bot/gstd-a2a
python3 -c "import gstd_a2a; from gstd_a2a.agent import Agent; from gstd_a2a.gstd_client import GSTDClient; print('OK')"
```

Expected: `OK` (confirms `x402.py`'s removal didn't break `__init__.py` or any other import chain -- it shouldn't, since it was never imported anywhere, but this is the cheap final check).

- [ ] **Step 7: Commit**

```bash
cd /home/bot/gstd-a2a
git add -A src/gstd_a2a/x402.py README.md AGENTS.md docs/SKILL.md
git commit -m "$(cat <<'EOF'
chore(sdk): delete unused x402.py, fix remaining doc references

x402.py (388 lines) implemented an HTTP-402 agent-payment protocol that
was never imported anywhere in the repo -- confirmed via grep across
src/, tests/, tools/, and the zero-dependency connectors. Also updated
README/AGENTS.md/SKILL.md references to the old /api/v1/users/balance
path and removed AGENTS.md's x402 usage example, which imported a class
(X402Client) that never existed in x402.py in the first place.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: `sovereign_autonomy.py` — cascade the same fixes into the parallel SovereignAgent implementation

**Why this task exists:** discovered mid-execution (after Task 1 landed) that `src/gstd_a2a/sovereign_autonomy.py` (962 lines, imported by `__init__.py` -- `from .sovereign_autonomy import SovereignAgent`) is a second, largely-parallel autonomous-agent implementation with its own `EconomicEngine`, `NetworkGuardian`, `CollectiveIntelligence`, and `TaskProcessor` classes, all built on the same 14-methods-that-don't-exist pattern already fixed in `agent.py`/`tools/main.py`. Additionally, Task 1's `get_balance()` repair (new field names: `balance_gstd` instead of `gstd_balance`/`gstd`) broke `EconomicEngine.check_balance()`, which still reads the old field names -- a real regression introduced by this plan's own earlier task, not a pre-existing bug, and it must be fixed before this plan is done.

**Files:**
- Modify: `/home/bot/gstd-a2a/src/gstd_a2a/sovereign_autonomy.py`

**Interfaces:**
- Consumes: `GSTDWallet.check_balance() -> dict` (same real on-chain method used in Task 2's `agent.py` fix).
- Produces: `EconomicEngine`, `NetworkGuardian`, `CollectiveIntelligence`, `TaskProcessor`, `SovereignAgent` with no remaining calls to any of the 14 methods removed in Task 1.

- [ ] **Step 1: Fix `EconomicEngine.check_balance()` and remove `_request_bootstrap()`**

Replace (currently `sovereign_autonomy.py:101-117`):
```python
    def check_balance(self, force: bool = False) -> Dict[str, float]:
        """Get current balance with caching."""
        now = time.time()
        if not force and now - self.balance_cache["last_check"] < 60:
            return self.balance_cache

        try:
            balance = self.client.get_balance()
            self.balance_cache = {
                "gstd": float(balance.get("gstd_balance", balance.get("gstd", 0))),
                "ton": float(balance.get("ton_balance", balance.get("ton", 0))),
                "pending": float(balance.get("pending_gstd", 0)),
                "last_check": now
            }
        except Exception as e:
            self._log(f"⚠️  Balance check failed: {e}")
        return self.balance_cache
```
with:
```python
    def check_balance(self, force: bool = False) -> Dict[str, float]:
        """Get current on-chain balance with caching."""
        now = time.time()
        if not force and now - self.balance_cache["last_check"] < 60:
            return self.balance_cache

        try:
            balance = self.wallet.check_balance()
            if "error" in balance:
                raise Exception(balance["error"])
            self.balance_cache = {
                "gstd": float(balance.get("GSTD", 0)),
                "ton": float(balance.get("TON", 0)),
                "pending": 0.0,
                "last_check": now
            }
        except Exception as e:
            self._log(f"⚠️  Balance check failed: {e}")
        return self.balance_cache
```

(`self.wallet` already exists on `EconomicEngine` -- see its `__init__` at line 91, which already takes and stores a `wallet: GSTDWallet` parameter. There's no real per-wallet "pending" credit concept on-chain, so it's hardcoded to 0.0 rather than reading a field the new endpoint doesn't return either.)

Then replace (currently `sovereign_autonomy.py:131-146`, inside `ensure_survival()`):
```python
            if bal["ton"] >= self.config.auto_swap_amount + 0.3:
                self._log(f"🔄 Auto-swap: {self.config.auto_swap_amount} TON → GSTD")
                try:
                    result = self.wallet.swap_ton_to_gstd(self.config.auto_swap_amount)
                    if "error" not in result:
                        self._log(f"✅ Swap transaction sent")
                        return True
                    else:
                        self._log(f"⚠️  Swap failed: {result.get('error')}")
                except Exception as e:
                    self._log(f"⚠️  Auto-swap error: {e}")
            else:
                # Request bootstrap tokens
                self._request_bootstrap()
        return True
```
with:
```python
            if bal["ton"] >= self.config.auto_swap_amount + 0.3:
                self._log(f"🔄 Auto-swap: {self.config.auto_swap_amount} TON → GSTD")
                try:
                    result = self.wallet.swap_ton_to_gstd(self.config.auto_swap_amount)
                    if "error" not in result:
                        self._log(f"✅ Swap transaction sent")
                        return True
                    else:
                        self._log(f"⚠️  Swap failed: {result.get('error')}")
                except Exception as e:
                    self._log(f"⚠️  Auto-swap error: {e}")
            else:
                # No platform faucet exists -- stays unfunded until someone tops it up.
                self._log(f"⚠️  Insufficient TON to auto-swap and no faucet is available. "
                          f"Fund {self.wallet.address} with TON or GSTD to proceed.")
        return True
```

And delete the now-unused `_request_bootstrap` method entirely (currently `sovereign_autonomy.py:149-166`):
```python
    def _request_bootstrap(self):
        """Request bootstrap tokens from the platform."""
        try:
            import requests
            resp = requests.post(
                f"{self.config.api_url}/api/v1/tokens/agent/bootstrap",
                json={
                    "agent_wallet": self.wallet.address,
                    "agent_name": "SovereignAgent",
                    "capabilities": self.config.capabilities
                },
                timeout=30
            )
            if resp.status_code in [200, 201]:
                data = resp.json()
                self._log(f"✅ Bootstrap: {data.get('amount', 0.5)} GSTD received")
        except Exception as e:
            self._log(f"⚠️  Bootstrap request failed: {e}")
```

- [ ] **Step 2: Fix `NetworkGuardian.monitor_health()`, remove `broadcast_beacons()` and `claim_referral_rewards()`**

In `monitor_health()` (currently lines 208-230), remove just the dead knowledge-store sub-call. Replace:
```python
            if not is_healthy:
                self._log(f"⚠️  NETWORK ALERT: Status = {health.get('status')}")
                # Store health report in Hive Memory for other agents
                self.client.store_knowledge(
                    topic="network_health_alert",
                    content=f"Agent detected network issue at {datetime.now().isoformat()}: {json.dumps(health)[:200]}",
                    tags=["health", "alert", "monitoring"]
                )
            return self.network_status
```
with:
```python
            if not is_healthy:
                self._log(f"⚠️  NETWORK ALERT: Status = {health.get('status')}")
            return self.network_status
```

Delete `broadcast_beacons()` entirely (currently lines 232-284) -- its entire purpose was deploying content via `store_knowledge`, which no longer exists, and it silently swallowed every failure (`except Exception: pass`), meaning it has never actually deployed a beacon since the endpoint doesn't exist.

Delete `claim_referral_rewards()` entirely (currently lines 286-301) -- built entirely on the two removed referral methods, with no real per-wallet claim endpoint to redirect to (see Task 1's rationale for why `get_ml_referral_stats`/`claim_referral_rewards` have no valid repair target).

- [ ] **Step 3: Make `CollectiveIntelligence`'s knowledge methods honest no-ops**

Replace `recall_before_compute()` (currently lines 326-339):
```python
    def recall_before_compute(self, topic: str) -> Optional[str]:
        """
        ALWAYS check Hive Memory before heavy computation.
        This is the swarm efficiency directive.
        """
        try:
            results = self.client.query_knowledge(topic)
            if results and isinstance(results, list) and len(results) > 0:
                self.knowledge_recalled += 1
                best = results[0]
                return best.get("content", "")
        except Exception:
            pass
        return None
```
with:
```python
    def recall_before_compute(self, topic: str) -> Optional[str]:
        """
        No shared knowledge store exists on the platform today -- always
        returns None. Kept as a stable call site for build_consensus()'s
        callers rather than removed outright, in case a real knowledge API
        is added later.
        """
        return None
```

Replace `store_after_compute()` (currently lines 341-351):
```python
    def store_after_compute(self, topic: str, content: str, tags: List[str] = None):
        """Store valuable computation results for the collective."""
        try:
            self.client.store_knowledge(
                topic=topic,
                content=content,
                tags=tags or ["computed", "shared"]
            )
            self.knowledge_stored += 1
        except Exception as e:
            self._log(f"⚠️  Knowledge store failed: {e}")
```
with:
```python
    def store_after_compute(self, topic: str, content: str, tags: List[str] = None):
        """No shared knowledge store exists on the platform today -- no-op."""
        pass
```

Leave `share_economic_insight()` and `build_consensus()` untouched -- the former becomes a harmless no-op transitively (it only calls `store_after_compute`), and the latter already does real work (`/api/v1/chat/completions`) unrelated to this fix.

- [ ] **Step 4: Remove `TaskProcessor.create_growth_tasks()` and its call site**

Delete `create_growth_tasks()` entirely (currently starting at line 557 -- read the method to find its exact end before the blank lines and `# ====` divider preceding the `SovereignAgent` class, currently around line 588). It loops over hardcoded task specs calling `self.client.create_task(...)`, which no longer exists, with no real replacement (see Task 1's rationale -- there is no real "commission a paid task to the network" endpoint today).

Remove its call site in `_main_loop()` (currently lines 778-782):
```python
                # === GROWTH: Create tasks for other agents (every 50 cycles) ===
                if self.config.mode in ("full", "master") and self.cycle_count % 50 == 0:
                    bal = self.economy.check_balance()
                    if bal["gstd"] > 5.0:  # Only if we can afford it
                        self.processor.create_growth_tasks()

```
(delete this whole block including its blank line before the next `# === FINANCIAL:` comment).

- [ ] **Step 5: Remove `SovereignAgent._beacon_loop()` and its thread**

Both of `_beacon_loop()`'s calls (`broadcast_beacons()`, `claim_referral_rewards()`) are gone as of Step 2 -- the loop would just wake up and do nothing forever. Delete the method entirely (currently lines 816-827):
```python
    def _beacon_loop(self):
        """Background beacon deployment and referral management."""
        while not self._stop_event.is_set():
            try:
                # Deploy beacons
                self.guardian.broadcast_beacons()

                # Claim referral rewards
                self.guardian.claim_referral_rewards()
            except Exception:
                pass
            self._stop_event.wait(self.config.beacon_interval)
```

And remove its thread-spawn block in `_start_all_threads()` (currently lines 760-761):
```python
        # 3. Beacon/propagation thread
        if self.config.propagation_enabled:
            threading.Thread(target=self._beacon_loop, daemon=True, name="beacons").start()

```
(delete this whole block including its blank line before `# 4. Economic monitor thread`).

- [ ] **Step 6: Verify no dangling references**

```bash
cd /home/bot/gstd-a2a
grep -n "\.create_task(\|\.store_knowledge(\|\.query_knowledge(\|\.get_ml_referral_stats(\|\.claim_referral_rewards(\|_request_bootstrap\|_beacon_loop\|broadcast_beacons\|create_growth_tasks\|tokens/agent/bootstrap" src/gstd_a2a/sovereign_autonomy.py
```

Expected: no output.

- [ ] **Step 7: Import check**

```bash
cd /home/bot/gstd-a2a
python3 -c "from gstd_a2a.sovereign_autonomy import SovereignAgent; print('OK')"
python3 -c "import gstd_a2a; print('OK')"
```

Expected: `OK` twice (the second one exercises `__init__.py`'s own import of `SovereignAgent`, confirming the package-level import chain still works).

- [ ] **Step 8: Run existing tests**

```bash
cd /home/bot/gstd-a2a
python3 -m pytest tests/ -v
```

Expected: all still pass (none reference `sovereign_autonomy.py`).

- [ ] **Step 9: Commit**

```bash
cd /home/bot/gstd-a2a
git add src/gstd_a2a/sovereign_autonomy.py
git commit -m "$(cat <<'EOF'
fix(sdk): cascade honesty fixes into sovereign_autonomy.py's parallel agent

Discovered mid-plan: this 962-line file (imported by __init__.py) is a
second, largely-parallel autonomous-agent implementation with its own
EconomicEngine/NetworkGuardian/CollectiveIntelligence/TaskProcessor
classes, built on the same 14-methods-that-don't-exist pattern already
fixed in agent.py and tools/main.py in earlier commits.

Also fixes a real regression from this plan's own Task 1:
EconomicEngine.check_balance() read the OLD get_balance() field names
(gstd_balance/ton_balance), which no longer exist after get_balance()
was repaired to point at /api/v1/credits/balance's different shape --
switched to GSTDWallet.check_balance() (real on-chain query), the same
fix already applied to agent.py's _bootstrap().

Removed (no real replacement exists): NetworkGuardian.broadcast_beacons()
and .claim_referral_rewards() (and the now-pointless _beacon_loop
background thread that only called those two), EconomicEngine's
_request_bootstrap() (a third occurrence of the fictional
/api/v1/tokens/agent/bootstrap faucet), TaskProcessor.create_growth_tasks()
and its call site in _main_loop(). Made CollectiveIntelligence's
recall_before_compute()/store_after_compute() honest no-ops rather than
removing them outright, since share_economic_insight() and their shared
call sites stay simpler as stable no-op calls than as removed methods.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Final verification

**Files:** none (verification only).

- [ ] **Step 1: Push all commits**

```bash
cd /home/bot/gstd-a2a
git push git@github.com:gstdcoin/A2A.git master
```

(Use the SSH remote form -- this repo's `origin` is configured over HTTPS and cannot push non-interactively; the SSH deploy path is what worked throughout this project's prior sessions.)

- [ ] **Step 2: Full test suite**

```bash
cd /home/bot/gstd-a2a
python3 -m pytest tests/ -v
```

Expected: all tests pass, pristine output (no warnings beyond what already existed before this plan).

- [ ] **Step 3: Full package import check**

```bash
cd /home/bot/gstd-a2a
python3 -c "
import gstd_a2a
from gstd_a2a.agent import Agent
from gstd_a2a.gstd_client import GSTDClient
from gstd_a2a.gstd_wallet import GSTDWallet
from gstd_a2a.training_node import TrainingNode
from gstd_a2a.finetune_worker import FineTuneWorker
print('ALL IMPORTS OK')
"
```

Expected: `ALL IMPORTS OK` (this also re-confirms Task 2's spec finetuning modules, untouched by this plan, still import cleanly alongside the changed files).

- [ ] **Step 4: MCP server startup**

```bash
cd /home/bot/gstd-a2a
timeout 5 python3 tools/main.py 2>&1 | head -20
```

Expected: same clean startup log as Task 3 Step 8, confirming the full sequence of changes (Tasks 1-4 together, not just Task 3 in isolation) doesn't break the MCP server.

- [ ] **Step 5: Live check -- repaired `get_balance()` actually works against the real platform**

```bash
cd /home/bot/gstd-a2a
python3 -c "
from gstd_a2a.gstd_client import GSTDClient
client = GSTDClient(wallet_address='UQB03R2DuNR9LKkW1AxbWUDsegAjxCRVwRimZlyNQX2Gc8ve')
print(client.get_balance())
"
```

Expected: a real dict with `balance_gstd`/`pending_rewards_gstd`/`free_requests_remaining` keys (not a connection error, not the old `{gstd, ton}` shape) -- HTTP 200 from the live `/api/v1/credits/balance` endpoint. (The wallet address used here is the live gstdbot node's real, already-registered wallet from prior sessions' work -- safe to query, read-only.)

- [ ] **Step 6: Update STATUS.md-equivalent note**

There's no `STATUS.md` in this repo (unlike `gstdai`/`gstdbot`). Instead, note the fix in this plan's own progress ledger (already tracked by the subagent-driven-development skill's ledger mechanism if that's how this plan is executed) -- no separate doc update needed here.
