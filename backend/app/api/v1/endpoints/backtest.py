from datetime import timedelta

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.backtest_result import BacktestResult
from app.models.spot_ohlc import SpotOHLC
from app.schemas.backtest import BacktestRequest, BacktestResultOut
from app.services.backtesting.engine import BacktestEngine

router = APIRouter(prefix="/backtest", tags=["backtest"])


@router.post("/run", response_model=BacktestResultOut)
async def run_backtest(request: BacktestRequest, db: AsyncSession = Depends(get_db)) -> BacktestResult:
    stmt = (
        select(SpotOHLC)
        .where(
            SpotOHLC.symbol == request.underlying,
            SpotOHLC.interval == "5m",
            SpotOHLC.datetime_ >= request.start_date,
            SpotOHLC.datetime_ <= request.end_date + timedelta(days=1),
        )
        .order_by(SpotOHLC.datetime_.asc())
    )
    result = await db.execute(stmt)
    rows = list(result.scalars().all())
    if len(rows) < 60:
        raise HTTPException(
            status_code=422,
            detail="Not enough spot_ohlc history for this range - run the historical backfill first.",
        )

    df = pd.DataFrame(
        [
            {
                "datetime": r.datetime_,
                "open": float(r.open),
                "high": float(r.high),
                "low": float(r.low),
                "close": float(r.close),
                "volume": r.volume,
            }
            for r in rows
        ]
    ).set_index("datetime")

    # NOTE: option-chain history lookup wiring (per-timestamp StrikeRow /
    # VIX maps) is left to the caller until `option_chain`/`india_vix`
    # backfill exists for the requested range - the engine itself is fully
    # functional given that data (see app/services/backtesting/engine.py).
    engine = BacktestEngine()
    run = engine.run(df, option_chain_by_time={}, india_vix_by_time={})

    backtest_result = BacktestResult(
        strategy_name=request.strategy_name,
        start_date=request.start_date,
        end_date=request.end_date,
        total_trades=run.metrics.total_trades,
        win_rate=run.metrics.win_rate,
        profit_factor=run.metrics.profit_factor if run.metrics.profit_factor != float("inf") else 0,
        max_drawdown=run.metrics.max_drawdown,
        sharpe_ratio=run.metrics.sharpe_ratio,
        net_pnl=run.metrics.net_pnl,
        params=request.params,
    )
    db.add(backtest_result)
    await db.commit()
    await db.refresh(backtest_result)
    return backtest_result


@router.get("/results", response_model=list[BacktestResultOut])
async def list_backtest_results(limit: int = 20, db: AsyncSession = Depends(get_db)) -> list[BacktestResult]:
    stmt = select(BacktestResult).order_by(BacktestResult.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())
