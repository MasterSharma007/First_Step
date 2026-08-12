from datetime import datetime

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.models.option_chain import OptionChainSnapshot
from app.models.spot_ohlc import SpotOHLC
from app.schemas.market_data import MultiTimeframeOut, SpotOHLCOut, TimeframeReadingOut, TrendOut
from app.services.market_analysis import indicators as ind
from app.services.market_analysis.multi_timeframe import analyze_timeframe, resample_ohlc
from app.services.market_analysis.trend import detect_trend
from app.services.option_chain.analyzer import StrikeRow, writing_activity

router = APIRouter(prefix="/market-data", tags=["market-data"])


async def _latest_writing_activity(db: AsyncSession, underlying: str, spot_price: float) -> tuple[bool, bool]:
    """CE/PE writing off the latest snapshot in `option_chain` - the table
    that's continuously kept fresh by the live tick/aggregation pipeline
    (`app/workers/live_aggregation.py`) and the live loop, not
    `option_ohlc` (backfill-only, frozen between manual runs)."""
    expiry_stmt = select(func.min(OptionChainSnapshot.expiry)).where(OptionChainSnapshot.underlying == underlying)
    expiry = (await db.execute(expiry_stmt)).scalar_one_or_none()
    if expiry is None:
        return False, False

    latest_ts_stmt = select(func.max(OptionChainSnapshot.datetime_)).where(
        OptionChainSnapshot.underlying == underlying, OptionChainSnapshot.expiry == expiry
    )
    latest_ts = (await db.execute(latest_ts_stmt)).scalar_one_or_none()
    if latest_ts is None:
        return False, False

    rows_stmt = select(OptionChainSnapshot).where(
        OptionChainSnapshot.underlying == underlying,
        OptionChainSnapshot.expiry == expiry,
        OptionChainSnapshot.datetime_ == latest_ts,
    )
    rows = list((await db.execute(rows_stmt)).scalars().all())
    by_strike: dict[float, dict[str, OptionChainSnapshot]] = {}
    for r in rows:
        by_strike.setdefault(float(r.strike), {})[r.option_type] = r
    chain = [
        StrikeRow(
            strike=strike,
            ce_oi=sides["CE"].oi if "CE" in sides else 0,
            ce_oi_change=sides["CE"].oi_change if "CE" in sides else 0,
            pe_oi=sides["PE"].oi if "PE" in sides else 0,
            pe_oi_change=sides["PE"].oi_change if "PE" in sides else 0,
        )
        for strike, sides in by_strike.items()
    ]
    writing = writing_activity(chain, spot_price=spot_price)
    return writing["ce_writing"], writing["pe_writing"]


async def _spot_df(db: AsyncSession, symbol: str, interval: str, limit: int) -> pd.DataFrame:
    stmt = (
        select(SpotOHLC)
        .where(SpotOHLC.symbol == symbol, SpotOHLC.interval == interval)
        .order_by(SpotOHLC.datetime_.desc())
        .limit(limit)
    )
    rows = list((await db.execute(stmt)).scalars().all())
    rows.reverse()
    return pd.DataFrame(
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


@router.get("/spot-ohlc", response_model=list[SpotOHLCOut])
async def get_spot_ohlc(
    interval: str = Query("5m", pattern="^(1m|5m|15m|1d)$"),
    symbol: str = "NIFTY BANK",
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = Query(500, le=5000),
    db: AsyncSession = Depends(get_db),
) -> list[SpotOHLC]:
    stmt = select(SpotOHLC).where(SpotOHLC.symbol == symbol, SpotOHLC.interval == interval)
    if start:
        stmt = stmt.where(SpotOHLC.datetime_ >= start)
    if end:
        stmt = stmt.where(SpotOHLC.datetime_ <= end)
    stmt = stmt.order_by(SpotOHLC.datetime_.desc()).limit(limit)

    result = await db.execute(stmt)
    rows = list(result.scalars().all())
    rows.reverse()
    return rows


@router.get("/trend", response_model=TrendOut)
async def get_trend(
    symbol: str = "NIFTY BANK",
    interval: str = Query("5m", pattern="^(1m|5m|15m|1d)$"),
    lookback: int = Query(100, ge=50, le=1000),
    sr_lookback: int = Query(20, ge=5, le=500, description="Bars to derive support/resistance from"),
    db: AsyncSession = Depends(get_db),
) -> TrendOut:
    """On-demand read of the Trend Detection Engine (SRD §2) against the
    latest spot candles plus the most recent option-chain writing activity
    available. Not a trade signal by itself - see `/signals` for that."""
    settings = get_settings()

    df = await _spot_df(db, symbol, interval, lookback)
    if len(df) < 50:
        raise HTTPException(
            status_code=422,
            detail="Not enough spot_ohlc history to compute a trend (need >= 50 bars) - run the historical backfill first.",
        )

    ce_writing, pe_writing = await _latest_writing_activity(db, settings.nfo_underlying, float(df["close"].iloc[-1]))

    reading = detect_trend(df, ce_writing=ce_writing, pe_writing=pe_writing)
    support, resistance = ind.support_resistance(df, lookback=sr_lookback)
    return TrendOut(
        symbol=symbol,
        interval=interval,
        as_of=df.index[-1],
        direction=reading.direction,
        reasons=reading.reasons,
        support=support,
        resistance=resistance,
        current_price=float(df["close"].iloc[-1]),
    )


@router.get("/multi-timeframe", response_model=MultiTimeframeOut)
async def get_multi_timeframe(symbol: str = "NIFTY BANK", db: AsyncSession = Depends(get_db)) -> MultiTimeframeOut:
    """Trend + support/resistance across 15m/1h/1d/1w/1M in one read. Only
    15m and 1d candles are ever fetched from Kite - 1h is resampled from
    15m, 1w/1M from 1d (see `multi_timeframe.py`). Weekly/monthly are
    honest about not having a full year+ of daily history yet: with fewer
    than 50 bars, `insufficient_data` is true and only support/resistance
    is returned, no guessed direction."""
    settings = get_settings()

    df_15m = await _spot_df(db, symbol, "15m", 2000)
    df_1d = await _spot_df(db, symbol, "1d", 2000)
    if df_15m.empty and df_1d.empty:
        raise HTTPException(
            status_code=422,
            detail="No spot_ohlc history at all - run `uv run backfill spot` first.",
        )

    current_price = float((df_15m if not df_15m.empty else df_1d)["close"].iloc[-1])
    ce_writing, pe_writing = await _latest_writing_activity(db, settings.nfo_underlying, current_price)

    df_1h = resample_ohlc(df_15m, "1h")
    df_1w = resample_ohlc(df_1d, "W")
    df_1m = resample_ohlc(df_1d, "ME")

    readings = [
        analyze_timeframe(df_15m, "15m", ce_writing, pe_writing),
        analyze_timeframe(df_1h, "1h", ce_writing, pe_writing),
        analyze_timeframe(df_1d, "1d", ce_writing, pe_writing),
        analyze_timeframe(df_1w, "1w", ce_writing, pe_writing),
        analyze_timeframe(df_1m, "1M", ce_writing, pe_writing),
    ]

    return MultiTimeframeOut(
        symbol=symbol,
        current_price=current_price,
        timeframes=[
            TimeframeReadingOut(
                timeframe=r.timeframe,
                bars_available=r.bars_available,
                insufficient_data=r.insufficient_data,
                support=r.support,
                resistance=r.resistance,
                direction=r.direction,
                reasons=r.reasons,
            )
            for r in readings
        ],
    )
