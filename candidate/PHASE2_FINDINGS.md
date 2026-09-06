# Phase 2: Protocol Exploration & Findings

## Overview

This document records our hands-on exploration of the TRV exchange protocol using the NATS CLI. We'll discover the exact behavior of market data, order entry, fills, cancellation, and edge cases through practical experimentation.

---

## Exploration Steps & Questions

### 1️⃣ Exchange Metadata (EX_META KV Bucket)

**Commands to run:**
```bash
nats kv ls EX_META                    # List all contracts
nats kv get EX_META AAH6              # Get AAH6 details
nats kv get EX_META AAM6              # Back month
nats kv get EX_META AAU6              # Back month
```

**Questions:**
- **Q1:** What is the tick size (minimum price increment) for AAH6?
- **Q2:** What are the min and max volumes allowed per order?
- **Q3:** What is the position limit (max absolute position)?
- **Q4:** What is max_tps (max transactions per second per feed)?

**Findings:**
```
Tick size: [to be filled]
Min volume: [to be filled]
Max volume: [to be filled]
Position limit: [to be filled]
Max TPS: [to be filled]
```

---

### 2️⃣ Market Data Feed (BBO & Market Data)

**Commands to run:**
```bash
# Terminal 1: Watch BBO updates
nats sub 'ex.bbo.AAH6'

# Terminal 2: Watch all market data events
nats sub 'ex.md.AAH6.*'

# Terminal 3: Watch price movements over 30 seconds
nats sub 'ex.md.AAH6.*' --raw  # See raw format
```

**Questions:**
- **Q5:** What message types appear in the market data? (A=add, E=execution, T=trade, C=cancel)
- **Q6:** How frequently does BBO update? (every tick? only on price change?)
- **Q7:** Do market data messages include timestamps? What format? (nanoseconds? milliseconds?)
- **Q8:** What are the exact fields in an E (execution) message?

**Findings:**
```
Message types observed: [to be filled]
BBO update frequency: [to be filled]
Timestamp format: [to be filled]
E message fields: [to be filled]
```

---

### 3️⃣ Order Entry & Limit Orders

**Commands to run:**
```bash
# Terminal 1: Watch market data
nats sub 'ex.md.AAH6.*'

# Terminal 2: Place a buy limit order
nats req 'ex.req.TEST0001' 'TEST0001 A AAH6 ORDER001 B 5 600 L'

# Terminal 3: Try a buy at very high price (likely to fill)
nats req 'ex.req.TEST0001' 'TEST0001 A AAH6 ORDER002 B 3 1000 L'
```

**Questions:**
- **Q9:** What does the exchange reply with for a successful order? (format: "EXCHANGE Y <n>" where n=?)
- **Q10:** Do you see an "A" (add) message on the market data feed when order rests?
- **Q11:** If order fills partially, do you see E (execution) messages? One per fill or aggregated?
- **Q12:** If order is rejected, does the exchange send any market data event? (Or just a reply?)

**Findings:**
```
Success reply format: [to be filled]
Add message: [yes/no] When? [to be filled]
Fill messages: [to be filled]
Rejection: [to be filled]
```

---

### 4️⃣ Fill-and-Kill (F) Orders

**Commands to run:**
```bash
# Terminal 1: Watch market data
nats sub 'ex.md.AAH6.*'

# Terminal 2: Place an aggressive F order (cross the spread)
# First check current BBO with: nats sub 'ex.bbo.AAH6'
# Then place F order at a price likely to partially fill
nats req 'ex.req.TEST0001' 'TEST0001 A AAH6 ORDER003 B 20 700 F'

# Terminal 3: Place F order with insufficient liquidity
nats req 'ex.req.TEST0001' 'TEST0001 A AAH6 ORDER004 B 1000 600 F'
```

**Questions:**
- **Q13:** Protocol says F orders "execute atomically" (v2.3+). Does this mean: (a) fills in full or (b) rejects with no partial fill?
- **Q14:** Do you see E (execution) messages for the successful F order? How many?
- **Q15:** For the F order with insufficient liquidity, does it: (a) reject entirely, (b) partially fill, or (c) something else?

**Findings:**
```
F order atomicity: [to be filled]
Execution messages: [to be filled]
Low liquidity behavior: [to be filled]
```

---

### 5️⃣ Order Cancellation

**Commands to run:**
```bash
# Terminal 1: Watch market data
nats sub 'ex.md.AAH6.*'

# Terminal 2: Post limit orders
nats req 'ex.req.TEST0001' 'TEST0001 A AAH6 ORDER005 B 5 595 L'
nats req 'ex.req.TEST0001' 'TEST0001 A AAH6 ORDER006 B 5 590 L'

# Terminal 3: Cancel one
nats req 'ex.req.TEST0001' 'TEST0001 C AAH6 ORDER005'

# Terminal 4: Try to cancel non-existent order
nats req 'ex.req.TEST0001' 'TEST0001 C AAH6 DOESNTEXIST'
```

