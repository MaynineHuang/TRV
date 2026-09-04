# Trading-desk task

## Notes

Use an AI agent of your choice to help you solve this task.

Your task, and supporting docs, are deliberately left incomplete and ambiguous,
to test your ability to work in a realistic subpar codebase.


## Brief:

You trade for **Cannon Capital**, a startup prop trading firm.

You have been assigned to a desk that trades a single exchange with 100,000 usd margin.
Your job is to expand the desks suite of trading processes.
Contracts on this exchange are cash-settled and worth exactly their listed price in usd.

Read **`TASK.md`** for the full brief and **`PROTOCOL.md`** for the exchange
wire protocol. Below is some info on getting started.


## Prerequisites

You are given a simulated exchange (a Docker image) that speaks a simple
message protocol over [NATS](https://nats.io).

You need:

- Docker + Docker Compose.
- An x86-64 machine, or emulation: the provided exchange image is
  `linux/amd64`. On Apple Silicon, Docker Desktop emulates it automatically
  (a platform warning is normal). On an arm64 Linux box, enable binfmt
  first: `docker run --privileged --rm tonistiigi/binfmt --install amd64`.
  Everything you build yourself runs natively either way.
- Python 3 if you want to run the taker on the host while probing
  (`taker/`, see its README) — in the full stack it runs as a container.
- The `nats` CLI is handy for probing (optional):
  https://github.com/nats-io/natscli — `nats context` defaults to
  `nats://localhost:4222`, which is what the exchange exposes.

## Run the exchange

```bash
./run.sh            # NATS + exchange
./run.sh --sim      # NATS + exchange + a sample market to trade against
```

(Equivalently: `docker compose up` / `docker compose --profile sim up`.) The
first run loads the exchange image; NATS is published on
**`nats://localhost:4222`** for development (handy with the `nats` CLI).

- **Without `--sim`** the book starts empty — good for controlled probing (you
  place orders and see exactly what happens).
- **With `--sim`** a simplistic sample market runs: background liquidity,
  prices that move around, casual takers.

Stop with Ctrl-C; `docker compose down` to clean up.

## Run your desk

The three trading processes will live in **`taker/`** (provided), **`strategy/`** and
**`hedger/`**. Once your code + Dockerfiles are in
place:

```bash
docker compose --profile sim --profile strategy up   # exchange + sample market + all three seats
```

(`./run.sh --sim --strategy` is the same thing — exactly what grading runs.)

Inside the compose network every seat reaches the exchange at
`nats://nats:4222`. While developing you can also run any seat directly on
the host against `nats://localhost:4222` — but the final submission must work
as containers from a clean checkout.
