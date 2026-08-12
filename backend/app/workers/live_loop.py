"""DB-backed live paper trading loop (SRD §2 Paper Trading Engine).

Runs on a schedule (`app/workers/scheduler.py`) rather than as an
in-memory engine, so open positions and P&L survive process restarts and
show up in the same `trade_execution`/`trade_signals` tables the rest of
the app already reads from (`GET /trades`, `/reports/daily`, `/signals`).

Off by default (`LIVE_LOOP_ENABLED=false`) - even paper-money automatic
execution should be an explicit opt-in, not something that starts firing
the moment the backend boots.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.logging import get_logger
from app.models.trade_execution import TradeExecution, TradeMode, TradeStatus
from app.models.trade_signal import SignalType, TradeSignal
from app.services.kite.client import KiteClient
from app.services.kite.instruments import InstrumentResolver
from app.services.kite.live_quote import fetch_ltp
from app.services.live.snapshot import STOP_LOSS_PCT, LiveSnapshot, compute_live_snapshot
from app.services.risk_management.manager import RiskLimits, RiskManager
from app.services.signal_engine.exit_rules import stop_loss_from_percentage, trail_stop_loss
from app.services.signal_engine.scorer import SignalEngine

TRAIL_STEP_PCT = 0.05  # matches BacktestEngine's default

logger = get_logger(__name__)


async def _open_positions(db: AsyncSession) -> list[TradeExecution]:
    stmt = select(TradeExecution).where(
        TradeExecution.mode == TradeMode.PAPER, TradeExecution.status == TradeStatus.OPEN
    )
    return list((await db.execute(stmt)).scalars().all())


async def _daily_realized_pnl(db: AsyncSession) -> float:
    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    stmt = select(TradeExecution).where(
        TradeExecution.mode == TradeMode.PAPER,
        TradeExecution.status == TradeStatus.CLOSED,
        TradeExecution.exit_time >= today_start,
    )
    rows = list((await db.execute(stmt)).scalars().all())
    return sum(float(r.pnl or 0) for r in rows)


async def _check_exits(db: AsyncSession, client: KiteClient, positions: list[TradeExecution]) -> None:
    """Trails the stop once a position is in profit, locking in gains if
    price pulls back before reaching target. The target still caps the
    trade - matches BacktestEngine's `_check_exit`, which explains why an
    uncapped version is unsafe (see its docstring); live polls far more
    often than the backtest's daily option snapshots so the argument is
    weaker here, but kept consistent until there's real evidence either way."""
    for position in positions:
        try:
            ltp = fetch_ltp(client, "NFO", position.symbol)
        except Exception as exc:  # noqa: BLE001 - one bad quote shouldn't stop the whole cycle
            logger.warning("live_exit_quote_failed", symbol=position.symbol, error=str(exc))
            continue

        entry_price = float(position.entry_price)
        original_stop_loss = stop_loss_from_percentage(entry_price, STOP_LOSS_PCT)
        current_stop_loss = float(position.stop_loss) if position.stop_loss is not None else original_stop_loss
        trail_step = entry_price * TRAIL_STEP_PCT
        new_stop_loss = trail_stop_loss(entry_price, ltp, current_stop_loss, trail_step)
        if new_stop_loss != current_stop_loss:
            position.stop_loss = new_stop_loss
        trailing_engaged = new_stop_loss > original_stop_loss

        exit_reason = None
        if ltp <= new_stop_loss:
            exit_reason = "TRAILING_STOP" if trailing_engaged else "STOP_LOSS"
        elif position.target is not None and ltp >= float(position.target):
            exit_reason = "TARGET"

        if exit_reason:
            position.status = TradeStatus.CLOSED
            position.exit_time = datetime.now(UTC)
            position.exit_price = ltp
            position.pnl = round((ltp - float(position.entry_price)) * position.quantity, 2)
            position.exit_reason = exit_reason
            logger.info("paper_position_closed", symbol=position.symbol, reason=exit_reason, pnl=position.pnl)

    await db.commit()


