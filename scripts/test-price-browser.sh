#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# The explicit project name isolates all state, networks and media from development.
repo_root=$(pwd)
compose=(docker compose -p partygame-price-e2e -f "$repo_root/docker-compose.yml" -f "$repo_root/compose.price-e2e.yml")
cleanup() { "${compose[@]}" down -v --remove-orphans; }
trap cleanup EXIT
"${compose[@]}" up --build -d --wait api frontend gateway
"${compose[@]}" exec -T api python -m tests.seed_price_e2e
cd frontend
PRICE_E2E_URL="http://127.0.0.1:${PRICE_E2E_PORT:-18080}" pnpm run test:browser "$@"
