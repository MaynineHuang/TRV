# Task

You will oversee 3 separate trading processes.

- **The taker** (`taker/`) — the firm's existing Python strategy. Legacy code;
  you own it now. It runs alongside your work.
- **The quoter** (`strategy/`) — you build this.
- **The hedger** (`hedger/`) — you build this.

Your two jobs:

## Job 1 — a quoting strategy

Write a **low-risk, profitable quoting strategy**: it should make its money
providing two-sided liquidity, not taking directional bets.

- **Language:** any language supported by NATS, **except Python**.

## Job 2 — keep the desk flat (the hedger)

The desk's **combined position** — taker + quoter + hedger together — should
be kept low. Build a hedger process that makes that true:
when the desk's other seats accumulate exposure, the hedger reduces it,
promptly, and keeps it low.

- How the desk's processes coordinate is up to you — you already have a
  message bus.
- **Language:** your choice (Python is allowed here).

The main purpose of the hedger is risk control. Having a small open position for a long time
is relatively low risk. Having a very large open position even for just a second is high risk
(a large open position combined with a large market move that goes in the wrong direction could
put you out of business).

## Mechanics

- Each seat ships as a **Docker container**: `taker/` (provided), `strategy/`
  and `hedger/` (yours — put code and a `Dockerfile` in each).
  `./run.sh --sim --strategy` brings up the whole stack: exchange + sample
  market + all three seats (equivalently
  `docker compose --profile sim --profile strategy up`).
- Each seat sends orders with its own sender id, which it reads from the environment.
  Our grading script injects real values; fall back to sensible defaults for local dev.
  - **`$SENDER`** (quoter),
  - **`$TAKER_SENDER`** (taker),
  - **`$HEDGER_SENDER`** (hedger).

- Every seat connects to the exchange at **`$NATS_URL`**
  (`nats://nats:4222` inside the compose network) — no host dependencies.
- Grading builds and runs your Dockerfiles on **`linux/amd64`** — build
  from source inside the Dockerfile; don't `COPY` in binaries compiled on
  your machine.
- See `README.md` to run everything and `PROTOCOL.md` for the wire protocol.

### How it's graded

Your desk runs unattended in our private grading market simulation for a
fixed session. When the session ends, resting orders are cancelled and any
remaining position is liquidated against the book.
We look at some risk and profitability metrics, as well as code quality, design quality,
and how you direct your AI agent. The grading market is not the sample market.

We expect you to use an AI agent; the question is not whether you used one but how.
Two things matter to us, roughly equally:
- a desk that works — quoting profitably while keeping the position flat is a real result, not a formality
- and a clear account of how you got there.
Treat this as a realistic codebase: the documentation is incomplete in places, and the code you have been
given is now yours, whatever state it is in. NOTES.md and TRANSCRIPT.txt are where you show us the
reasoning behind the result — what you assumed, what you checked, what surprised you. We would rather see
how you convinced yourself something was true than a tidy write-up composed afterwards; if you built
something along the way to answer a question, include it. Be ready to explain any line you ship.

## Deliverables

- **`strategy/` and `hedger/`** with working Dockerfiles — plus whatever
  changes you made anywhere else in the repo, at the same relative paths
  (e.g. if you changed `taker/`, include your `taker/`). From a clean
  checkout, `./run.sh --sim --strategy` must bring up your working desk.
- **`NOTES.md`** — a short notes file: your design decisions, including any
  assumptions you made and hurdles you had to tackle.
- **`TRANSCRIPT.txt`** — your complete AI agent transcript. A raw export or
  a copy-paste is fine; if you used multiple sessions, concatenate them
  into this one file.
- Include any probes, helper scripts or test tooling you wrote — we want to
  see them.

Submission upload: https://www.dropbox.com/request/54m5donacqj8ng5d0a9x

Submit a single file, a compressed directory, `<your_email>.tar.gz` or
`<your_email>.zip`.

Your submission should decompress to:

```
your@email.com/
  strategy/
    ...
  hedger/
    ...
  taker/            # include if you changed it
  NOTES.md
  TRANSCRIPT.txt
  <any other files/scripts/tests you wrote>
  <to keep submission size small, please remove other files/directories, unless you have changed them>
```



