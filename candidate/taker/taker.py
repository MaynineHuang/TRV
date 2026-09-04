#!/usr/bin/env python3
"""Momentum taker strategy.

Watches the best-bid/offer for one contract and, when the mid-price moves far
enough in one direction, crosses the spread with a fill-and-kill order to follow
the move. Tracks its own position and mark-to-market PnL and reports them once a
second on `strat.<sender>.status`.

Config (env):
  NATS_URL        default nats://127.0.0.1:4222
  TAKER_FEED      contract to trade            (default BTH6)
  TAKER_SENDER    8-char sender tag            (default PYTKR001)
  TAKER_CLIP      order size per trade         (default 3)
  TAKER_MAX_POS   max absolute position        (default 30)
  TAKER_THRESH    mid move (price units) that triggers a trade (default 10)
  TAKER_LAG       how many BBO updates back the move is measured (default 5)
  TAKER_RUN       seconds to run               (default 20)
"""
import asyncio
import collections
import os
import random

import nats

NATS_URL = os.environ.get("NATS_URL", "nats://127.0.0.1:4222")
FEED = os.environ.get("TAKER_FEED", "BTH6")
SENDER = os.environ.get("TAKER_SENDER", "PYTKR001")
CLIP = int(os.environ.get("TAKER_CLIP", "3"))
MAX_POS = int(os.environ.get("TAKER_MAX_POS", "30"))
THRESH = int(os.environ.get("TAKER_THRESH", "10"))
LAG = int(os.environ.get("TAKER_LAG", "5"))
RUN_S = float(os.environ.get("TAKER_RUN", "20"))


class Taker:
    def __init__(self, nc):
        self.nc = nc
        self.oid = random.randint(0, 80_000_000)  # avoid id clashes across runs
        self.best_bid = None
        self.best_ask = None
        self.mids = collections.deque(maxlen=LAG + 1)
        self.position = 0
        self.cash = 0.0       # signed: buys spend cash, sells receive cash
        self.fills = 0
        self.send_lock = asyncio.Lock()

    def next_oid(self):
        self.oid += 1
        return f"{self.oid:08d}"

    def mid(self):
        if self.best_bid is None or self.best_ask is None:
            return None
        return (self.best_bid + self.best_ask) / 2

    async def on_bbo(self, msg):
        # payload: "<ts> <FEED> <bid_px> <bid_vol> <ask_px> <ask_vol>", '-' if empty
        f = msg.data.decode().split()
        if len(f) < 6:
            return
        self.best_bid = None if f[2] == "-" else int(f[2])
        self.best_ask = None if f[4] == "-" else int(f[4])
        m = self.mid()
        if m is None:
            return
        self.mids.append(m)
        await self.maybe_trade()

    async def maybe_trade(self):
        if len(self.mids) < self.mids.maxlen:
            return
        past, now = self.mids[0], self.mids[-1]
        if now - past >= THRESH and self.position < MAX_POS and self.best_ask is not None:
            await self.take("B")
        elif past - now >= THRESH and self.position > -MAX_POS and self.best_bid is not None:
            await self.take("S")

    async def take(self, side):
        async with self.send_lock:
            px = self.best_ask if side == "B" else self.best_bid
            oid = self.next_oid()
            order = f"{SENDER} A {FEED} {oid} {side} {CLIP} {px} F"
            try:
                reply = await self.nc.request("ex.req", order.encode(), timeout=1.0)
            except Exception:
                return  # timed out; treat as no fill
            parts = reply.data.decode().split()
            # parts looks like ["EXCHANGE", "Y", "<n>"] on accept or
            # ["EXCHANGE", "N", "<code>", ...] on reject. parts[2] is just an
            # exchange-side detail field; for accepted orders we don't need it.
            if len(parts) >= 2 and parts[1] == "Y":
                # Fill-and-kill orders are marketable: they cross the spread and
                # fill in full against the resting book, so the size we asked for
                # is the size we got.
                filled = CLIP
                self.apply_fill(side, filled, px)
                self.fills += 1

    def apply_fill(self, side, qty, px):
        signed = qty if side == "B" else qty
        self.position += signed
        self.cash -= signed * px

    def pnl(self):
        m = self.mid()
        return self.cash + (self.position * m if m is not None else 0)

    async def publish_status(self):
        s = (f"pos={self.position} cash={self.cash:.0f} "
             f"pnl={self.pnl():.0f} fills={self.fills}")
        print(f"[taker] {s}", flush=True)
        await self.nc.publish(f"strat.{SENDER}.status", s.encode())

    async def reporter(self):
        while True:
            await asyncio.sleep(1.0)
            await self.publish_status()


async def main():
    nc = await nats.connect(NATS_URL)
    t = Taker(nc)
    await nc.subscribe(f"ex.bbo.{FEED}", cb=t.on_bbo)
    print(f"[taker] {SENDER} trading {FEED} clip={CLIP} thresh={THRESH} "
          f"for {RUN_S}s", flush=True)
    rep = asyncio.create_task(t.reporter())
    await asyncio.sleep(RUN_S)
    rep.cancel()
    await t.publish_status()
    print(f"[taker] final: position={t.position} pnl={t.pnl():.0f} "
          f"fills={t.fills}", flush=True)
    await nc.drain()


if __name__ == "__main__":
    asyncio.run(main())
