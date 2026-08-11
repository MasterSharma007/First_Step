"""Live Market Data Service (SRD §2, §4): Kite ticker websocket wrapper.

Streams tick-by-tick LTP/OI for subscribed instrument tokens and hands each
tick to an async callback, which is expected to persist it (see
`app/workers/tick_ingestion.py`) and/or push it onto Redis pub/sub for the
1s and 1m aggregation stages.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from kiteconnect import KiteTicker

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

TickHandler = Callable[[list[dict]], Awaitable[None]]


class LiveFeedService:
    def __init__(self, on_ticks: TickHandler, loop: asyncio.AbstractEventLoop | None = None):
        settings = get_settings()
        if not settings.kite_api_key or not settings.kite_access_token:
            raise RuntimeError("KITE_API_KEY / KITE_ACCESS_TOKEN required for live feed")

        self.ticker = KiteTicker(settings.kite_api_key, settings.kite_access_token)
        self.on_ticks = on_ticks
        self.loop = loop or asyncio.get_event_loop()

        self.ticker.on_ticks = self._handle_ticks
        self.ticker.on_connect = self._handle_connect
        self.ticker.on_close = self._handle_close
        self._tokens: list[int] = []

    def subscribe(self, instrument_tokens: list[int]) -> None:
        self._tokens = instrument_tokens

    def _handle_connect(self, ws, response) -> None:
        logger.info("kite_ws_connected")
        if self._tokens:
            ws.subscribe(self._tokens)
            ws.set_mode(ws.MODE_FULL, self._tokens)

    def _handle_close(self, ws, code, reason) -> None:
        logger.warning("kite_ws_closed", code=code, reason=reason)

    def _handle_ticks(self, ws, ticks: list[dict]) -> None:
        asyncio.run_coroutine_threadsafe(self.on_ticks(ticks), self.loop)

    def start(self, threaded: bool = True) -> None:
        self.ticker.connect(threaded=threaded)

    def stop(self) -> None:
        self.ticker.close()
