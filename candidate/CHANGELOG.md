# Exchange changelog


## v2.4 — 2026-05

- Multi-shard matching: instruments are partitioned across matching shards
  (`EX_SHARDS`). Ordering guarantees are per-instrument, as before.
- Hot-path allocation removed; per-event latency counters added.
- Minor perf imperoments using boost containers

## v2.3 — 2026-02

- Matching: `F` (fill-and-kill) orders now execute atomically — they fill in
  full or reject. Partial executions no longer occur; internal strategies have
  been simplified accordingly.
- Per-feed transaction rate limiting (`max_tps`, reject codes `306`/`307`).
  Exceeding rate will disconnect user

## v2.2 — 2025-11

- Self-trade prevention: per-feed opt-in via `Q`, opt-out via `W`.
- `X` (cancel-many) accepted across instrument groups.
- split `E` into `E` and `T`

## v2.1 — 2025-09

- Market data and best-bid/offer moved to JetStream (`ex.md.<feed>.<sender>`,
  `ex.bbo.<feed>`); instrument metadata published to the `EX_META` KV bucket.

## v2.0 — 2025-08

- Protocol v2: space-separated ASCII over NATS request/reply. Order types
  `L`/`M`/`F`; reject-code overhaul.
- Added STP; on by default

## v1.0 — 2025-06

- inital mvp; can enter cancel and trade orders
