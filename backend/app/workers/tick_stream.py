"""Owns the Kite tick websocket connection lifecycle (SRD §2 Live Market
Data Service - tick-by-tick spot/VIX). Started from the FastAPI lifespan
alongside the paper-trading scheduler.

Scoped to the two index instruments that actually need tick-level
freshness - the spot index (drives every EMA/VWAP/trend calculation) and
India VIX. Options stay on the existing 30s REST poll
(`app/services/kite/live_quote.py`), which already matches the SRD's
stated 30s option-chain refresh target - tracking option tick data would
mean resubscribing every time the ATM strike drifts, for a feed the
strategy doesn't actually need faster than 30s.
"""

from __future__ import annotations

import asyncio

from app.core.config import get_settings
from app.core.database import async_session_factory
from app.core.logging import get_logger
from app.services.kite.client import KiteClientError, get_kite_client
from app.services.kite.instruments import InstrumentResolver
from app.services.kite.live_feed import LiveFeedService
from app.workers.tick_ingestion import handle_ticks

logger = get_logger(__name__)

_feed: LiveFeedService | None = None


async def _on_ticks(ticks: list[dict], token_to_symbol: dict[int, str]) -> None:
    async with async_session_factory() as db:
        try:
            await handle_ticks(ticks, db, token_to_symbol)
        except Exception:
            logger.exception("tick_ingestion_failed")


def start_tick_stream() -> None:
    global _feed
    if _feed is not None:
        return

    settings = get_settings()
    try:
        client = get_kite_client()
    except KiteClientError as exc:
        logger.warning("tick_stream_not_started_no_kite_client", error=str(exc))
        return

    resolver = InstrumentResolver(client)
    try:
        spot = resolver.spot_index(settings.trading_symbol)
        vix = resolver.india_vix()
    except LookupError as exc:
        logger.warning("tick_stream_not_started_instrument_lookup_failed", error=str(exc))
        return

    token_to_symbol = {spot.instrument_token: settings.trading_symbol, vix.instrument_token: "INDIA VIX"}
    loop = asyncio.get_event_loop()

    async def on_ticks(ticks: list[dict]) -> None:
        await _on_ticks(ticks, token_to_symbol)

    feed = LiveFeedService(on_ticks=on_ticks, loop=loop)
    feed.subscribe(list(token_to_symbol.keys()))
    feed.start(threaded=True)
    _feed = feed
    logger.info("tick_stream_started", tokens=token_to_symbol)


def stop_tick_stream() -> None:
    global _feed
    if _feed is not None:
        _feed.stop()
        _feed = None
