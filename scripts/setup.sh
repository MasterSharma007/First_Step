#!/usr/bin/env bash
set -euo pipefail

# AI-Based Bank Nifty Intraday Trading Platform - one-shot dev setup.
#
# Checks prerequisites, installs backend + frontend dependencies, starts
# Postgres/Redis/RabbitMQ, and runs database migrations. Safe to re-run -
# every step is skipped if already done. See docs/SETUP.md for details on
# what this does and how to do it manually instead.
#
# Usage: ./scripts/setup.sh

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

info() { printf '\033[1;34m==>\033[0m %s\n' "$1"; }
warn() { printf '\033[1;33m!!\033[0m %s\n' "$1"; }
fail() { printf '\033[1;31mERROR:\033[0m %s\n' "$1"; exit 1; }

require() {
  command -v "$1" >/dev/null 2>&1 || fail "$1 is required but not installed. $2"
}

info "Checking prerequisites"
require docker "Install Docker: https://docs.docker.com/get-docker/"
require node "Install Node.js 20+: https://nodejs.org/"
require npm "Comes with Node.js"

if ! command -v uv >/dev/null 2>&1; then
  warn "uv not found - installing (https://docs.astral.sh/uv/)"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

# Root .env: docker-compose host port overrides, so this doesn't clash
# with ports already used by other projects on your machine (5432/3000/8000
# are common defaults elsewhere). Only written if missing.
if [ ! -f "$ROOT_DIR/.env" ]; then
  info "Writing root .env (docker-compose port overrides)"
  cat > "$ROOT_DIR/.env" <<'EOF'
POSTGRES_HOST_PORT=5433
BACKEND_HOST_PORT=8001
FRONTEND_HOST_PORT=3001
EOF
fi
# shellcheck disable=SC1091
source "$ROOT_DIR/.env"

if [ ! -f "$ROOT_DIR/backend/.env" ]; then
  info "Creating backend/.env from .env.example - fill in your Kite credentials before using live features"
  cp "$ROOT_DIR/backend/.env.example" "$ROOT_DIR/backend/.env"
fi

info "Starting Postgres, Redis, RabbitMQ"
docker compose up -d postgres redis rabbitmq

info "Waiting for Postgres to be ready"
for _ in $(seq 1 30); do
  docker exec bn_postgres pg_isready -U bn_user -d banknifty >/dev/null 2>&1 && break
  sleep 1
done

info "Installing backend dependencies (uv sync, including dev tools)"
(cd "$ROOT_DIR/backend" && uv sync --extra dev)

info "Running database migrations"
(cd "$ROOT_DIR/backend" && uv run alembic upgrade head)

info "Installing frontend dependencies (npm install)"
(cd "$ROOT_DIR/frontend" && npm install)

if [ ! -f "$ROOT_DIR/frontend/.env.local" ]; then
  info "Writing frontend/.env.local"
  cat > "$ROOT_DIR/frontend/.env.local" <<EOF
NEXT_PUBLIC_API_URL=http://localhost:${BACKEND_HOST_PORT:-8001}/api/v1
EOF
fi

cat <<EOF

Setup complete.

Next steps:
  1. Fill in Kite credentials in backend/.env (KITE_API_KEY, KITE_API_SECRET)
     - see docs/USER_MANUAL.md "Connecting Kite" section.
  2. Backfill historical data:
       cd backend
       uv run backfill spot --years 2
       uv run backfill vix --years 2
       uv run backfill options --expiries 2 --strikes-around-atm 10
  3. Start the backend:
       cd backend && uv run uvicorn app.main:app --reload --port ${BACKEND_HOST_PORT:-8001}
  4. Start the frontend:
       cd frontend && npm run dev -- --port ${FRONTEND_HOST_PORT:-3001}
  5. Open http://localhost:${FRONTEND_HOST_PORT:-3001}

See docs/USER_MANUAL.md for what each page shows.
EOF
