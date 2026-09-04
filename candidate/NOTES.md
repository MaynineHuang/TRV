# TRV Internship Task — Development Notes

## Task Overview

Build a trading desk with three processes:
1. **taker** (provided) — momentum strategy that takes directional bets
2. **strategy** (to build) — quoter/market-maker providing two-sided liquidity
3. **hedger** (to build) — risk control, keeps desk position flat

**Constraints & Context:**
- Entry-level internship: no deep technical knowledge expected
- Goal: demonstrate AI-guided problem-solving, not just code generation
- 100,000 USD margin on a single exchange with cash-settled contracts
- Message protocol: NATS + ASCII over request/reply and publish/subscribe
- All three processes run as Docker containers coordinating via NATS

---

## What We've Discovered

### ✅ Already Provided & Working

1. **Exchange infrastructure**
   - Simulated exchange (Docker image `sim-exchange:candidate`)
   - NATS message bus for coordination
   - Protocol v2.5 with request/reply order entry and JetStream market data feeds
   - Sample market simulator (`sim/market.py`) — generates synthetic liquidity and price movement

2. **Taker (existing Python strategy)**
   - Momentum-based: watches best-bid/offer (BBO), crosses spread when mid-price moves
   - Configuration: 
     - Trades on contract `AAH6` (front month)
     - Order size (clip): 3 contracts per trade
     - Max position: ±30
     - Price movement threshold: 10 price units
     - Lookback window: 5 BBO updates
   - Publishes position/PnL status every second on `strat.<sender>.status`
   - Runs for entire session (86400s) as a container

3. **Docker/Compose setup**
   - `docker-compose.yml` orchestrates NATS + exchange + sim + desk processes
   - `.run.sh` helper scripts for quick startup
   - All containers share private network; NATS also exposed on host `:4222`

### ❌ Issues Found in Taker (Bugs to Fix)

**Bug 1: Wrong request subject for order entry**
- **Location:** `taker/taker.py`, line 85
- **Current:** `await self.nc.request("ex.req", ...)`
- **Should be:** `await self.nc.request(f"ex.req.{SENDER}", ...)`
- **Impact:** Orders timeout and fail because protocol requires sender ID in subject
- **Root cause:** Missing SENDER ID in NATS request subject (protocol says `ex.req.<SENDER>`)

**Bug 2: Sell-side fill accounting is wrong**
- **Location:** `taker/taker.py`, lines 100-103
- **Current:** `signed = qty if side == "B" else qty` (both branches identical)
- **Should be:** `signed = qty if side == "B" else -qty` (sell reduces position)
- **Impact:** Sell orders incorrectly accumulate position in buy direction; cash/PnL metrics are wrong
- **Root cause:** Copy-paste error; sell-side should use negative sign

### ⚠️ Known Incomplete/Ambiguous Parts

1. **Strategy (`strategy/`) — completely empty**
   - No code or Dockerfile
   - Must build a quoter (market-maker strategy)

2. **Hedger (`hedger/`) — completely empty**
   - No code or Dockerfile
   - Must build a position-flattening risk control engine

3. **Protocol details to verify via experimentation**
   - Exact semantics of market data feeds (when are fills redelivered?)
   - Fill callback behavior (`E` vs `T` message distinction)
   - Rate limits on cancel/re-quote operations
   - Self-trade prevention (`Q`/`W` commands) — when and why use it?

4. **Sample market differs from grading market**
   - We're developing against simple synthetic market
   - Actual grading happens on private market with different price behavior
   - Risk of over-fitting to sample price patterns

---

## What We Need to Build

### 1. Strategy (Quoter) — `strategy/` folder

**Purpose:** Provide two-sided liquidity for profit (spread earnings, not directional bets)

**Requirements:**
- Low-risk market-making strategy
- Profitable via bid-ask spread, not speculation
- Must use **non-Python language** (any NATS-supported: Go, Node.js, Rust, C++, etc.)
- Must include working Dockerfile (build from source, not binaries)
- Can coordinate with hedger via NATS message bus

