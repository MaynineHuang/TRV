# Exchange protocol v2.5

The exchange speaks **space-separated ASCII messages over NATS**. Fields never
contain spaces. There are three things to talk to:

| What                 | NATS subject              | Mechanism            |
|----------------------|---------------------------|----------------------|
| Order entry          | `ex.req.<SENDER>`         | request / reply      |
| Market data          | `ex.md.<FEED>.<SENDER>`   | publish (JetStream)  |
| Best bid/offer        | `ex.bbo.<FEED>`           | publish (JetStream)  |
| Instrument metadata  | KV bucket `EX_META`       | JetStream KV         |

- A **`<FEED>`** (feedcode) is 4 chars: 2 for the underlying + 2 for the expiry,
  e.g. `AAH6`. All feedcodes on the same underlying share the prefix (`AA`).
- A **`<SENDER>`** is an 8-char identity tag you choose for your strategy.
- An **order id** is 8 chars you choose, unique per sender. Publicly an order is
  identified by the 17-char `sender:orderid`.
- Prices and volumes are integers.

## Order entry — `ex.req.<SENDER>` (request/reply)

Publish your request to **`ex.req.<your-sender>`** (NATS request/reply; the reply
comes back on the inbox). The sender in the subject is what the exchange acts on,
and it **must match** the `<SENDER>` at the start of your message — you can only
enter and cancel orders for your own sender. Every request starts with your
`<SENDER>` then a 1-char type.

| Type | Meaning      | Fields after `<SENDER> <type>`                                   |
|------|--------------|------------------------------------------------------------------|
| `A`  | add order    | `<FEED> <id:8> <B\|S> <volume> <price> <M\|L\|F>`                 |
| `C`  | cancel order | `<FEED> <id:8>`                                                  |
| `X`  | cancel many  | `<FEED> <B\|S\|X> <price>`  — see below                           |
| `Q`  | enable STP   | `<FEED>`                                                         |
| `W`  | disable STP  | `<FEED>`                                                          |

Order types: **`L`** = limit (rests on the book), **`M`** = market, **`F`** =
fill-and-kill (executes what it can immediately, cancels the rest). Only `L`
rests.

**Replies** start with the exchange's tag, then:
- `Y <n>` — accepted. For `A`, `<n>` is the volume that traded immediately. For
  `C`/`X`, `<n>` is how many orders were cancelled.
- `N <code> <text>` — rejected.

Reject codes are stable numbers with a short text. A few you will hit early:
`100` malformed · `202` bad feedcode · `203` re-used order id. The rest are
yours to catalogue by experiment.

### `X` — cancel many

`X <FEED> <B|S|X> <price>` cancels several of **your** resting orders at once and
replies `Y <n>` with the number cancelled. The `<FEED>` may also select more than
one expiry, price may select more than one price

## Market data — `ex.md.<FEED>.<SENDER>`

Subscribe to `ex.md.<FEED>.*` to see all market data for a contract, or to
`ex.md.<FEED>.<your-sender>` for just your own. Every message is prefixed with an
`int64` nanosecond timestamp.

| Type | Fields after `<ts> <type>`                                          |
|------|---------------------------------------------------------------------|
| `A`  | `<id:17> <B\|S> <volume> <price>`  — order added to the book          |
| `E`  | `<incoming:17> <resting:17> <volume> <price> <matchid> <B\|S>`        |
| `C`  | `<id:17>`  — order removed from the book                              |
| `T`  | same fields as `E`                                                    |

- `E` is an **execution**. The trailing `B`/`S` is the **aggressor's side**. An
  order may fill over **several** `E` messages — accumulate them.
- `T` reports a **trade** — useful for watching trade flow.
- Your own fills show up on `ex.md.<FEED>.<your-sender>`.

## Best bid/offer — `ex.bbo.<FEED>`

`<ts> <FEED> <bid_px> <bid_vol> <ask_px> <ask_vol>`, with `-` for an empty side.
Updated as the top of book changes.

## Instrument metadata — KV `EX_META`

Key = feedcode; value is `key=value` pairs: `ticksize`, `ref_price`, `band`
(price band is `ref_price ± band`), `min_volume`, `max_volume`, `position_limit`,
`max_tps`, `last_traded_price`. Read it to learn each contract's tick, price
band, and limits.

```bash
nats kv ls  EX_META
nats kv get EX_META AAH6
```

## Probing

The `nats` CLI is the fastest way to explore before you write code: `nats sub`
on the feeds above, `nats req` for order entry, `nats kv` for `EX_META`.
