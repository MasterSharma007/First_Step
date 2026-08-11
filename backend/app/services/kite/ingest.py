"""Upserts raw Kite historical candles into the platform's DB tables.

Kite candle dicts look like:
    {"date": datetime, "open": .., "high": .., "low": .., "close": ..,
     "volume": .., "oi": ..}  (oi only present for F&O instruments)

`futures_data`/`india_vix` store one value per timestamp (ltp/value) rather
than a full OHLC candle, so those upserts collapse each candle to its
close - a documented simplification, not a bug: the intraday shape is still
fully preserved in `spot_ohlc`/`option_ohlc` where it matters most for the
Signal Engine.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.futures_data import FuturesTick
from app.models.india_vix import IndiaVix
from app.models.option_ohlc import OptionOHLC
from app.models.spot_ohlc import SpotOHLC


async def upsert_spot_ohlc(db: AsyncSession, symbol: str, interval: str, candles: list[dict]) -> int:
    if not candles:
        return 0
    rows = [
        {
            "symbol": symbol,
            "interval": interval,
            "datetime": c["date"],
            "open": c["open"],
            "high": c["high"],
            "low": c["low"],
            "close": c["close"],
            "volume": c["volume"],
        }
        for c in candles
    ]
    stmt = insert(SpotOHLC).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["symbol", "interval", "datetime"],
        set_={k: stmt.excluded[k] for k in ("open", "high", "low", "close", "volume")},
    )
    await db.execute(stmt)
    await db.commit()
    return len(rows)


async def upsert_option_ohlc(
    db: AsyncSession,
    underlying: str,
    strike: float,
    expiry: date,
    option_type: str,
    interval: str,
    candles: list[dict],
) -> int:
    if not candles:
        return 0
    rows = []
    prev_oi = None
    for c in sorted(candles, key=lambda c: c["date"]):
        oi = c.get("oi", 0) or 0
        rows.append(
            {
                "underlying": underlying,
                "strike": strike,
                "expiry": expiry,
                "option_type": option_type,
                "interval": interval,
                "datetime": c["date"],
                "open": c["open"],
                "high": c["high"],
                "low": c["low"],
                "close": c["close"],
                "volume": c["volume"],
                "oi": oi,
                "oi_change": 0 if prev_oi is None else oi - prev_oi,
                "iv": None,  # Kite's historical API doesn't provide IV history
            }
        )
        prev_oi = oi

    stmt = insert(OptionOHLC).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["underlying", "strike", "expiry", "option_type", "interval", "datetime"],
        set_={
            k: stmt.excluded[k]
            for k in ("open", "high", "low", "close", "volume", "oi", "oi_change")
        },
    )
    await db.execute(stmt)
    await db.commit()
    return len(rows)


async def upsert_futures(db: AsyncSession, underlying: str, expiry: date, candles: list[dict]) -> int:
    if not candles:
        return 0
    rows = []
    prev_oi = None
    for c in sorted(candles, key=lambda c: c["date"]):
        oi = c.get("oi", 0) or 0
        rows.append(
            {
                "underlying": underlying,
                "expiry": expiry,
                "datetime": c["date"],
                "ltp": c["close"],
                "oi": oi,
                "oi_change": 0 if prev_oi is None else oi - prev_oi,
                "volume": c["volume"],
            }
        )
        prev_oi = oi

    stmt = insert(FuturesTick).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["underlying", "expiry", "datetime"],
        set_={k: stmt.excluded[k] for k in ("ltp", "oi", "oi_change", "volume")},
    )
    await db.execute(stmt)
    await db.commit()
    return len(rows)


async def upsert_india_vix(db: AsyncSession, interval: str, candles: list[dict]) -> int:
    if not candles:
        return 0
    rows = [{"interval": interval, "datetime": c["date"], "value": c["close"]} for c in candles]
    stmt = insert(IndiaVix).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["interval", "datetime"],
        set_={"value": stmt.excluded.value},
    )
    await db.execute(stmt)
    await db.commit()
    return len(rows)
