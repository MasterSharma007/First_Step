"""Rolls up ticks accumulated in `market_ticks` into the *current,
in-progress* bar for `spot_ohlc`/`india_vix`, run on a short interval (see
`app/workers/scheduler.py`) so the trend/EMA/VWAP window genuinely reflects
right-now instead of only advancing whenever someone happens to run the
historical backfill.

Distinct from `aggregation.py::aggregate_last_minute`, which finalizes the
*previous complete* minute - this instead continuously re-upserts the bar
still forming, so a 5m candle's high/low/close keep updating as new ticks
arrive within it, and the next bar starts automatically once the clock
crosses the boundary.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market_tick import MarketTick
from app.services.kite.ingest import upsert_india_vix, upsert_spot_ohlc

INTERVAL_SECONDS = {"1m": 60, "5m": 300, "15m": 900}


def _bucket_start(as_of: datetime, interval: str) -> datetime:
    seconds = INTERVAL_SECONDS[interval]
    epoch_seconds = int(as_of.timestamp())
    floored = epoch_seconds - (epoch_seconds % seconds)
    return datetime.fromtimestamp(floored, tz=UTC)


async def _ticks_in_bucket(db: AsyncSession, symbol: str, bucket_start: datetime, as_of: datetime) -> list[MarketTick]:
    stmt = (
        select(MarketTick)
        .where(MarketTick.symbol == symbol, MarketTick.timestamp >= bucket_start, MarketTick.timestamp <= as_of)
        .order_by(MarketTick.timestamp.asc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def aggregate_current_spot_bar(
    db: AsyncSession, symbol: str, interval: str = "5m", as_of: datetime | None = None
) -> int:
    """Upserts the still-forming bar for `interval` from ticks seen so far
    this bucket. Returns the number of ticks it was built from (0 = no new
    data, caller can skip)."""
    as_of = as_of or datetime.now(UTC)
    bucket_start = _bucket_start(as_of, interval)
    ticks = await _ticks_in_bucket(db, symbol, bucket_start, as_of)
    if not ticks:
        return 0

    prices = [float(t.price) for t in ticks]
    candle = {
        "date": bucket_start,
        "open": prices[0],
        "high": max(prices),
        "low": min(prices),
        "close": prices[-1],
        "volume": sum(t.volume for t in ticks),
    }
    await upsert_spot_ohlc(db, symbol, interval, [candle])
    return len(ticks)


async def aggregate_current_vix_bar(db: AsyncSession, interval: str = "1m", as_of: datetime | None = None) -> int:
    as_of = as_of or datetime.now(UTC)
    bucket_start = _bucket_start(as_of, interval)
    ticks = await _ticks_in_bucket(db, "INDIA VIX", bucket_start, as_of)
    if not ticks:
        return 0

    candle = {"date": bucket_start, "close": float(ticks[-1].price)}
    await upsert_india_vix(db, interval, [candle])
    return len(ticks)


async def prune_old_ticks(db: AsyncSession, older_than: timedelta = timedelta(hours=6)) -> None:
    """`market_ticks` is tick-granularity and only needed to build the
    still-forming bar - keeps the table from growing unbounded across a
    long-running process. Safe to prune well before that, since anything
    older has long since been folded into a finalized spot_ohlc/india_vix row."""
    from sqlalchemy import delete

    cutoff = datetime.now(UTC) - older_than
    await db.execute(delete(MarketTick).where(MarketTick.timestamp < cutoff))
    await db.commit()
