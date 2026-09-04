#!/usr/bin/env bash
# Run the exchange, optionally with the sample market and/or your strategy.
#   ./run.sh                       exchange only
#   ./run.sh --sim                 + sample market
#   ./run.sh --strategy            + your strategy (from ./strategy)
#   ./run.sh --sim --strategy      everything (this is what grading runs)
set -e
cd "$(dirname "$0")"
./setup.sh
profiles=()
for a in "$@"; do
  case "$a" in
    --sim)      profiles+=(--profile sim) ;;
    --strategy) profiles+=(--profile strategy) ;;
    *) echo "unknown option: $a" >&2; exit 1 ;;
  esac
done
# --build: always rebuild from source so edits take effect (compose would
# otherwise happily reuse a stale image built from older code).
exec docker compose "${profiles[@]}" up --build
