"""Live cockpit read (SRD §2): current price, trend, support/resistance,
what the Signal Engine says right now, and any open paper positions with
live unrealized P&L. Read-only - the actual position management happens
in the background loop (`app/workers/live_loop.py`), not here, so calling
this endpoint never itself opens/closes a trade."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.logging import get_logger
from app.models.trade_execution import TradeExecution, TradeMode, TradeStatus
from app.schemas.live import LiveStatusOut, OpenPositionOut, SignalSuggestion
from app.services.kite.client import KiteClientError, get_kite_client
from app.services.kite.instruments import InstrumentResolver
from app.services.kite.live_quote import fetch_ltp
from app.services.live.snapshot import compute_live_snapshot
from app.services.signal_engine.scorer import SignalEngine

logger = get_logger(__name__)

router = APIRouter(prefix="/live", tags=["live"])


@router.get("/status", response_model=LiveStatusOut)
async def get_live_status(db: AsyncSession = Depends(get_db)) -> LiveStatusOut:
    settings = get_settings()
    try:
        client = get_kite_client()
    except KiteClientError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    resolver = InstrumentResolver(client)
    signal_engine = SignalEngine(
        ce_threshold=settings.ce_signal_score_threshold, pe_threshold=settings.pe_signal_score_threshold
    )

    snapshot = await compute_live_snapshot(db, client, resolver, settings, signal_engine)
    if snapshot is None:
        raise HTTPException(
            status_code=422,
            detail="Not enough spot_ohlc history yet - run `uv run backfill spot` first.",
        )

    open_stmt = select(TradeExecution).where(
        TradeExecution.mode == TradeMode.PAPER, TradeExecution.status == TradeStatus.OPEN
    )
    open_rows = list((await db.execute(open_stmt)).scalars().all())

    open_positions: list[OpenPositionOut] = []
    for row in open_rows:
        current_price = None
        unrealized_pnl = None
        try:
            current_price = fetch_ltp(client, "NFO", row.symbol)
            unrealized_pnl = round((current_price - float(row.entry_price)) * row.quantity, 2)
        except Exception as exc:  # noqa: BLE001 - a stale/bad quote shouldn't break the whole status response
            logger.warning("live_position_quote_failed", symbol=row.symbol, error=str(exc))
        open_positions.append(
            OpenPositionOut(
                order_id=str(row.order_id),
                symbol=row.symbol,
                option_type=row.option_type,
                quantity=row.quantity,
                entry_price=float(row.entry_price),
                current_price=current_price,
                stop_loss=float(row.stop_loss) if row.stop_loss is not None else None,
                target=float(row.target) if row.target is not None else None,
                unrealized_pnl=unrealized_pnl,
                entry_time=row.entry_time,
            )
        )

    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    closed_today_stmt = select(TradeExecution).where(
        TradeExecution.mode == TradeMode.PAPER,
        TradeExecution.status == TradeStatus.CLOSED,
        TradeExecution.exit_time >= today_start,
    )
    closed_today = list((await db.execute(closed_today_stmt)).scalars().all())
    today_realized_pnl = round(sum(float(r.pnl or 0) for r in closed_today), 2)

    decision = snapshot.decision
    signal = SignalSuggestion(
        signal_type=decision.signal_type if decision else "NO_TRADE",
        verdict=decision.verdict if decision else "NO_TRADE",
        confidence_score=decision.confidence_score if decision else 50.0,
        strike=snapshot.suggested_strike,
        option_type=snapshot.suggested_option_type,
        entry_price=snapshot.entry_price,
        stop_loss=snapshot.stop_loss,
        target=snapshot.target,
        reasons=decision.reasons if decision else {},
    )

    return LiveStatusOut(
        as_of=snapshot.as_of,
        spot_price=snapshot.spot_price,
        trend_direction=snapshot.trend.direction,
        trend_reasons=snapshot.trend.reasons,
        support=snapshot.support,
        resistance=snapshot.resistance,
        expiry=snapshot.expiry,
        atm_strike=snapshot.atm_strike,
        pcr=snapshot.pcr,
        max_pain=snapshot.max_pain,
        oi_signal=snapshot.oi_signal,
        india_vix=snapshot.india_vix,
        signal=signal,
        open_positions=open_positions,
        today_realized_pnl=today_realized_pnl,
        today_trade_count=len(closed_today) + len(open_positions),
        live_loop_enabled=settings.live_loop_enabled,
    )
