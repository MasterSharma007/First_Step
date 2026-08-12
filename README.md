# AI-Based Bank Nifty Intraday Trading Platform

Automated platform that analyzes Bank Nifty spot and options data in
real-time, identifies high-probability CE/PE opportunities, backtests
strategies, paper-trades, and executes live trades via Kite Connect.

- Full requirements: [`docs/SRD.md`](docs/SRD.md)
- Setup guide: [`docs/SETUP.md`](docs/SETUP.md)
- User manual (what each page shows): [`docs/USER_MANUAL.md`](docs/USER_MANUAL.md)

## Structure

```
.
├── backend/     FastAPI service: data ingestion, analysis engines,
│                signal generation, risk management, backtesting, trading
├── frontend/    Next.js dashboard: market view, option chain, signals,
│                backtest results, reports
├── docs/        SRD, setup guide, user manual
├── scripts/     setup.sh - one-shot dev environment setup
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
├── workers/         background tick ingestion / aggregation tasks
└── cli/             `backfill` - historical data backfill CLI
```

## Getting started

```bash
./scripts/setup.sh
```

Checks prerequisites, installs backend/frontend deps, starts Postgres/Redis/RabbitMQ, and runs migrations. Then follow the printed next steps (Kite credentials, historical backfill, starting the dev servers). Full walkthrough: [`docs/SETUP.md`](docs/SETUP.md).

Once running: dashboard at `http://localhost:3001`, API docs at `http://localhost:8001/docs`. See [`docs/USER_MANUAL.md`](docs/USER_MANUAL.md) for what each page shows - support/resistance, live signals, trades, logs, etc.

## Status

Working end-to-end against real Kite data: database schema + migrations,
historical backfill, live price/signal/trend/support-resistance, a
DB-backed live paper trading loop, backtesting, and a Next.js dashboard
(Dashboard, Live, Option Chain, Signals, Trades, Backtest, Reports, Logs).
The rule-based Signal Engine is functional but untuned - see `docs/SRD.md`
§11 for the ML scoring model and other phased roadmap items, and
`docs/USER_MANUAL.md` for a walkthrough of what's live today.
