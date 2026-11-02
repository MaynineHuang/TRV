"""Regression tests for the provided taker's order routing and accounting.

These tests deliberately mock NATS so they can run before Docker/the exchange
is available.  Live exchange behaviour is covered separately by the Phase 1
manual integration check in NOTES.md.
"""
import asyncio
import importlib.util
import sys
import types
import unittest
from pathlib import Path


# ``taker.py`` imports nats at module load, but these unit tests exercise only
# its local request construction and accounting logic.
sys.modules.setdefault("nats", types.SimpleNamespace())
TAKER_PATH = Path(__file__).resolve().parents[1] / "taker" / "taker.py"
SPEC = importlib.util.spec_from_file_location("taker_under_test", TAKER_PATH)
taker = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(taker)


class Reply:
    data = b"EXCHANGE Y 3"


class FakeNats:
    def __init__(self):
        self.calls = []

    async def request(self, subject, payload, timeout):
        self.calls.append((subject, payload.decode(), timeout))
        return Reply()

    async def publish(self, subject, payload):
        self.calls.append((subject, payload.decode(), None))


class TakerRegressionTests(unittest.TestCase):
    def test_sell_fill_reduces_position_and_increases_cash(self):
        desk = taker.Taker(FakeNats())

        desk.apply_fill("S", 3, 101)

        self.assertEqual(desk.position, -3)
        self.assertEqual(desk.cash, 303)

    def test_buy_fill_increases_position_and_spends_cash(self):
        desk = taker.Taker(FakeNats())

        desk.apply_fill("B", 2, 101)

        self.assertEqual(desk.position, 2)
        self.assertEqual(desk.cash, -202)

    def test_orders_use_sender_specific_request_subject(self):
        nc = FakeNats()
        desk = taker.Taker(nc)
        desk.best_ask = 101

        asyncio.run(desk.take("B"))

        self.assertEqual(nc.calls[0][0], f"ex.req.{taker.SENDER}")
        self.assertIn(f"{taker.SENDER} A {taker.FEED}", nc.calls[0][1])


if __name__ == "__main__":
    unittest.main()
