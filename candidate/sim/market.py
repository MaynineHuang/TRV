#!/usr/bin/env python3
"""Sample market for developing your strategy.

A small set of synthetic participants that make the contracts on underlying "AA"
(front AAH6, backs AAM6, AAU6) behave like a real-ish market: background
liquidity on every month, casual takers, and a "mover" that walks the front-month
price around and occasionally sweeps the book aggressively. It is deliberately
simpler than what we grade against — use it to see your quoter work.

Run it pointed at the exchange's NATS (see the project README). It runs until you
stop it. Env: NATS_URL (default nats://127.0.0.1:4222), SIM_SEED (default 1).
"""
import asyncio
import os
import random
import threading
import time

import nats

NATS_URL = os.environ.get("NATS_URL", "nats://127.0.0.1:4222")
SEED = int(os.environ.get("SIM_SEED", "1"))

FRONT = "AAH6"
CONTRACTS = {"AAH6": {"rel": 0}, "AAM6": {"rel": 15}, "AAU6": {"rel": 30}}
ALL = list(CONTRACTS)
TICK = 1
START = 600


def now():
    return time.monotonic()


class Conn:
    def __init__(self, sender):
        self.sender, self.nc = sender, None
        self.oid = random.randint(0, 80_000_000)

    async def connect(self):
        self.nc = await nats.connect(NATS_URL)

    def _noid(self):
        self.oid += 1
        return f"{self.oid:08d}"

    async def add(self, feed, side, vol, px, typ="L"):
        oid = self._noid()
        await self.nc.publish(
            f"ex.req.{self.sender}",
            f"{self.sender} A {feed} {oid} {side} {int(vol)} {int(px)} {typ}".encode())
        return oid

    async def cancel(self, feed, oid):
        await self.nc.publish(f"ex.req.{self.sender}", f"{self.sender} C {feed} {oid}".encode())

    async def close(self):
        try:
            await self.nc.flush()
            await self.nc.drain()
        except Exception:
            pass


class BboCache:
    def __init__(self):
        self.bbo = {}

    async def subscribe(self, nc):
        await nc.subscribe("ex.bbo.*", cb=self._cb)

    async def _cb(self, msg):
        f = msg.data.decode().split()
        if len(f) < 6:
            return
        bid = None if f[2] == "-" else int(f[2])
        ask = None if f[4] == "-" else int(f[4])
        self.bbo[f[1]] = (bid, int(f[3]), ask, int(f[5]))

    def get(self, feed):
        return self.bbo.get(feed)


def fair_value(b):
    if b is None:
        return None
    bid, bv, ask, av = b
    if bid is None and ask is None:
        return None
    if bid is None:
        return float(ask)
    if ask is None:
        return float(bid)
    if ask - bid >= 2 * TICK:          # wide -> mid
        return (bid + ask) / 2.0
    if bv + av == 0:
        return (bid + ask) / 2.0
    return (bid * av + ask * bv) / (bv + av)


class Book:
    """Front-month book reconstruction for the mover (ignores T)."""

    def __init__(self):
        self.bids, self.asks, self.orders = {}, {}, {}

    async def subscribe(self, nc, feed):
        await nc.subscribe(f"ex.md.{feed}.*", cb=self._cb)

    async def _cb(self, msg):
        f = msg.data.decode().split()
        t = f[1]
        if t == "A":
            self.orders[f[2]] = [f[3], int(f[5]), int(f[4])]
            lv = self.bids if f[3] == "B" else self.asks
            lv[int(f[5])] = lv.get(int(f[5]), 0) + int(f[4])
        elif t == "E":
            for oid in (f[2], f[3]):
                o = self.orders.get(oid)
                if o:
                    o[2] -= int(f[4])
                    lv = self.bids if o[0] == "B" else self.asks
                    lv[o[1]] = lv.get(o[1], 0) - int(f[4])
                    if lv.get(o[1], 0) <= 0:
                        lv.pop(o[1], None)
        elif t == "C":
            o = self.orders.pop(f[2], None)
            if o and o[2] > 0:
                lv = self.bids if o[0] == "B" else self.asks
                lv[o[1]] = lv.get(o[1], 0) - o[2]
                if lv.get(o[1], 0) <= 0:
                    lv.pop(o[1], None)

    def best_bid(self):
        return max(self.bids) if self.bids else None

    def best_ask(self):
        return min(self.asks) if self.asks else None


