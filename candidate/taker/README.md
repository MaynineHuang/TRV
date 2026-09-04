# Python taker strategy

The desk's existing momentum taker. It subscribes to the best-bid/offer feed
for one contract and, when the mid-price moves by `TAKER_THRESH` over the last
`TAKER_LAG` updates, crosses the spread with a fill-and-kill (`F`) order to
follow the move. It keeps its own position and mark-to-market PnL and
publishes them once a second on `strat.<sender>.status` (and to stdout).

In the full stack (`./run.sh --sim --strategy`) it runs as a container — the
desk's taker seat, trading the front month all session. The instructions below
are for running it by hand while probing.

## Run

Bring up the exchange + sample market first (`./run.sh --sim`), then:

```bash
python3 -m venv .venv && .venv/bin/pip install nats-py     # once
TAKER_FEED=<feed> .venv/bin/python taker/taker.py          # pick a listed feed
```

(`nats kv ls EX_META` lists the feeds; see `PROTOCOL.md`.)

Watch its self-reported state:

```bash
nats sub 'strat.PYTKR001.status'
```

## Config (env)

| Var           | Default | Meaning                                        |
|---------------|---------|------------------------------------------------|
| `TAKER_FEED`  | `BTH6`  | contract to trade                              |
| `TAKER_SENDER`| `PYTKR001` | 8-char sender tag                           |
| `TAKER_CLIP`  | `3`     | order size per trade                           |
| `TAKER_MAX_POS`| `30`   | max absolute position                          |
| `TAKER_THRESH`| `10`    | mid move (price units) that triggers a trade   |
| `TAKER_LAG`   | `5`     | BBO updates back the move is measured over     |
| `TAKER_RUN`   | `20`    | seconds to run                                 |
