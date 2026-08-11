"""Persists incoming Kite ticks and republishes them on Redis pub/sub for
1s/1m aggregation consumers (SRD §2 Live Market Data Service update
frequencies: tick-by-tick, 1s, 1m)."""

from __future__ import annotations

from datetime import UTC, datetime

import orjson
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.redis import get_redis
from app.models.market_tick import MarketTick

logger = get_logger(__name__)

TICK_CHANNEL = "market:ticks"


async def handle_ticks(ticks: list[dict], db: AsyncSession) -> None:
    redis = get_redis()

    for tick in ticks:
        db.add(
            MarketTick(
                timestamp=tick.get("exchange_timestamp") or datetime.now(UTC),
                symbol=str(tick["instrument_token"]),
                price=tick.get("last_price", 0),
                volume=tick.get("volume_traded", 0),
                bid=(tick.get("depth", {}).get("buy") or [{}])[0].get("price"),
                ask=(tick.get("depth", {}).get("sell") or [{}])[0].get("price"),
                oi=tick.get("oi"),
            )
        )
        await redis.publish(TICK_CHANNEL, orjson.dumps(tick).decode())

    await db.commit()
    logger.debug("ticks_persisted", count=len(ticks))
