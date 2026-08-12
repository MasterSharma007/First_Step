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


async def handle_ticks(ticks: list[dict], db: AsyncSession, token_to_symbol: dict[int, str]) -> None:
    """`token_to_symbol` maps subscribed instrument tokens to the
    human-readable symbol names used everywhere else (`"NIFTY BANK"`,
    `"INDIA VIX"`) - `market_ticks`/`spot_ohlc` are keyed by that name, not
    Kite's numeric token, so ticks for unmapped tokens are dropped."""
    redis = get_redis()
    persisted = 0

    for tick in ticks:
        symbol = token_to_symbol.get(tick["instrument_token"])
        if symbol is None:
            continue

        db.add(
            MarketTick(
                timestamp=tick.get("exchange_timestamp") or datetime.now(UTC),
                symbol=symbol,
                price=tick.get("last_price", 0),
                volume=tick.get("volume_traded", 0),
                bid=(tick.get("depth", {}).get("buy") or [{}])[0].get("price"),
                ask=(tick.get("depth", {}).get("sell") or [{}])[0].get("price"),
                oi=tick.get("oi"),
            )
        )
        persisted += 1
        try:
            await redis.publish(TICK_CHANNEL, orjson.dumps(tick).decode())
        except Exception as exc:  # noqa: BLE001 - Redis being unavailable shouldn't drop the tick itself
            logger.warning("tick_redis_publish_failed", error=str(exc))

    if persisted:
        await db.commit()
    logger.debug("ticks_persisted", count=persisted, received=len(ticks))
