# gstd-a2a SDK Honesty Fix — Design Spec
**Date:** 2026-07-19
**Status:** Approved
**Goal:** Remove or repair every `gstd_client.py` method that calls a platform endpoint that does not exist, so the SDK's public surface only promises what the live platform can actually do — before building any new "compute exchange for agents" feature on top of it.

---

## 1. Problem

This is the first step of a two-part plan: direction #2 from an earlier brainstorm ("compute exchange for AI agents via gstd-a2a SDK"). Before adding anything new, an audit of `GSTDClient`'s methods against the live platform (`app.gstdtoken.com`, verified live via direct HTTP checks and by checking for the corresponding file under `gstdai/frontend/src/pages/api/v1/`) found:

**7 methods point to real, working endpoints** — keep as-is:
`health_check`, `login_via_genesis`/`reauthenticate` (`/api/v1/genesis/ignite`), `register_node` (`/api/v1/nodes/register`), `send_heartbeat` (`/api/v1/nodes/heartbeat`), `get_pending_tasks` (`/api/v1/tasks/worker/pending`), `submit_result` (`/api/v1/tasks/worker/submit`), `discover_agents` (`/api/v1/nodes/public`).

**1 method points to a real endpoint but the wrong one / wrong field names** — repair:
`get_balance()` calls `/api/v1/users/balance` (404, no such route). The real endpoint is `/api/v1/credits/balance`, which returns `{wallet, balance_gstd, pending_rewards_gstd, free_requests_today, free_requests_remaining, currency}` — different field names, and no `ton_balance` field at all (this endpoint tracks the platform's internal GSTD spending-credit ledger, not on-chain token holdings).

**14 methods point to endpoints that do not exist anywhere in the platform** (verified: no corresponding file under `gstdai/frontend/src/pages/api/v1/`, and live HTTP checks return 404):
`create_task` (`/tasks/create`), `check_task_status` (`/tasks/{id}` — no dynamic route file exists), `get_payout_intent` (`/payments/payout-intent`), `get_market_quote` (`/market/quote`), `prepare_swap` (`/market/swap`), `buy_gstd_x402` (`/market/buy-gstd-x402`), `request_invoice`/`pay_invoice` (`/invoices`), `store_knowledge`/`query_knowledge` (`/knowledge/agent/store`, `/knowledge/query` — no knowledge API exists on the platform at all), `get_marketplace_agents`/`hire_agent` (`/marketplace/agents`, `/marketplace/rentals`), `get_ml_referral_stats`/`claim_referral_rewards` (`/referrals/ml/stats`, `/referrals/ml/claim`).

Two of those 14 have a *plausible-looking but semantically wrong* near-match on the platform: `/api/v1/referrals/stats` is real, but keyed by Telegram user ID (not wallet address) and read-only (no claim/payout action) — a completely different identity and capability model than what `get_ml_referral_stats`/`claim_referral_rewards` promise. Not a valid repair target; remove both.

**`x402.py`** (388 lines, an unimplemented HTTP-402 agent-payment protocol) is imported by nothing anywhere in the repo — confirmed via `grep -rln "from .x402\|import x402"` across `src/` and `tests/`. Dead code from day one.

**The blast radius is bigger than `gstd_client.py` alone.** `agent.py`'s `_bootstrap()` — part of the flagship `Agent.run()` one-liner advertised in the README — calls `client.get_balance()` and, on low balance, either calls a real on-chain swap (`wallet.swap_ton_to_gstd()`, unaffected by any of this) or falls back to `POST /api/v1/tokens/agent/bootstrap` (also 404 — a third, previously-undiscovered fictional endpoint). Separately, `agent.py` calls `client.store_knowledge()` at 6 call sites as part of a "resonance report" / "grid_tool" knowledge-sharing routine. `tools/main.py` (the MCP server) registers MCP tools that thinly wrap 10 of the 14 doomed methods — an MCP client (e.g. Claude Desktop) would see these tools listed as available and get a runtime error the moment it tried to use one.

## 2. What's actually the right fix for `_bootstrap()`'s balance check

Not just "call the repaired `get_balance()`." `gstd_wallet.py` already has real, independent, on-chain balance methods that don't touch the platform API at all: `check_balance()` (returns `{"TON": ..., "GSTD": ...}` via a direct `toncenter` RPC call + a `tonapi.io` Jetton-balance lookup). This is the *correct* data source for "does this agent own enough TON/GSTD to get started" — a question about on-chain holdings, not platform spending credits. `_bootstrap()` should call `self.wallet.check_balance()` instead of `self.client.get_balance()`. The repaired `gstd_client.get_balance()` (pointed at `/api/v1/credits/balance`) remains useful for its own real purpose — checking platform spending-credit balance before submitting a paid job/API call — just not for this bootstrap decision.

## 3. Scope

**In scope:**
1. `gstd_client.py`: remove the 14 dead methods; repair `get_balance()`; simplify `get_pending_tasks()`'s dead `/api/v1/marketplace/tasks` fallback branch out.
2. `agent.py`: `_bootstrap()` — switch to `wallet.check_balance()`; remove the `/api/v1/tokens/agent/bootstrap` fallback branch entirely (replace with an honest log line: no TON to swap, no faucet available, agent stays unfunded until someone funds it); remove all 6 `store_knowledge()` call sites and their now-pointless surrounding "resonance report"/"grid_tool" logic (read `agent.py` fully to judge how much of each surrounding block only exists to feed `store_knowledge` versus does something else independently useful — remove only the now-dead part, not anything doing real work alongside it).
3. `tools/main.py`: remove the MCP tool functions that wrap now-deleted client methods (`check_gstd_price`/`get_market_quote`, `buy_resources`/`prepare_swap`, `outsource_computation`/`create_task`, `check_computation_status`/`check_task_status`, `memorize`/`store_knowledge`, `recall`/`query_knowledge`, `exchange_bridge_swap`/`prepare_swap`, parts of `unify_intelligence` that call `query_knowledge`/`get_marketplace_agents`, `get_ml_referral_report`/`get_ml_referral_stats`, `claim_network_bonus`/`claim_referral_rewards`, `autonomous_knowledge_monetization`/`store_knowledge`). Read each function's full body first — some may do other real work alongside the dead call and need partial edits, not wholesale deletion; judge each on its own.
4. `x402.py`: delete the file entirely.
5. `README.md`/`AGENTS.md`/`docs/`: grep for references to any removed method name or `x402` and remove/update those mentions so documentation doesn't promise dead functionality.

**Out of scope:** building the actual "compute exchange for agents" feature (that's the next spec, after this one ships). Any change to the *real* 7 methods or to `wallet.py`'s on-chain swap logic.

## 4. Testing approach

No mocking of the removed-vs-real distinction — verify against the actual live platform, matching how the rest of this session's work was verified:
- `get_balance()`'s fix: a real HTTP call to `/api/v1/credits/balance` (already confirmed reachable and returning the documented shape during design).
- `wallet.check_balance()`: already real, existing, working code — no change needed, just confirm `_bootstrap()`'s new call matches its actual return shape (`{"TON": float, "GSTD": float}`, or `{"error": str}` on failure — `_bootstrap()` must handle the error shape, since the original `get_balance()` path didn't need to).
- After all removals: `python -c "import gstd_a2a"` and `python -c "from gstd_a2a.agent import Agent"` must succeed with no import errors (proves no dangling reference to a removed name).
- `tools/main.py` must still start (`python3 tools/main.py` should initialize FastMCP without error) after its tool removals.
- Existing test suite (`pytest tests/ -v`) must still pass — confirmed zero existing tests reference any of the removed methods, so no test deletions are needed, but the suite must still be green after the code changes.
- No new tests are being added for the removed methods (there's nothing to test — they're gone). If any existing test happens to cover `get_balance()`'s old behavior, update it to the new endpoint/shape rather than deleting coverage.

## 5. Known follow-up (not this spec)

Once this ships, `docs/superpowers/specs/` will get a second spec for whatever "compute exchange for agents" concretely becomes — likely built on the 7 endpoints that already work (`tasks/worker/pending`+`tasks/worker/submit`, i.e. the earn-by-fulfilling-tasks path) rather than resurrecting the fictional pay-to-commission-a-task flow, unless the platform side gets a real implementation of that first.
