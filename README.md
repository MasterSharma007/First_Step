# AI-Based Bank Nifty Intraday Trading Platform

Automated platform that analyzes Bank Nifty spot and options data in
real-time, identifies high-probability CE/PE opportunities, backtests
strategies, paper-trades, and executes live trades via Kite Connect.

Full requirements: [`docs/SRD.md`](docs/SRD.md).

## Structure

```
.
├── backend/     FastAPI service: data ingestion, analysis engines,
│                signal generation, risk management, backtesting, trading
├── frontend/    Next.js dashboard: market view, option chain, signals,
│                backtest results, reports
├── docs/        SRD and supporting docs
└── docker-compose.yml   Postgres, Redis, RabbitMQ, backend, frontend
```

## Backend layout (`backend/app`)

```
app/
├── core/            settings, db session, redis client, logging
├── models/          SQLAlchemy ORM models (market data, signals, trades)
├── schemas/         Pydantic request/response schemas
├── api/v1/          FastAPI routers
├── services/
│   ├── kite/            Kite Connect client, historical + live feed, orders
│   ├── market_analysis/ VWAP, EMA, ATR, support/resistance, breakout
│   ├── option_chain/    PCR, Max Pain, OI buildup classification
│   ├── signal_engine/   entry/exit rules, confidence scoring
│   ├── risk_management/ position sizing, loss limits
│   ├── backtesting/     historical strategy runner + metrics
│   └── trading/         paper + live trading engines
├── ml/              feature extraction + scoring model interface
└── workers/         background tick ingestion / aggregation tasks
```

## Getting started

### 1. Infra

```bash
cp backend/.env.example backend/.env   # fill in Kite + DB credentials
docker compose up -d postgres redis rabbitmq
```

### 2. Backend

```bash
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

API docs at `http://localhost:8000/docs`.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Dashboard at `http://localhost:3000`.

## Status

Initial scaffold: database schema + migrations, FastAPI service structure,
Kite integration interfaces, option chain / market analysis / signal /
backtesting engines with working logic against historical data, and a
Next.js dashboard shell. Live order execution and the ML scoring model are
wired to real interfaces but require your Kite credentials and trained
model artifacts respectively before going live — see `docs/SRD.md` §11 for
the phased roadmap.
