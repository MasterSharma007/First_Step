from fastapi import APIRouter

from app.api.v1.endpoints import (
    backtest,
    health,
    kite,
    live,
    logs,
    market_data,
    option_chain,
    reports,
    signals,
    trades,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(market_data.router)
api_router.include_router(option_chain.router)
api_router.include_router(signals.router)
api_router.include_router(trades.router)
api_router.include_router(backtest.router)
api_router.include_router(reports.router)
api_router.include_router(kite.router)
api_router.include_router(logs.router)
api_router.include_router(live.router)
