"""Rolls raw ticks up into 1-minute OHLCV bars (SRD §2, §4). Intended to run
on a scheduler (e.g. APScheduler cron every minute) reading the last
minute's `market_ticks` rows and upserting into `spot_ohlc`.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market_tick import MarketTick
from app.models.spot_ohlc import SpotOHLC


async def aggregate_last_minute(db: AsyncSession, symbol: str, as_of: datetime | None = None) -> SpotOHLC | None:
    as_of = as_of or datetime.now(UTC)
    minute_start = as_of.replace(second=0, microsecond=0) - timedelta(minutes=1)
    minute_end = minute_start + timedelta(minutes=1)

    stmt = select(MarketTick).where(
        MarketTick.symbol == symbol,
        MarketTick.timestamp >= minute_start,
        MarketTick.timestamp < minute_end,
    ).order_by(MarketTick.timestamp.asc())
    result = await db.execute(stmt)
    ticks = list(result.scalars().all())
    if not ticks:
        return None

    prices = [float(t.price) for t in ticks]
    bar = {
        "symbol": symbol,
        "interval": "1m",
        "datetime": minute_start,
        "open": prices[0],
        "high": max(prices),
        "low": min(prices),
        "close": prices[-1],
        "volume": sum(t.volume for t in ticks),
    }

    stmt = insert(SpotOHLC).values(**bar)
    stmt = stmt.on_conflict_do_update(
        index_elements=["symbol", "interval", "datetime"],
        set_={k: v for k, v in bar.items() if k not in ("symbol", "interval", "datetime")},
    )
    await db.execute(stmt)
    await db.commit()

    result = await db.execute(
        select(SpotOHLC).where(
            SpotOHLC.symbol == symbol, SpotOHLC.interval == "1m", SpotOHLC.datetime_ == minute_start
        )
    )
    return result.scalar_one()
