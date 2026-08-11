from datetime import datetime

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.models.option_ohlc import OptionOHLC
from app.models.spot_ohlc import SpotOHLC
from app.schemas.market_data import SpotOHLCOut, TrendOut
from app.services.market_analysis import indicators as ind
from app.services.market_analysis.trend import detect_trend
from app.services.option_chain.analyzer import StrikeRow, writing_activity

router = APIRouter(prefix="/market-data", tags=["market-data"])


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

    spot_stmt = (
        select(SpotOHLC)
        .where(SpotOHLC.symbol == symbol, SpotOHLC.interval == interval)
        .order_by(SpotOHLC.datetime_.desc())
        .limit(lookback)
    )
    spot_rows = list((await db.execute(spot_stmt)).scalars().all())
    if len(spot_rows) < 50:
        raise HTTPException(
            status_code=422,
            detail="Not enough spot_ohlc history to compute a trend (need >= 50 bars) - run the historical backfill first.",
        )
    spot_rows.reverse()

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

    latest_ts_stmt = select(func.max(OptionOHLC.datetime_)).where(OptionOHLC.underlying == settings.nfo_underlying)
    latest_ts = (await db.execute(latest_ts_stmt)).scalar_one_or_none()

    ce_writing = pe_writing = False
    if latest_ts is not None:
        option_stmt = select(OptionOHLC).where(
            OptionOHLC.underlying == settings.nfo_underlying, OptionOHLC.datetime_ == latest_ts
        )
        option_rows = list((await db.execute(option_stmt)).scalars().all())
        by_strike: dict[float, dict[str, OptionOHLC]] = {}
        for r in option_rows:
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
        writing = writing_activity(chain, spot_price=float(spot_rows[-1].close))
        ce_writing, pe_writing = writing["ce_writing"], writing["pe_writing"]

    reading = detect_trend(df, ce_writing=ce_writing, pe_writing=pe_writing)
    support, resistance = ind.support_resistance(df, lookback=sr_lookback)
    return TrendOut(
        symbol=symbol,
        interval=interval,
        as_of=spot_rows[-1].datetime_,
        direction=reading.direction,
        reasons=reading.reasons,
        support=support,
        resistance=resistance,
        current_price=float(spot_rows[-1].close),
    )