**Questions:**
- **Q16:** What does the exchange reply with? (format: "EXCHANGE Y 1" or "EXCHANGE N <code>")
- **Q17:** Do you see a "C" (cancel) message on the market data feed?
- **Q18:** If order was already partially filled before cancel, what happens?

**Findings:**
```
Cancel reply format: [to be filled]
Market data message: [yes/no, format: to be filled]
Partial fill cancellation: [to be filled]
Non-existent order: [to be filled]
```

---

### 6️⃣ Cancel Many (X Command)

**Commands to run:**
```bash
# Terminal 1: Watch market data
nats sub 'ex.md.AAH6.*'

# Terminal 2: Post multiple orders
nats req 'ex.req.TEST0001' 'TEST0001 A AAH6 ORDER010 B 5 585 L'
nats req 'ex.req.TEST0001' 'TEST0001 A AAH6 ORDER011 B 3 580 L'
nats req 'ex.req.TEST0001' 'TEST0001 A AAH6 ORDER012 S 5 605 L'

# Terminal 3: Cancel all buy orders
nats req 'ex.req.TEST0001' 'TEST0001 X AAH6 B 0'

# Terminal 4: Cancel all orders at specific price
nats req 'ex.req.TEST0001' 'TEST0001 X AAH6 X 585'
```

**Questions:**
- **Q19:** Does the X command respect the side (B/S) and price selectors, or does it cancel everything?
- **Q20:** What does the reply show? ("Y 2" = 2 orders cancelled?)

**Findings:**
```
X command behavior: [to be filled]
Count accuracy: [to be filled]
```

---

### 7️⃣ Self-Trade Prevention (Q/W Commands)

**Commands to run:**
```bash
# Terminal 1: Watch market data
nats sub 'ex.md.AAH6.*'

# Terminal 2: Enable STP (Q command)
nats req 'ex.req.TEST0001' 'TEST0001 Q AAH6'

# Terminal 3: Post a buy limit
nats req 'ex.req.TEST0001' 'TEST0001 A AAH6 ORDER020 B 5 600 L'

# Terminal 4: Try to sell at same price from same sender (should conflict)
nats req 'ex.req.TEST0001' 'TEST0001 A AAH6 ORDER021 S 3 600 F'

# Terminal 5: Disable STP and repeat
nats req 'ex.req.TEST0001' 'TEST0001 W AAH6'
nats req 'ex.req.TEST0001' 'TEST0001 A AAH6 ORDER022 S 3 600 F'
```

**Questions:**
- **Q21:** With STP enabled, do the buy and sell orders match against each other? Or just against the rest of the book?
- **Q22:** Without STP, do they match against each other?
- **Q23:** Can one order partially fill against itself before hitting the rest of the book?

**Findings:**
```
STP enabled behavior: [to be filled]
STP disabled behavior: [to be filled]
Self-matching rules: [to be filled]
```

---

### 8️⃣ Rate Limits

**Commands to run:**
```bash
# Get max_tps from metadata
nats kv get EX_META AAH6

# Terminal 1: Rapid-fire orders
for i in {1..100}; do
  nats req 'ex.req.TEST0001' "TEST0001 A AAH6 FAST$(printf '%05d' $i) B 1 600 L" &
done
wait

# Check if any orders were rejected
```

**Questions:**
- **Q24:** Do orders get rejected after hitting max_tps?
- **Q25:** What error code do rejected orders return? (Check PROTOCOL.md for reject codes; likely 306/307)
- **Q26:** Is the entire connection dropped, or just the orders rejected with error replies?

**Findings:**
```
Rate limit enforcement: [to be filled]
Error code: [to be filled]
Connection handling: [to be filled]
```

---

## Summary of Findings

### Key Protocol Details
- Atomic F order behavior: [to be filled]
- Market data message latency: [to be filled]
- Cancellation guarantees: [to be filled]
- Fill order granularity: [to be filled]

### Assumptions Validated
- [List which assumptions from NOTES.md were confirmed]

### Assumptions Challenged/Updated
- [List any surprising findings]

### Open Questions
- [Any protocol behaviors still unclear?]

---

## Next Steps

After completing this exploration:

1. **Update NOTES.md** — Add a "Phase 2" section with key findings
2. **Design the Quoter** — Use these insights to build market-making logic
3. **Prototype early** — Start with simplest possible quoter (single price level)