# --------------------------------------------------------------------------- #
async def quoter(sender, contract, deadline):
    conn = Conn(sender)
    await conn.connect()
    bbo = BboCache()
    await bbo.subscribe(conn.nc)
    rel = CONTRACTS[contract]["rel"]
    volume = random.randint(2, 6)
    levels = random.randint(4, 8)
    offset = random.randint(2, 5)
    live, center = [], [None]

    async def requote(c):
        for _, oid in live:
            await conn.cancel(contract, oid)
        live.clear()
        for i in range(levels):
            live.append(("B", await conn.add(contract, "B", volume, c - offset - i)))
            live.append(("S", await conn.add(contract, "S", volume, c + offset + i)))
        await conn.nc.flush()
        center[0] = c

    async def on_bbo(_m):
        fv = fair_value(bbo.get(FRONT))
        if fv is None:
            return
        c = int(round(fv + rel))
        if c != center[0]:
            await requote(c)

    await requote(START + rel)
    await conn.nc.subscribe(f"ex.bbo.{FRONT}", cb=on_bbo)
    while now() < deadline:
        await asyncio.sleep(0.1)
    await conn.close()


async def taker(sender, deadline):
    # Casual flow: crosses the spread with F (fill-and-kill) orders. F executes
    # atomically on the v2.3+ engine (fills in full or rejects), so there is no
    # partial-execution handling here.
    conn = Conn(sender)
    await conn.connect()
    bbo = BboCache()
    await bbo.subscribe(conn.nc)
    while now() < deadline:
        await asyncio.sleep(random.uniform(0.05, 0.5))
        b = bbo.get(random.choice(ALL))
        if b is None:
            continue
        bid, ask = b[0], b[2]
        if random.random() < 0.5 and ask is not None:
            await conn.add(random.choice(ALL), "B", 1 + int(20 * random.random() ** 2),
                           ask + random.randint(0, 6), "F")
        elif bid is not None:
            await conn.add(random.choice(ALL), "S", 1 + int(20 * random.random() ** 2),
                           bid - random.randint(0, 6), "F")
        await conn.nc.flush()


async def mover(sender, deadline):
    conn = Conn(sender)
    await conn.connect()
    book = Book()
    await book.subscribe(conn.nc, FRONT)
    # seed an initial market on every contract
    for c in ALL:
        init = START + CONTRACTS[c]["rel"]
        await conn.add(c, "B", 20, init - 1)
        await conn.add(c, "S", 20, init + 1)
    await conn.nc.flush()

    target = START
    next_move = now() + 3
    while now() < deadline:
        await asyncio.sleep(0.2)
        if now() >= next_move:
            shock = random.random() < 0.3                 # ~1/3 of moves are sharp
            step = random.randint(20, 60) * (2 if shock else 1)
            target = max(440, min(760, target + random.choice([-1, 1]) * step))
            next_move = now() + random.uniform(2.5, 4.5)
        # walk the front toward target: marketable limit at target + market poke
        bid, ask = book.best_bid(), book.best_ask()
        if bid is None or ask is None:
            continue
        cur = (bid + ask) / 2.0
        if abs(target - cur) < 2:
            continue
        if target > cur:
            need = sum(v for px, v in book.asks.items() if px < target)
            await conn.add(FRONT, "B", int(need * 1.2) + 20, target, "L")
        else:
            need = sum(v for px, v in book.bids.items() if px > target)
            await conn.add(FRONT, "S", int(need * 1.2) + 20, target, "L")
        await conn.nc.flush()
    await conn.close()


def main():
    random.seed(SEED)
    deadline = now() + float(os.environ.get("SIM_DURATION", "86400"))
    threads = []

    def spawn(fn, *a):
        t = threading.Thread(target=lambda: asyncio.run(fn(*a)), daemon=True)
        t.start()
        threads.append(t)

    spawn(mover, "MOVER001", deadline)
    time.sleep(1.5)
    qn = 0
    for c in ALL:
        for _ in range(2):
            qn += 1
            spawn(quoter, f"BGQUOT{qn:02d}", c, deadline)
    spawn(taker, "TAKER001", deadline)
    spawn(taker, "TAKER002", deadline)
    print(f"[market] running on {NATS_URL} (Ctrl-C to stop)", flush=True)
    for t in threads:
        t.join()


if __name__ == "__main__":
    main()
