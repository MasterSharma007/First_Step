from datetime import timedelta

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.models.backtest_result import BacktestResult
from app.models.india_vix import IndiaVix
from app.models.option_ohlc import OptionOHLC
from app.models.spot_ohlc import SpotOHLC
from app.schemas.backtest import BacktestRequest, BacktestResultOut
from app.services.backtesting.data_prep import (
    build_option_chain_by_time,
    build_option_series,
    build_vix_by_time,
)
from app.services.backtesting.engine import BacktestEngine

router = APIRouter(prefix="/backtest", tags=["backtest"])


@router.post("/run", response_model=BacktestResultOut)
async def run_backtest(request: BacktestRequest, db: AsyncSession = Depends(get_db)) -> BacktestResult:
    settings = get_settings()
    range_end = request.end_date + timedelta(days=1)

    spot_stmt = (
        select(SpotOHLC)
        .where(
            SpotOHLC.symbol == request.underlying,
            SpotOHLC.interval == "5m",
            SpotOHLC.datetime_ >= request.start_date,
            SpotOHLC.datetime_ <= range_end,
        )
        .order_by(SpotOHLC.datetime_.asc())
    )
    spot_rows = list((await db.execute(spot_stmt)).scalars().all())
    if len(spot_rows) < 60:
        raise HTTPException(
            status_code=422,
            detail="Not enough spot_ohlc history for this range - run `uv run backfill spot` first.",
        )

    # option_ohlc/futures are stored under the NFO underlying name (e.g.
    # "BANKNIFTY"), which differs from the spot symbol in `request.underlying`
    # (e.g. "NIFTY BANK") - see app/core/config.py:nfo_underlying.
    #
    # Multiple expiries' contracts share the same strike/type/date once more
    # than one is listed (e.g. Aug and Sep). Grouping option rows without
    # pinning to one expiry silently mixes them - a thin, barely-traded far
    # expiry's stale flat last-price can overwrite the real near-expiry
    # premium on some dates and not others, corrupting entry/exit prices.
    # So: pick the nearest expiry with any data in range and trade only that
    # one throughout - the same "nearest expiry" contract the live signal
    # engine and Trend endpoint already use.
    expiry_stmt = select(func.min(OptionOHLC.expiry)).where(
        OptionOHLC.underlying == settings.nfo_underlying,
        OptionOHLC.datetime_ >= request.start_date,
        OptionOHLC.datetime_ <= range_end,
    )
    chosen_expiry = (await db.execute(expiry_stmt)).scalar_one_or_none()
    if chosen_expiry is None:
        raise HTTPException(
            status_code=422,
            detail=(
                "No option_ohlc history for this date range - the Signal Engine needs option-chain "
                "data (PCR/OI writing) to generate any signal. Run `uv run backfill options` for a "
                "range Kite still has listed contracts for (see app/services/kite/instruments.py for "
                "why historical options are limited to currently-listed contracts)."
            ),
        )

    # Matches the spot interval below ("5m") - mixing this with daily
    # candles would forward-fill a stale once-a-day premium across an
    # entire trading session, making positions only checkable/closeable
    # once per day instead of intraday (see app/services/backtesting/
    # engine.py for why that's actively harmful, not just imprecise).
    option_interval = "5m"
    option_stmt = select(OptionOHLC).where(
        OptionOHLC.underlying == settings.nfo_underlying,
        OptionOHLC.expiry == chosen_expiry,
        OptionOHLC.interval == option_interval,
        OptionOHLC.datetime_ >= request.start_date,
        OptionOHLC.datetime_ <= range_end,
    )
    option_rows = list((await db.execute(option_stmt)).scalars().all())
    if not option_rows:
        raise HTTPException(
            status_code=422,
            detail=(
                f"No {option_interval} option_ohlc history for this range - run "
                f"`uv run backfill options --interval {option_interval}` for it first."
            ),
        )

    # A wider lookback purely for ATR history, so trades near the start of
    # the requested range still have enough prior candles for a real ATR
    # instead of always falling back to the flat percentage stop.
    atr_lookback_start = request.start_date - timedelta(days=30)
    atr_stmt = select(OptionOHLC).where(
        OptionOHLC.underlying == settings.nfo_underlying,
        OptionOHLC.expiry == chosen_expiry,
        OptionOHLC.interval == option_interval,
        OptionOHLC.datetime_ >= atr_lookback_start,
        OptionOHLC.datetime_ <= range_end,
    )
    atr_rows = list((await db.execute(atr_stmt)).scalars().all())
    option_series = build_option_series(atr_rows)

    vix_stmt = select(IndiaVix).where(IndiaVix.datetime_ >= request.start_date, IndiaVix.datetime_ <= range_end)
    vix_rows = list((await db.execute(vix_stmt)).scalars().all())

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
            for r in spot_rows
        ]
    ).set_index("datetime")

    option_chain_by_time = build_option_chain_by_time(option_rows, df.index)
    india_vix_by_time = build_vix_by_time(vix_rows, df.index)

    engine = BacktestEngine()
    run = engine.run(df, option_chain_by_time, india_vix_by_time, option_series)

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
        params={
            **request.params,
            "expiry_traded": chosen_expiry.isoformat(),
            "option_chain_coverage_bars": len(option_chain_by_time),
            "spot_bars": len(df),
        },
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
