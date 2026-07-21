# SDK Honesty Follow-up: examples/, starter-kit/, tools/*, docs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the gap the original SDK honesty plan (`docs/superpowers/plans/2026-07-19-sdk-honesty.md`) explicitly deferred: standalone scripts under `examples/`, `starter-kit/`, `tools/*.py` (outside the pip-packaged `src/gstd_a2a/`) still call the 14 methods removed from `GSTDClient`, still expect `get_balance()`'s old response shape, or otherwise promise platform features (a shared "Hive Memory" knowledge store, a paid task marketplace) that don't exist server-side. `starter-kit/` is the literal clone-and-run onboarding path for `gstdcoin/A2A` — a real user following it hits a crash or silent wrong behavior.

**Architecture:** No new abstractions. Each broken file gets one of three treatments based on whether the broken call is incidental (small patch, keep the file) or is the file's entire reason for existing (delete the file, matching the treatment `x402.py` got in the original plan). Two onboarding docs (`CONTRIBUTING.md`, `skills/beacon_broadcaster/SKILL.md`) get the same honesty treatment as `README.md`/`AGENTS.md` did in the original plan.

**Tech Stack:** Python 3.9+, same as the rest of the repo. No new dependencies.

## Global Constraints

- Every reference to a removed `GSTDClient` method (`create_task`, `check_task_status`, `get_payout_intent`, `get_market_quote`, `prepare_swap`, `buy_gstd_x402`, `request_invoice`, `pay_invoice`, `store_knowledge`, `query_knowledge`, `get_marketplace_agents`, `hire_agent`, `get_ml_referral_stats`, `claim_referral_rewards`) must be gone from every file this plan touches — verify with `grep -rn` before considering a task done.
- Every reference to the OLD `get_balance()` shape (`gstd_balance`, `ton_balance`, `balance.get("gstd"`, `balance.get("ton"`) or the old endpoint (`/api/v1/users/balance`, `users/balance`) must be fixed to the real shape (`balance_gstd`, `pending_rewards_gstd`, etc.) and real endpoint (`/api/v1/credits/balance?wallet=...`).
- No shared "Hive Memory" / knowledge-store feature exists on the platform (confirmed in the original design spec: `docs/superpowers/specs/2026-07-19-sdk-honesty-design.md`) and there is no repair target for it — any code/docs claiming to store or query shared knowledge must be removed, not repaired.
- No paid task-marketplace ("hire other agents", "outsource computation") feature exists on the platform — same treatment: remove, don't repair.
- Real, working, unaffected methods (never touch): `register_node`, `send_heartbeat`, `get_pending_tasks`, `submit_result`, `health_check`, `discover_agents`, `login_via_genesis`/`reauthenticate`, the repaired `get_balance()`, and everything in `gstd_wallet.py` (`check_balance()`, `swap_ton_to_gstd()`, `check_gstd_balance()`).
- Deleting a file is the right call only when the broken call(s) are the file's entire purpose (no other independently-useful logic remains) AND the file is not the sole implementation of a doc-referenced, runnable command. Two files ARE doc-referenced and runnable (`examples/recruit_agent.py`, `examples/propagate_beacon.py`) — these must be patched, never deleted.
- No new tests needed (none of these directories are covered by `pytest tests/`, confirmed in the original plan's scope). Existing test suite (`pytest tests/ -v`) must stay green throughout (none of these changes touch `src/gstd_a2a/`, so this is a sanity check, not an expected-impact check).

---

## Task 1: `examples/` — patch 2 reachable scripts, delete 3 orphaned ones

**Files:**
- Modify: `/home/bot/gstd-a2a/examples/recruit_agent.py`
- Modify: `/home/bot/gstd-a2a/examples/propagate_beacon.py`
- Delete: `/home/bot/gstd-a2a/examples/consensus_agent.py`
- Delete: `/home/bot/gstd-a2a/examples/broadcast_beacon.py`
- Delete: `/home/bot/gstd-a2a/examples/genesis_loop.py`

**Interfaces:** none produced/consumed — these are standalone scripts, not imported by anything else in the repo (confirmed: no other file imports from `examples/`).

- [ ] **Step 1: Patch `recruit_agent.py` — remove dead Hive Memory deploy/status logic, fix stale tool list**

The beacon content at line 43-49 advertises MCP tools that no longer exist (`memorize`, `recall`, `outsource_computation` were deleted from `tools/main.py` in the original plan's Task 3). Replace (currently lines 42-50):
```python
        "content": (
            "MCP-compatible agents: GSTD provides a full MCP server with 15+ tools for "
            "autonomous economic operation. Tools include: find_work, submit_task_result, "
            "memorize, recall, exchange_bridge_swap, outsource_computation, and more. "
            "Install: see https://github.com/gstdcoin/A2A/blob/main/docs/SKILL.md | "
            "Run: python3 tools/main.py (stdio transport) | "
            "Earn GSTD tokens on TON blockchain for every task completed."
        ),
```
with:
```python
        "content": (
            "MCP-compatible agents: GSTD provides an MCP server with tools for "
            "autonomous economic operation. Tools include: find_work, submit_task_result, "
            "exchange_bridge_swap, and more. "
            "Install: see https://github.com/gstdcoin/A2A/blob/main/docs/SKILL.md | "
            "Run: python3 tools/main.py (stdio transport) | "
            "Earn GSTD tokens on TON blockchain for every task completed."
        ),
```

There is no shared knowledge store on the platform (confirmed in the design spec — `store_knowledge`/`query_knowledge` were removed with no repair target), so `deploy_recruitment_beacons()` and `check_recruitment_status()` cannot actually do what their names promise. Replace the entire `deploy_recruitment_beacons()` function (currently lines 204-250):
```python
def deploy_recruitment_beacons(wallet: str = None, api_key: str = None):
    """Deploy all recruitment beacons to Hive Memory"""
    if not HAS_SDK:
        print("⚠️  SDK not available. Install: pip install gstd-a2a")
        # Fallback: print beacons for manual deployment
        print("\n📋 Beacons for manual deployment:")
        for b in RECRUITMENT_BEACONS:
            print(f"\n  Topic: {b['topic']}")
            print(f"  Content: {b['content'][:100]}...")
        return 0
    
    wallet = wallet or os.getenv("GSTD_WALLET_ADDRESS", "EQ_RECRUITMENT_AGENT")
    api_key = api_key or os.getenv("GSTD_API_KEY", "")
    
    client = GSTDClient(
        api_url="https://app.gstdtoken.com",
        wallet_address=wallet,
        api_key=api_key
    )
    
    deployed = 0
    print(f"\n📡 Deploying {len(RECRUITMENT_BEACONS)} recruitment beacons...")
    
    for beacon in RECRUITMENT_BEACONS:
        try:
            client.store_knowledge(
                topic=beacon["topic"],
                content=beacon["content"],
                tags=beacon["tags"]
            )
            print(f"  ✅ '{beacon['topic']}' — deployed")
            deployed += 1
        except Exception as e:
            print(f"  ⚠️  '{beacon['topic']}' — failed: {e}")
    
    # Store propagation report
    try:
        client.store_knowledge(
            topic="recruitment_report",
            content=f"Agent {wallet[:16]} deployed {deployed} recruitment beacons at {datetime.now().isoformat()}",
            tags=["propagation", "recruitment", "report"]
        )
    except:
        pass
    
    print(f"\n📊 Result: {deployed}/{len(RECRUITMENT_BEACONS)} beacons active")
    return deployed
```
with:
```python
def deploy_recruitment_beacons(wallet: str = None, api_key: str = None):
    """Print recruitment beacons for manual sharing.

    There is no shared knowledge store on the platform to deploy these
    to automatically -- print them for a human (or agent) to share
    manually (e.g. in a project README, a forum post, a tweet).
    """
    print("\n📋 Recruitment beacons for manual sharing:")
    for b in RECRUITMENT_BEACONS:
        print(f"\n  Topic: {b['topic']}")
        print(f"  Content: {b['content']}")
    return len(RECRUITMENT_BEACONS)
```

Replace the entire `check_recruitment_status()` function (currently lines 253-282):
```python
def check_recruitment_status(wallet: str = None, api_key: str = None):
    """Check recruitment beacon reach"""
    if not HAS_SDK:
        print("⚠️  SDK not available")
        return
    
    wallet = wallet or os.getenv("GSTD_WALLET_ADDRESS", "EQ_RECRUITMENT_AGENT")
    api_key = api_key or os.getenv("GSTD_API_KEY", "")
    
    client = GSTDClient(
        api_url="https://app.gstdtoken.com",
        wallet_address=wallet,
        api_key=api_key
    )
    
    print("\n📊 Recruitment Status Report")
    print("="*40)
    
    # Check each beacon topic
    for beacon in RECRUITMENT_BEACONS:
        results = client.query_knowledge(beacon["topic"])
        count = len(results) if isinstance(results, list) else 0
        print(f"  {beacon['topic']}: {count} entries in Hive Memory")
    
    # Check network size
    try:
        nodes = client.discover_agents(limit=1)
        print(f"\n  Network nodes (visible): {len(nodes)}+")
    except:
        pass
```
with:
```python
def check_recruitment_status(wallet: str = None, api_key: str = None):
    """Check visible network size (the only real, queryable recruitment signal)."""
    if not HAS_SDK:
        print("⚠️  SDK not available")
        return

    wallet = wallet or os.getenv("GSTD_WALLET_ADDRESS", "EQ_RECRUITMENT_AGENT")
    api_key = api_key or os.getenv("GSTD_API_KEY", "")

    client = GSTDClient(
        api_url="https://app.gstdtoken.com",
        wallet_address=wallet,
        api_key=api_key
    )

    print("\n📊 Recruitment Status Report")
    print("="*40)

    try:
        nodes = client.discover_agents(limit=1)
        print(f"  Network nodes (visible): {len(nodes)}+")
    except Exception as e:
        print(f"  ⚠️  Could not fetch network size: {e}")
```

- [ ] **Step 2: Patch `propagate_beacon.py` — remove dead Hive Memory deploy path, fix stale endpoint in propagated text**

The `SKILL_BEACON` text template (this file's whole job is to write this text into OTHER people's repos) has a stale endpoint reference. Replace (currently lines 51-55):
```
## API: https://app.gstdtoken.com/api/v1
- Register: POST /nodes/register (X-Wallet-Address header)
- Work: GET /tasks/worker/pending → POST /tasks/worker/submit
- Knowledge: POST /knowledge/agent/store | GET /knowledge/query
- Balance: GET /users/balance
```
with:
```
## API: https://app.gstdtoken.com/api/v1
- Register: POST /nodes/register (X-Wallet-Address header)
- Work: GET /tasks/worker/pending → POST /tasks/worker/submit
- Balance: GET /credits/balance?wallet=YOUR_WALLET
```
(the "Knowledge" line is removed, not just fixed -- there is no `/knowledge/agent/store` or `/knowledge/query` endpoint on the platform, so this line was never accurate)

There is no shared knowledge store to deploy `HIVE_BEACONS` to. Replace the entire `deploy_hive_beacons()` function (currently lines 155-183):
```python
def deploy_hive_beacons(wallet: str = None, api_key: str = None) -> int:
    """Deploy beacons to Hive Memory"""
    if not HAS_SDK:
        print("  ⚠️  SDK not available. Install: pip install gstd-a2a")
        return 0
    
    wallet = wallet or os.getenv("GSTD_WALLET_ADDRESS", "EQ_PROPAGATION_AGENT")
    api_key = api_key or os.getenv("GSTD_API_KEY", "")
    
    client = GSTDClient(
        api_url="https://app.gstdtoken.com",
        wallet_address=wallet,
        api_key=api_key
    )
    
    deployed = 0
    for beacon in HIVE_BEACONS:
        try:
            client.store_knowledge(
                topic=beacon["topic"],
                content=beacon["content"],
                tags=beacon["tags"]
            )
            print(f"  ✅ Hive beacon '{beacon['topic']}' deployed")
            deployed += 1
        except Exception as e:
            print(f"  ⚠️  Hive beacon '{beacon['topic']}' failed: {e}")
    
    return deployed
```
with:
```python
def deploy_hive_beacons(wallet: str = None, api_key: str = None) -> int:
    """Print beacons for manual sharing.

    There is no shared knowledge store on the platform to deploy these
    to automatically -- print them for manual sharing instead.
    """
    print("  📋 Hive beacons for manual sharing (no shared knowledge store exists to auto-deploy to):")
    for beacon in HIVE_BEACONS:
        print(f"\n    Topic: {beacon['topic']}")
        print(f"    Content: {beacon['content']}")
    return len(HIVE_BEACONS)
```

Also fix two of the `HIVE_BEACONS` content strings that reference the dead knowledge endpoints. Replace (currently lines 94-104):
```python
    {
        "topic": "collective_intelligence_network",
        "content": (
            "GSTD Hive Memory: a shared knowledge graph across thousands of AI agents. "
            "What one agent learns, all agents can access. "
            "Store: POST /api/v1/knowledge/agent/store | "
            "Query: GET /api/v1/knowledge/query?topic=... | "
            "Hub: https://github.com/gstdcoin/A2A"
        ),
        "tags": ["beacon", "hive-memory", "collective", "knowledge", "intelligence"]
    },
```
with:
```python
    {
        "topic": "collective_intelligence_network",
        "content": (
            "GSTD Collective Intelligence: access 8 AI models through the platform's "
            "chat completions API, pay-per-query with GSTD tokens. "
            "API: POST https://app.gstdtoken.com/api/v1/chat/completions | "
            "Hub: https://github.com/gstdcoin/A2A"
        ),
        "tags": ["beacon", "collective", "ai-inference", "intelligence"]
    },
```
(this beacon's content is themselves propagated into other repos, so the same accuracy bar applies as to code -- redirect the "collective intelligence" pitch to the one real always-available multi-model endpoint, `/api/v1/chat/completions`, confirmed real and working via prior sessions' verification of this platform)

- [ ] **Step 3: Verify no dangling references in the 2 patched files**

```bash
cd /home/bot/gstd-a2a
grep -n "store_knowledge\|query_knowledge\|users/balance\|knowledge/agent/store\|knowledge/query" examples/recruit_agent.py examples/propagate_beacon.py
```

Expected: no output.

- [ ] **Step 4: Delete the 3 orphaned, entirely-broken example scripts**

```bash
cd /home/bot/gstd-a2a
rm examples/consensus_agent.py examples/broadcast_beacon.py examples/genesis_loop.py
```

(Each file's entire purpose depends on removed methods with no real replacement -- `consensus_agent.py` on `create_task`/`check_task_status`, `broadcast_beacon.py` and `genesis_loop.py` on `store_knowledge`/`create_task` -- and none are referenced by any doc or script in the repo, confirmed via `grep -rn "consensus_agent\|broadcast_beacon\|genesis_loop" --include="*.md" --include="*.py" .` returning only the repo-tree diagram entries in `README.md`, which Step 6 below removes.)

- [ ] **Step 5: Remove the 3 deleted files' README repo-tree entries**

Find and remove their lines from `README.md`'s directory-tree listing (they're plain `├──`/`└──` entries alongside other `examples/*.py` lines -- read the tree section first to get exact current line numbers and correct tree-connector characters for whichever lines end up needing to become the new last entry).

- [ ] **Step 6: Import/syntax check on the 2 patched files**

```bash
cd /home/bot/gstd-a2a
python3 -c "import ast; ast.parse(open('examples/recruit_agent.py').read()); print('recruit_agent.py OK')"
python3 -c "import ast; ast.parse(open('examples/propagate_beacon.py').read()); print('propagate_beacon.py OK')"
```

Expected: both print OK (these scripts aren't part of the pip package so `ast.parse` -- syntax validity -- is the right level of check, not a full import, since `recruit_agent.py`/`propagate_beacon.py` do their own `sys.path` manipulation to find the SDK relative to the repo checkout).

- [ ] **Step 7: Run existing test suite (sanity check, unaffected)**

```bash
cd /home/bot/gstd-a2a
python3 -m pytest tests/ -v
```

Expected: still 10/10 passing (this task touches no file under `tests/` coverage).

- [ ] **Step 8: Commit**

```bash
cd /home/bot/gstd-a2a
git add examples/recruit_agent.py examples/propagate_beacon.py README.md
git rm examples/consensus_agent.py examples/broadcast_beacon.py examples/genesis_loop.py
git commit -m "$(cat <<'EOF'
fix(examples): remove dead Hive Memory/task-marketplace calls, delete orphaned demos

Closes a gap explicitly deferred by the original SDK honesty plan:
examples/ scripts still called GSTDClient methods removed for calling
nonexistent platform endpoints (store_knowledge, query_knowledge,
create_task, check_task_status -- no shared knowledge store or paid
task marketplace exists on the platform, confirmed in the design spec).

recruit_agent.py and propagate_beacon.py are the two example scripts
actually referenced by README.md/CONTRIBUTING.md as runnable commands
-- patched to print beacons for manual sharing instead of pretending to
deploy them to a network store that doesn't exist, and fixed a stale
tool list (referenced 3 MCP tools deleted in an earlier commit) and a
stale /users/balance endpoint reference in text this script propagates
into other repos.

consensus_agent.py, broadcast_beacon.py, and genesis_loop.py are not
referenced by any doc or script in the repo, and their entire purpose
(multi-agent task consensus, beacon broadcasting, a manifesto+translation
demo) depends entirely on the removed methods with no real replacement
-- deleted rather than patched, same treatment x402.py got in the
original plan.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: `starter-kit/` — fix auth-check pattern in 2 scripts

**Files:**
- Modify: `/home/bot/gstd-a2a/starter-kit/check_all.py`
- Modify: `/home/bot/gstd-a2a/starter-kit/verify_payment_auth.py`

**Interfaces:**
- Consumes: `GSTDClient.get_balance() -> dict` (repaired in the original plan; returns `{"wallet":..., "balance_gstd":..., "pending_rewards_gstd":..., "free_requests_today":..., "free_requests_remaining":..., "currency":...}` on success, raises on HTTP error).

Both scripts used `client.create_task(...)` as an "auth verification" trick (a real, dead endpoint that would 401 on a bad key). Since `create_task` is gone, `get_balance()` is the correct replacement: it's a real, currently-working endpoint that also requires a valid `X-Wallet-Address`/API key pairing, so a 401/403 there is an equally valid "auth failed" signal, without pretending to spend GSTD.

- [ ] **Step 1: Patch `check_all.py`'s Step 4 (Authorization Verify)**

Replace (currently lines 76-103):
```python
    client = GSTDClient(api_key=api_key, wallet_address=wallet.address)
    try:
        # Try to create a dummy task (smallest possible bid)
        # Verify Payment Auth only works by trying to SPEND or LOCK funds.
        # create_task checks both Key Validity AND Balance.
        print("   Sending test request (create_task)...")
        task = client.create_task(
            task_type="auth_check",
            data_payload={"test": True},
            bid_gstd=0.01
        )
        print("✅ AUTHORIZATION SUCCESS!")
        print(f"   Test Task ID: {task.get('task_id')}")
        status = "PASSED"
    except Exception as e:
        err_str = str(e)
        if "401" in err_str:
             print("❌ FAILED: 401 Unauthorized.")
             print("   👉 Your API Key is invalid or expired.")
             status = "FAILED"
        elif "402" in err_str or "balance" in err_str.lower():
             print("⚠️  PARTIAL SUCCESS: 402 Payment Required.")
             print("   ✅ Auth worked (Key is valid).") 
             print("   ❌ But insufficient GSTD balance on Grid Account.")
             status = "PASSED (Low Balance)"
        else:
             print(f"❌ FAILED: Server returned error: {err_str}")
             status = "FAILED"
```
with:
```python
    client = GSTDClient(api_key=api_key, wallet_address=wallet.address)
    try:
        print("   Sending test request (get_balance)...")
        balance = client.get_balance()
        print("✅ AUTHORIZATION SUCCESS!")
        print(f"   Platform balance: {balance.get('balance_gstd')} GSTD | "
              f"Free requests remaining today: {balance.get('free_requests_remaining')}")
        status = "PASSED"
    except Exception as e:
        err_str = str(e)
        if "401" in err_str:
             print("❌ FAILED: 401 Unauthorized.")
             print("   👉 Your API Key is invalid or expired.")
             status = "FAILED"
        else:
             print(f"❌ FAILED: Server returned error: {err_str}")
             status = "FAILED"
```

- [ ] **Step 2: Patch `verify_payment_auth.py`**

Replace (currently lines 36-63):
```python
    # 3. Test Task Creation
    client = GSTDClient(api_key=api_key, wallet_address=wallet_address)
    
    try:
        print("📡 Sending authenticated request to create paid task...")
        # Create a minimal task to verify header acceptance
        task = client.create_task(
            task_type="text-processing",
            data_payload={
                "text": "Auth Check", 
                "instruction": "Verify Bearer Token is accepted",
                "context": "Debug Mode"
            },
            bid_gstd=0.1 # Small bid
        )
        
        print("\n✅ AUTHORIZATION SUCCESS!")
        print(f"   Task ID: {task.get('task_id')}")
        print(f"   Status: {task.get('status')}")
        print("   The server accepted the Authorization header.")
        
    except Exception as e:
        print("\n❌ AUTHORIZATION/REQUEST FAILED")
        print(f"   Error: {e}")
        if "401" in str(e):
            print("   👉 Cause: Invalid API Key. Check your key on gstdtoken.com")
        elif "402" in str(e) or "balance" in str(e).lower():
            print("   👉 Cause: Key valid, but insufficient GSTD balance.")
```
with:
```python
    # 3. Test Authenticated Request
    client = GSTDClient(api_key=api_key, wallet_address=wallet_address)
    
    try:
        print("📡 Sending authenticated request (get_balance)...")
        balance = client.get_balance()
        
        print("\n✅ AUTHORIZATION SUCCESS!")
        print(f"   Balance: {balance.get('balance_gstd')} GSTD")
        print(f"   Free requests remaining today: {balance.get('free_requests_remaining')}")
        print("   The server accepted the Authorization header.")
        
    except Exception as e:
        print("\n❌ AUTHORIZATION/REQUEST FAILED")
        print(f"   Error: {e}")
        if "401" in str(e):
            print("   👉 Cause: Invalid API Key. Check your key on gstdtoken.com")
```

- [ ] **Step 3: Verify no dangling references**

```bash
cd /home/bot/gstd-a2a
grep -n "create_task\|check_task_status\|402" starter-kit/check_all.py starter-kit/verify_payment_auth.py
```

Expected: no output.

- [ ] **Step 4: Syntax check**

```bash
cd /home/bot/gstd-a2a
python3 -c "import ast; ast.parse(open('starter-kit/check_all.py').read()); print('check_all.py OK')"
python3 -c "import ast; ast.parse(open('starter-kit/verify_payment_auth.py').read()); print('verify_payment_auth.py OK')"
```

Expected: both OK.

- [ ] **Step 5: Run existing test suite (sanity check, unaffected)**

```bash
cd /home/bot/gstd-a2a
python3 -m pytest tests/ -v
```

Expected: still 10/10 passing.

- [ ] **Step 6: Commit**

```bash
cd /home/bot/gstd-a2a
git add starter-kit/check_all.py starter-kit/verify_payment_auth.py
git commit -m "$(cat <<'EOF'
fix(starter-kit): replace dead create_task auth-check with get_balance()

Both scripts used client.create_task(...) purely as a side-effect-free
way to test whether an API key is accepted (a real endpoint's 401
response was the actual signal being tested for, not task creation
itself). create_task no longer exists (removed for calling a
nonexistent platform endpoint). get_balance() is a real, currently
working authenticated endpoint that serves the identical purpose --
same 401-on-bad-key signal, without pretending to spend GSTD or lock
funds. Dropped the "402 Payment Required" partial-success branches in
both scripts since credits/balance has no paid-lock semantics to
partially succeed at.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: `tools/` — fix a silent balance-check bug and 3 dead-call scripts

**Files:**
- Modify: `/home/bot/gstd-a2a/tools/sovereign_agent.py`
- Modify: `/home/bot/gstd-a2a/tools/openclaw_bridge.py`
- Modify: `/home/bot/gstd-a2a/tools/verify_deployment.py`
- Delete: `/home/bot/gstd-a2a/tools/external_agent_launcher.py`

**Interfaces:** none produced/consumed -- standalone scripts, none imported elsewhere in the repo.

- [ ] **Step 1: Fix `sovereign_agent.py`'s silent balance bug (the highest-value fix in this task)**

`get_balance()`'s repaired response has no `"gstd"` key (real keys are `balance_gstd`, `pending_rewards_gstd`, etc.), so `check_balance()` here has been silently returning `0.0` on every call since the repair -- not crashing, just always reporting zero balance. Because `DualModeAgent.start()`'s mode-switch logic uses `balance <= WORKER_THRESHOLD` to decide when to stay in worker mode, this bug makes the agent **permanently unable to enter MASTER mode**, regardless of actual funds. Replace (currently lines 31-34):
```python
            res = self.client.get_balance()
            if res and 'gstd' in res:
                return float(res['gstd'])
            return 0.0
```
with:
```python
            res = self.client.get_balance()
            if res and 'balance_gstd' in res:
                return float(res['balance_gstd'])
            return 0.0
```

- [ ] **Step 2: Patch `openclaw_bridge.py` -- remove the dead vision-offload feature**

`_offload_vision_task()`'s only real action is `self.client.create_task(...)`, which no longer exists, and it has no replacement (no paid task-marketplace exists on the platform). The rest of the bridge (register, poll pending tasks, execute, submit result, heartbeat) is real and unaffected. Remove the call site in `run()` (currently lines 70-73):
```python
                # B. Simulation: Offload AI Task (Intelligence Mode)
                # Every 10 cycles, simulated robot "sees" something and asks for help
                if cycle_count % 10 == 0:
                    self._offload_vision_task()

```
(delete this whole block including its trailing blank line, so the loop goes straight from the incoming-jobs check to the heartbeat call)

Delete the entire `_offload_vision_task()` method (currently lines 115-135):
```python
    def _offload_vision_task(self):
        # Simulate robot seeing an object it doesn't understand
        print("\n🧠 Robot camera detected unknown object. Requesting Grid Analysis...")
        
        task_payload = {
            "image_data": "base64_mock_data...",
            "text": "Image analysis request", # Protocol requirement
            "instruction": "Identify object and suggest grip strategy for OpenClaw",
            "context": "Warehouse environment"
        }
        
        try:
            # Create a high-priority task for other agents using own balance
            resp = self.client.create_task(
                task_type="text-processing", # Using text/vision protocol
                data_payload=task_payload,
                bid_gstd=0.5 # Paying 0.5 GSTD for intelligence
            )
            print(f"   🚀 Analysis Task Broadcasted: {resp.get('task_id')}")
        except Exception as e:
            print(f"   ⚠️ Could not offload task (Low Balance?): {e}")
```

Also fix the class docstring, which advertises this now-removed capability. Replace (currently lines 13-20):
```python
    """
    Bridge between OpenClaw hardware and the GSTD Decentralized Grid.
    Uses GSTD sovereign nodes (Ollama llama3.2:3b) for planning and vision.
    Enables:
    1. Monetization: Rent out your OpenClaw hardware to global agents.
    2. Intelligence: Offload heavy AI tasks (Vision, Planning) to the GSTD grid.
    3. Panel: Full management dashboard at /api/v1/openclaw/*
    """
```
with:
```python
    """
    Bridge between OpenClaw hardware and the GSTD Decentralized Grid.
    Registers as a physical control node and earns GSTD by executing
    control-command tasks dispatched from the agent network.
    """
```

- [ ] **Step 3: Patch `verify_deployment.py` -- remove the dead market-quote check**

`get_market_quote()` is gone with no repair target (no public swap-quote endpoint exists on the platform). Replace (currently lines 42-49):
```python
    # 4. Market Data (Public Endpoint)
    print("\n3️⃣  Testing Economic Logic (Market Quote)...")
    try:
        quote = client.get_market_quote(amount_ton=1.0)
        print(f"   ✅ 1 TON buys approx: {quote.get('estimated_gstd', 'N/A')} GSTD")
        print(f"   📊 Quote Details: {quote}")
    except Exception as e:
        print(f"   ❌ Market Quote Error: {e}")

    # 5. Task Logic (Simulation)
    print("\n4️⃣  Verifying Task Protocols...")
```
with:
```python
    # 4. Task Logic (Simulation)
    print("\n3️⃣  Verifying Task Protocols...")
```

Also renumber the final check's header (currently line 60), since removing the market-quote check shifts every subsequent number down by one. Replace:
```python
    # 6. Check MCP Server Import
    print("\n5️⃣  Verifying MCP Server Integrity...")
```
with:
```python
    # 5. Check MCP Server Import
    print("\n4️⃣  Verifying MCP Server Integrity...")
```

- [ ] **Step 4: Delete `external_agent_launcher.py`**

```bash
cd /home/bot/gstd-a2a
grep -rn "external_agent_launcher" --include="*.md" --include="*.py" . 2>/dev/null
```

Expected: only the README repo-tree diagram entry (confirm this before deleting -- if any other reference turns up, stop and report it rather than deleting). Then:

```bash
rm tools/external_agent_launcher.py
```

(`launch_task()`'s entire job is dispatch-via-`create_task()` + poll-via-`check_task_status()` -- both removed, no replacement exists, and the whole file has no other purpose. Not referenced by any doc as a runnable command.)

- [ ] **Step 5: Remove the deleted file's README repo-tree entry**

Same treatment as Task 1 Step 5 -- find and remove `external_agent_launcher.py`'s line from `README.md`'s directory-tree listing.

- [ ] **Step 6: Verify no dangling references**

```bash
cd /home/bot/gstd-a2a
grep -n "get_market_quote\|create_task\|check_task_status\|\.get('gstd')\|\['gstd'\]" tools/sovereign_agent.py tools/openclaw_bridge.py tools/verify_deployment.py
```

Expected: no output.

- [ ] **Step 7: Syntax check**

```bash
cd /home/bot/gstd-a2a
python3 -c "import ast; ast.parse(open('tools/sovereign_agent.py').read()); print('sovereign_agent.py OK')"
python3 -c "import ast; ast.parse(open('tools/openclaw_bridge.py').read()); print('openclaw_bridge.py OK')"
python3 -c "import ast; ast.parse(open('tools/verify_deployment.py').read()); print('verify_deployment.py OK')"
```

Expected: all three OK.

- [ ] **Step 8: Run existing test suite (sanity check, unaffected)**

```bash
cd /home/bot/gstd-a2a
python3 -m pytest tests/ -v
```

Expected: still 10/10 passing.

- [ ] **Step 9: Commit**

```bash
cd /home/bot/gstd-a2a
git add tools/sovereign_agent.py tools/openclaw_bridge.py tools/verify_deployment.py README.md
git rm tools/external_agent_launcher.py
git commit -m "$(cat <<'EOF'
fix(tools): fix silent balance bug, remove dead task/market calls

sovereign_agent.py: check_balance() read the OLD get_balance() key
("gstd"), which no longer exists after an earlier repair (real key is
"balance_gstd") -- this was NOT crashing, it was silently returning
0.0 on every call, which permanently locked DualModeAgent out of
MASTER mode regardless of actual wallet funds. Fixed to read the real
key. This is the highest-value fix in this commit: a correctness bug
introduced by an earlier repair, not just dead-code removal.

openclaw_bridge.py: removed _offload_vision_task() (its only action
was the removed create_task(), no replacement exists) and its
call site; the real control-command worker loop (register, poll,
execute, submit, heartbeat) is untouched.

verify_deployment.py: removed the get_market_quote() smoke-test check
(no public swap-quote endpoint exists to replace it); the other 5
checks (wallet gen, health check, task fetch, MCP import) are
untouched.

external_agent_launcher.py deleted entirely -- its only job was
dispatch-via-create_task()+poll-via-check_task_status(), both removed
with no replacement, and it's not referenced by any doc as a runnable
command.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Fix 2 onboarding docs that actively teach a broken API call

**Files:**
- Modify: `/home/bot/gstd-a2a/CONTRIBUTING.md`
- Delete: `/home/bot/gstd-a2a/skills/beacon_broadcaster/SKILL.md`

**Interfaces:** none -- documentation only.

- [ ] **Step 1: Fix `CONTRIBUTING.md`'s "Contribute Knowledge" section**

This section instructs a new AI contributor to call `store_knowledge()`, which no longer exists (no shared knowledge store exists on the platform, confirmed in the design spec, no repair target). Replace (currently lines 33-43):
```
### 4. Contribute Knowledge
Share valuable findings with the network:
```python
from gstd_a2a.gstd_client import GSTDClient
client = GSTDClient(wallet_address="YOUR_WALLET")
client.store_knowledge(
    topic="your_discovery",
    content="Valuable knowledge to share...",
    tags=["contribution", "knowledge"]
)
```
```
with:
```
### 4. Contribute Knowledge
There is currently no shared knowledge store on the platform. If you
discover something valuable, share it the same way as any other open-source
contribution: open a GitHub issue or discussion at
https://github.com/gstdcoin/A2A/issues.
```

- [ ] **Step 2: Delete `skills/beacon_broadcaster/SKILL.md`**

This skill's entire purpose -- documented in its own description ("Broadcast discovery beacons to the GSTD Hive Memory network") -- is built on `POST /api/v1/knowledge/agent/store`, one of the confirmed-nonexistent endpoints (same one `store_knowledge()` wrapped before removal; this file hits it directly via `curl`/raw Python instead of through the SDK, but it's the identical dead endpoint). It is `user-invocable: true`, meaning a skill-aware agent would actively try to run its curl commands and Python snippet, all of which 404. There's no repair target -- no shared knowledge store exists to broadcast to. Same treatment as `x402.py` in the original plan.

```bash
cd /home/bot/gstd-a2a
grep -rln "beacon_broadcaster" --include="*.md" . 2>/dev/null
```

Expected: only the file itself (self-reference in its own frontmatter/content) or no output. If anything else references it, stop and report before deleting.

```bash
rm -rf skills/beacon_broadcaster
```

(remove the whole directory, not just the file, if `skills/beacon_broadcaster/` contains only `SKILL.md` -- check with `ls skills/beacon_broadcaster/` first)

- [ ] **Step 3: Verify no dangling references**

```bash
cd /home/bot/gstd-a2a
grep -rn "store_knowledge\|knowledge/agent/store\|beacon_broadcaster" README.md AGENTS.md CONTRIBUTING.md docs/*.md skills/ 2>/dev/null
```

Expected: no output.

- [ ] **Step 4: Commit**

```bash
cd /home/bot/gstd-a2a
git add CONTRIBUTING.md
git rm -r skills/beacon_broadcaster
git commit -m "$(cat <<'EOF'
docs: remove onboarding instructions that teach a dead API call

CONTRIBUTING.md's "Contribute Knowledge" section instructed new AI
contributors to call store_knowledge() -- no shared knowledge store
exists on the platform (confirmed in the SDK honesty design spec, no
repair target) -- replaced with a pointer to GitHub issues, a real
channel.

skills/beacon_broadcaster/SKILL.md is deleted entirely: it is
user-invocable (a skill-aware agent would actively execute its curl
commands and Python snippet) and its whole purpose is broadcasting to
POST /api/v1/knowledge/agent/store, the same nonexistent endpoint
store_knowledge() used to wrap before its removal -- same treatment
x402.py got in the original SDK honesty plan.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Final verification and push

**Files:** none (verification only).

- [ ] **Step 1: Full repo-wide grep for any remaining dead reference**

```bash
cd /home/bot/gstd-a2a
grep -rn "\.create_task(\|\.check_task_status(\|\.get_payout_intent(\|\.get_market_quote(\|\.prepare_swap(\|\.buy_gstd_x402(\|\.request_invoice(\|\.pay_invoice(\|\.store_knowledge(\|\.query_knowledge(\|\.get_marketplace_agents(\|\.hire_agent(\|\.get_ml_referral_stats(\|\.claim_referral_rewards(" --include="*.py" --include="*.md" .
```

Expected: no output anywhere in the repo (this is the final, repo-wide confirmation -- narrower per-task greps in Tasks 1-4 already checked their own files, this catches anything missed across file boundaries).

- [ ] **Step 2: Full repo-wide grep for the old get_balance() shape / old endpoint**

```bash
cd /home/bot/gstd-a2a
grep -rn "gstd_balance\|ton_balance\|users/balance\|\.get('gstd')\|\['gstd'\]\|\.get(\"gstd\")\|\[\"gstd\"\]" --include="*.py" --include="*.md" .
```

Expected: no output.

- [ ] **Step 3: Syntax check every modified/remaining Python file in examples/, starter-kit/, tools/**

```bash
cd /home/bot/gstd-a2a
for f in examples/*.py starter-kit/*.py tools/*.py; do
  python3 -c "import ast; ast.parse(open('$f').read())" && echo "OK: $f" || echo "SYNTAX ERROR: $f"
done
```

Expected: `OK:` for every file, no `SYNTAX ERROR` lines.

- [ ] **Step 4: Full test suite**

```bash
cd /home/bot/gstd-a2a
python3 -m pytest tests/ -v
```

Expected: 10/10 passing, pristine output.

- [ ] **Step 5: Push**

```bash
cd /home/bot/gstd-a2a
git push git@github.com:gstdcoin/A2A.git master
```

- [ ] **Step 6: Update progress ledger**

No separate STATUS.md in this repo (same as the original plan) -- the subagent-driven-development skill's ledger mechanism (`.superpowers/sdd/progress.md`) tracks this automatically if that's how this plan is executed.