async def _maybe_open_position(
    db: AsyncSession,
    settings: Settings,
    resolver: InstrumentResolver,
    snapshot: LiveSnapshot,
    risk_manager: RiskManager,
    open_positions: list[TradeExecution],
) -> None:
    if (
        snapshot.decision is None
        or snapshot.decision.signal_type == "NO_TRADE"
        or snapshot.suggested_strike is None
        or snapshot.entry_price is None
        or snapshot.stop_loss is None
        or snapshot.target is None
        or snapshot.expiry is None
    ):
        return

    suggested_symbol_hint = f"{snapshot.suggested_strike:.0f}{snapshot.suggested_option_type}"
    if any(suggested_symbol_hint in p.symbol for p in open_positions):
        # Already holding this exact strike/side - the signal hasn't
        # changed since we opened it, so re-entering every cycle would
        # just stack duplicate positions on the same instrument.
        return

    daily_pnl = await _daily_realized_pnl(db)
    can_open = risk_manager.can_open_new_trade(daily_pnl, len(open_positions))
    if not can_open.allowed:
        logger.info("live_entry_blocked", reason=can_open.reason)
        return

    instrument = next(
        (
            i
            for i in resolver.options(settings.nfo_underlying, snapshot.expiry)
            if i.strike == snapshot.suggested_strike and i.instrument_type == snapshot.suggested_option_type
        ),
        None,
    )
    if instrument is None:
        logger.warning("live_entry_instrument_not_found", strike=snapshot.suggested_strike, expiry=str(snapshot.expiry))
        return

    risk_check = risk_manager.validate_trade_risk(snapshot.entry_price, snapshot.stop_loss, instrument.lot_size)
    if not risk_check.allowed:
        logger.info("live_entry_risk_rejected", reason=risk_check.reason)
        return

    lots = risk_manager.position_size(snapshot.entry_price, snapshot.stop_loss, instrument.lot_size)
    if lots <= 0:
        logger.info("live_entry_zero_size", entry_price=snapshot.entry_price, stop_loss=snapshot.stop_loss)
        return
    quantity = lots * instrument.lot_size

    signal = TradeSignal(
        signal_id=uuid.uuid4(),
        entry_time=snapshot.as_of,
        underlying=settings.trading_symbol,
        strike=snapshot.suggested_strike,
        expiry=snapshot.expiry,
        signal_type=SignalType.CE_ENTRY if snapshot.suggested_option_type == "CE" else SignalType.PE_ENTRY,
        entry_price=snapshot.entry_price,
        stop_loss=snapshot.stop_loss,
        target=snapshot.target,
        confidence_score=snapshot.decision.confidence_score,
        reasons=snapshot.decision.reasons,
    )
    db.add(signal)
    await db.flush()  # signal row must exist before trade_execution's FK to it does

    trade = TradeExecution(
        order_id=uuid.uuid4(),
        signal_id=signal.signal_id,
        mode=TradeMode.PAPER,
        status=TradeStatus.OPEN,
        symbol=instrument.tradingsymbol,
        option_type=snapshot.suggested_option_type,
        quantity=quantity,
        entry_time=snapshot.as_of,
        entry_price=snapshot.entry_price,
        stop_loss=snapshot.stop_loss,
        target=snapshot.target,
    )
    db.add(trade)
    await db.commit()
    logger.info(
        "paper_position_opened",
        symbol=instrument.tradingsymbol,
        quantity=quantity,
        entry_price=snapshot.entry_price,
        confidence=snapshot.decision.confidence_score,
    )


async def run_live_cycle(
    db: AsyncSession,
    client: KiteClient,
    resolver: InstrumentResolver,
    settings: Settings,
    signal_engine: SignalEngine,
) -> LiveSnapshot | None:
    """One iteration: check/close existing paper positions against live
    prices, then consider opening a new one if the Signal Engine currently
    says so and risk limits allow it. Returns the snapshot it computed
    (also useful for callers like `/live/status` that want the same read)."""
    snapshot = await compute_live_snapshot(db, client, resolver, settings, signal_engine)
    if snapshot is None:
        logger.warning("live_cycle_skipped_insufficient_history")
        return None

    open_positions = await _open_positions(db)
    await _check_exits(db, client, open_positions)

    remaining_open = await _open_positions(db)
    risk_manager = RiskManager(
        RiskLimits(
            max_daily_loss=settings.max_daily_loss,
            max_trade_loss=settings.max_trade_loss,
            max_open_positions=settings.max_open_positions,
            capital=settings.paper_trading_capital,
            risk_per_trade_pct=settings.risk_per_trade_pct,
        )
    )
    await _maybe_open_position(db, settings, resolver, snapshot, risk_manager, remaining_open)

    return snapshot
