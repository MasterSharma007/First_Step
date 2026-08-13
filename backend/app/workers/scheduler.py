"""Background scheduler wiring: the tick stream + live-bar aggregation
(always on whenever Kite credentials are configured - passive data
collection, no trading risk) and the paper trading loop (gated behind
`LIVE_LOOP_ENABLED`, default off - see `app/workers/live_loop.py` for why).

Started from the FastAPI lifespan in `app/main.py`.
"""

from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import get_settings
from app.core.database import async_session_factory
from app.core.logging import get_logger
from app.services.kite.client import get_kite_client
from app.services.kite.instruments import get_instrument_resolver
from app.services.signal_engine.scorer import SignalEngine
from app.workers.live_aggregation import (
    aggregate_current_spot_bar,
    aggregate_current_vix_bar,
    prune_old_ticks,
)
from app.workers.live_loop import run_live_cycle
from app.workers.tick_stream import start_tick_stream, stop_tick_stream

logger = get_logger(__name__)

_scheduler: AsyncIOScheduler | None = None

AGGREGATION_INTERVAL_SECONDS = 5
TICK_PRUNE_INTERVAL_HOURS = 1


async def _aggregate_tick() -> None:
    settings = get_settings()
    async with async_session_factory() as db:
        try:
            await aggregate_current_spot_bar(db, settings.trading_symbol, "5m")
            await aggregate_current_spot_bar(db, settings.trading_symbol, "15m")
            await aggregate_current_vix_bar(db, "1m")
        except Exception:
            logger.exception("live_aggregation_failed")


async def _prune_ticks() -> None:
    async with async_session_factory() as db:
        try:
            await prune_old_ticks(db)
        except Exception:
            logger.exception("tick_prune_failed")


async def _tick() -> None:
    settings = get_settings()
    try:
        client = get_kite_client()
    except Exception as exc:  # noqa: BLE001 - a bad/missing Kite session shouldn't crash the scheduler thread
        logger.error("live_loop_tick_failed_no_kite_client", error=str(exc))
        return

    resolver = get_instrument_resolver(client)
    signal_engine = SignalEngine(
        ce_threshold=settings.ce_signal_score_threshold, pe_threshold=settings.pe_signal_score_threshold
    )

    async with async_session_factory() as db:
        try:
            await run_live_cycle(db, client, resolver, settings, signal_engine)
        except Exception:
            logger.exception("live_loop_tick_failed")


def start_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return

    settings = get_settings()
    _scheduler = AsyncIOScheduler()

    start_tick_stream()
    _scheduler.add_job(_aggregate_tick, "interval", seconds=AGGREGATION_INTERVAL_SECONDS, id="live_aggregation")
    _scheduler.add_job(_prune_ticks, "interval", hours=TICK_PRUNE_INTERVAL_HOURS, id="tick_prune")

    if settings.live_loop_enabled:
        _scheduler.add_job(_tick, "interval", seconds=settings.live_loop_interval_seconds, id="live_loop")
        logger.info("live_loop_started", interval_seconds=settings.live_loop_interval_seconds)
    else:
        logger.info("live_loop_disabled")

    _scheduler.start()
    logger.info("scheduler_started", aggregation_interval_seconds=AGGREGATION_INTERVAL_SECONDS)


def stop_scheduler() -> None:
    global _scheduler
    stop_tick_stream()
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
