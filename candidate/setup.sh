#!/usr/bin/env bash
# Ensures the simulated-exchange image is available locally.
set -e
cd "$(dirname "$0")"
if docker image inspect sim-exchange:candidate >/dev/null 2>&1; then
  exit 0
fi
if [ -f exchange/image.tar.xz ]; then
  if ! command -v xz >/dev/null 2>&1; then
    echo "ERROR: 'xz' is required to unpack the exchange image (install xz-utils)." >&2
    exit 1
  fi
  echo "Loading exchange image from exchange/image.tar.xz ..."
  xz -dc exchange/image.tar.xz | docker load
elif [ -f exchange/image.tar.gz ]; then
  echo "Loading exchange image from exchange/image.tar.gz ..."
  gunzip -c exchange/image.tar.gz | docker load
else
  echo "ERROR: 'sim-exchange:candidate' image not present and exchange/image.tar.xz is missing." >&2
  echo "Ask the task organisers for the exchange image." >&2
  exit 1
fi