**Key questions to answer:**
- What market-making model? (Simple: quote around fair value at fixed offset?)
- How to calculate fair value? (Taker's BBO + relocation, or independent?)
- Quote size and depth? (How many price levels?)
- How aggressively adjust quotes when price moves?
- Risk management: position limits per contract? Stop-loss rules?

**Success criteria:**
- Runs as Docker container alongside taker + hedger
- Sends limit orders via `ex.req.<SENDER>` with correct protocol format
- Subscribes to market data (`ex.md.<FEED>.<SENDER>`) to see own fills
- Subscribes to BBO feed to adjust quotes
- Publishes status periodically so we can monitor

### 2. Hedger (Risk Control) — `hedger/` folder

**Purpose:** Keep desk position flat (low risk)

**Requirements:**
- Watch combined position of all three desk processes
- When others accumulate net exposure, hedger trades to offset it
- Fast reversal hedging needed: large positions even briefly are high-risk
- Any language allowed (Python OK)
- Must include working Dockerfile

**Key questions to answer:**
- How to discover other processes' positions? (Subscribe to their status broadcasts?)
- Should hedger aggregate position across all three senders?
- When to hedge? (Immediately on every fill, or in batches?)
- How aggressive? (Market orders, limit orders, what size?)
- Any rate-limit awareness? (Protocol has max_tps per feed)

**Success criteria:**
- Detects when desk has net exposure
- Executes hedging trades to reduce it
- Keeps position low even under price volatility
- Doesn't accidentally over-hedge or cascade-trade

---

## Our Implementation Plan

### Phase 1: Fix Taker Bugs (Foundation)
1. Fix NATS request subject: add `{SENDER}` to subject
2. Fix sell-side position math: use `-qty` for sells
3. Test locally with `./run.sh --sim` to verify orders now execute

**Expected outcome:** Taker places orders, gets fills, tracks position correctly

### Phase 2: Understand the Exchange (Experimentation)
1. Probe with `nats` CLI to understand protocol in practice
   - Subscribe to `ex.bbo.AAH6` — watch bid/ask updates
   - Subscribe to `ex.md.AAH6.*` — watch fills and trades
   - Query `EX_META` KV bucket — learn contract specs (tick, limits, etc.)
2. Run taker standalone with `--sim` to watch how fills propagate through market data feed
3. Measure latencies, observe price behavior, understand fill semantics

**Expected outcome:** Clear mental model of protocol, instrument specs, market dynamics

### Phase 3: Build Quoter Strategy
1. **Language choice:** Pick non-Python (suggest Go for simplicity + NATS support)
2. **Algorithm:**
   - Subscribe to BBO feed for the contract
   - Calculate fair value (simple: mid of best bid/ask, or volume-weighted)
   - Post limit orders ±N ticks around fair value at multiple price levels
   - On price move, cancel old orders and re-quote around new fair value
   - Track own position from market data feed
   - Implement basic position limits (stop quoting if too long/short)
3. **Iterative refinement:** 
   - Start with single price level, widen quotes
   - Gradually add multiple levels
   - Tune spread and size parameters

**Expected outcome:** Quoter makes consistent small profits on each spread cycle

### Phase 4: Build Hedger
1. **Discovery:** Subscribe to status broadcasts from taker and quoter
   - Parse `strat.{SENDER}.status` messages to extract position + cash
2. **Aggregation:** Maintain cumulative desk position
3. **Hedging logic:**
   - If desk is long (net positive): send sell market order to reduce
   - If desk is short (net negative): send buy market order to reduce
   - Size: aim to neutralize exposure but not overshoot
4. **Rate awareness:** Respect exchange's max_tps to avoid disconnects

**Expected outcome:** Desk position stays small even under taker + quoter activity

### Phase 5: Integration Testing
1. Bring up full stack: `./run.sh --sim --strategy`
2. Observe all three processes working together
3. Check metrics: desk PnL, position turnover, max drawdown, order fill rates
4. Iterate on parameters if needed

### Phase 6: Documentation & Submission
1. Write final NOTES.md with design decisions and learnings
2. Export full transcript of AI conversations into TRANSCRIPT.txt
3. Clean up and package: `your@email.com.tar.gz`

---

## Assumptions We're Making

1. **Protocol interpretation:**
   - Sender ID must match subject (e.g., SENDER="QUOTE001" → send to "ex.req.QUOTE001")
   - All fills for a sender appear on "ex.md.<FEED>.<SENDER>"
   - BBO feed is independent (not per-sender)

2. **Market-making model:**
   - Quoter will make money on small bid-ask spreads
   - Sufficient liquidity exists at sample market to offset our position through hedger
   - Price movement is slow enough that quote staleness isn't catastrophic

3. **Coordination:**
   - NATS message ordering is sufficient (no need for explicit locking or sequencing)
   - Status broadcasts are reliable for position discovery
   - Hedger can react fast enough to prevent large unhedged positions

4. **Grading expectations:**
   - Evaluators care about the *process* (AI-guided reasoning) as much as the result
   - A working but simple strategy is better than complex code with unclear reasoning
   - Documentation of assumptions and learning is valued

---

## Next Steps

1. **Immediate:** Fix the two taker bugs and verify with local test
2. **Short-term:** Probe protocol with nats CLI, understand market behavior
3. **Medium-term:** Build quoter and hedger, starting with minimal working versions
4. **Long-term:** Refine parameters, document learnings, prepare submission

---

*Last updated: 2026-09-04 (initial discovery phase)*
