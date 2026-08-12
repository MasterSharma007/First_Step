# Setup

## Requirements

| Tool | Version | Why |
|---|---|---|
| [Docker](https://docs.docker.com/get-docker/) | any recent | Postgres, Redis, RabbitMQ |
| [Node.js](https://nodejs.org/) | 20+ | Frontend (Next.js) |
| [uv](https://docs.astral.sh/uv/) | any recent | Backend (Python 3.12) - `scripts/setup.sh` installs it for you if missing |
| A [Kite Connect](https://kite.trade/connect/login) app | - | `KITE_API_KEY` / `KITE_API_SECRET` for live data, backfill, and paper trading |

You don't need Python or Node installed system-wide beyond Node itself - `uv` manages the Python 3.12 interpreter and virtualenv on its own.

## Quick start

```bash
./scripts/setup.sh
```

This is safe to re-run. It:

1. Checks for Docker/Node/npm, installs `uv` if missing.
2. Writes `.env` (root) and `backend/.env` from `.env.example` if they don't already exist.
3. Starts Postgres (`5433`), Redis (`6379`), RabbitMQ (`5672`) via `docker compose`.
4. Runs `uv sync` (backend deps) and `npm install` (frontend deps).
5. Runs `alembic upgrade head` (database migrations).
6. Writes `frontend/.env.local` pointing at the backend.

It does **not** start the backend/frontend dev servers themselves, or backfill any data - see below.

## After setup

### 1. Add your Kite credentials

Edit `backend/.env`:

```
KITE_API_KEY=...
KITE_API_SECRET=...
```

Get these from your app at [developers.kite.trade](https://developers.kite.trade/apps) — set the app's redirect URL to `http://localhost:8001/api/v1/kite/callback`.

`KITE_ACCESS_TOKEN` is *not* a long-lived secret - it's generated fresh every trading day. Start the backend, then:

1. `GET http://localhost:8001/api/v1/kite/login-url` → open the returned URL, log in on Kite.
2. You're redirected to the callback URL with a `request_token`; the callback exchanges it and returns an access token.
3. Paste that into `KITE_ACCESS_TOKEN` in `backend/.env` and restart the backend.

Repeat step 1-3 each trading day.

### 2. Backfill historical data

```bash
cd backend
uv run backfill spot --years 2
uv run backfill vix --years 2
uv run backfill options --expiries 2 --strikes-around-atm 10
```

`options`/`futures` backfill is limited to currently-listed contracts (Kite doesn't expose expired ones) - see `app/services/kite/instruments.py` for why. `spot`/`vix` have no such limit.

### 3. Start the app

```bash
# Terminal 1
cd backend && uv run uvicorn app.main:app --reload --port 8001

# Terminal 2
cd frontend && npm run dev -- --port 3001
```

Open `http://localhost:3001`. API docs at `http://localhost:8001/docs`.

### 4. (Optional) Enable live paper trading

Off by default. In `backend/.env`:

```
LIVE_LOOP_ENABLED=true
```

Restart the backend. It'll poll Kite every 30s, and open/close paper positions automatically when the Signal Engine has a strong-enough read. See `docs/USER_MANUAL.md` → **Live**.

## Ports

Default host ports (overridable via root `.env`, written by `scripts/setup.sh`):

| Service | Port | Env var |
|---|---|---|
| Postgres | 5433 | `POSTGRES_HOST_PORT` |
| Backend | 8001 | `BACKEND_HOST_PORT` |
| Frontend | 3001 | `FRONTEND_HOST_PORT` |
| Redis | 6379 | - |
| RabbitMQ | 5672 (mgmt UI 15672) | - |

Non-default ports (5433/8001/3001 instead of 5432/8000/3000) avoid clashing with other projects that might already be using the standard ones on your machine. Change them in the root `.env` if you'd rather use the defaults.

## Troubleshooting

- **`docker: command not found`** - install Docker first, the script can't do that for you.
- **Postgres won't come up healthy** - `docker compose logs postgres`; check nothing else already owns port 5433 (`ss -ltnp | grep 5433`).
- **Backend 422s on `/live/status` or `/market-data/trend`** - not enough `spot_ohlc` history yet (needs ≥50 bars). Run the spot backfill.
- **Backtest 422s "No option_ohlc history"** - run the options backfill for a date range that overlaps currently-listed contracts.
- **Kite calls failing with auth errors** - your daily access token expired; redo the login flow (step 1 above).
