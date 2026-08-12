"""Background scheduler wiring for the live paper trading loop.

Started from the FastAPI lifespan in `app/main.py`, gated behind
`LIVE_LOOP_ENABLED` (default off - see `app/workers/live_loop.py` for why).
"""

from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import get_settings
from app.core.database import async_session_factory
from app.core.logging import get_logger
from app.services.kite.client import get_kite_client
from app.services.kite.instruments import InstrumentResolver
from app.services.signal_engine.scorer import SignalEngine
from app.workers.live_loop import run_live_cycle

logger = get_logger(__name__)

_scheduler: AsyncIOScheduler | None = None


async def _tick() -> None:
    settings = get_settings()
    try:
        client = get_kite_client()
    except Exception as exc:  # noqa: BLE001 - a bad/missing Kite session shouldn't crash the scheduler thread
        logger.error("live_loop_tick_failed_no_kite_client", error=str(exc))
        return

    resolver = InstrumentResolver(client)
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
    settings = get_settings()
    if not settings.live_loop_enabled:
        logger.info("live_loop_disabled")
        return
    if _scheduler is not None:
        return

    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(_tick, "interval", seconds=settings.live_loop_interval_seconds, id="live_loop")
    _scheduler.start()
    logger.info("live_loop_started", interval_seconds=settings.live_loop_interval_seconds)


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
