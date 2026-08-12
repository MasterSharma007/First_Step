"""DB-backed live trading loop (SRD §2 Paper/Live Trading Engine).

Runs on a schedule (`app/workers/scheduler.py`) rather than as an
in-memory engine, so open positions and P&L survive process restarts and
show up in the same `trade_execution`/`trade_signals` tables the rest of
the app already reads from (`GET /trades`, `/reports/daily`, `/signals`).

Off by default (`LIVE_LOOP_ENABLED=false`) - even paper-money automatic
execution should be an explicit opt-in, not something that starts firing
the moment the backend boots.

`settings.paper_trading` (`PAPER_TRADING` env var) switches every entry
and exit between simulated bookkeeping and real Kite orders
(`KiteOrderService`) - flip it and restart the backend to switch modes.
Positions are scoped by `TradeMode` throughout (`_open_positions`,
`_daily_realized_pnl`, `/live/status`, `/reports/daily`), so switching
modes never mixes paper and real positions/P&L in the same read, and any
position left open in the mode you switched away from just sits there
untouched (not silently exited) until you switch back to it."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.logging import get_logger
from app.models.trade_execution import TradeExecution, TradeMode, TradeStatus
from app.models.trade_signal import SignalType, TradeSignal
from app.services.kite.client import KiteClient
from app.services.kite.instruments import InstrumentResolver
from app.services.kite.live_quote import fetch_ltp
from app.services.kite.orders import KiteOrderService
from app.services.live.snapshot import STOP_LOSS_PCT, LiveSnapshot, compute_live_snapshot
from app.services.risk_management.manager import RiskLimits, RiskManager
from app.services.signal_engine.exit_rules import stop_loss_from_percentage, trail_stop_loss
from app.services.signal_engine.scorer import SignalEngine

TRAIL_STEP_PCT = 0.05  # matches BacktestEngine's default
IST = ZoneInfo("Asia/Kolkata")

logger = get_logger(__name__)


def _is_past_square_off(as_of: datetime, square_off_time: str) -> bool:
    """`square_off_time` is "HH:MM" in IST (e.g. "15:38") - NSE trading
    hours are always quoted in IST regardless of what timezone the server
    runs in, so `as_of` (UTC) is converted before comparing."""
    hour, minute = (int(part) for part in square_off_time.split(":"))
    return as_of.astimezone(IST).time() >= time(hour, minute)


def _fetch_fill_price(client: KiteClient, broker_order_id: str, fallback: float) -> float:
    """Best-effort real fill price for a just-placed order. Falls back to
    the pre-order LTP if Kite hasn't reported a completed fill yet (market
    orders are usually near-instant but not guaranteed) - approximate
    P&L beats no P&L, and the position is still real either way."""
    try:
        history = client.kite.order_history(broker_order_id)
        completed = [h for h in history if h.get("status") == "COMPLETE" and h.get("average_price")]
        if completed:
            return float(completed[-1]["average_price"])
    except Exception as exc:  # noqa: BLE001 - a lookup failure shouldn't block recording the trade
        logger.warning("live_order_fill_price_lookup_failed", broker_order_id=broker_order_id, error=str(exc))
    return fallback


async def _open_positions(db: AsyncSession, mode: TradeMode) -> list[TradeExecution]:
    stmt = select(TradeExecution).where(TradeExecution.mode == mode, TradeExecution.status == TradeStatus.OPEN)
    return list((await db.execute(stmt)).scalars().all())


async def _daily_realized_pnl(db: AsyncSession, mode: TradeMode) -> float:
    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    stmt = select(TradeExecution).where(
        TradeExecution.mode == mode,
        TradeExecution.status == TradeStatus.CLOSED,
        TradeExecution.exit_time >= today_start,
    )
    rows = list((await db.execute(stmt)).scalars().all())
    return sum(float(r.pnl or 0) for r in rows)


def _close_position(position: TradeExecution, exit_price: float, reason: str) -> None:
    position.status = TradeStatus.CLOSED
    position.exit_time = datetime.now(UTC)
    position.exit_price = exit_price
    position.pnl = round((exit_price - float(position.entry_price)) * position.quantity, 2)
    position.exit_reason = reason
    event = "live_position_closed" if position.mode == TradeMode.LIVE else "paper_position_closed"
    logger.info(event, symbol=position.symbol, reason=reason, pnl=position.pnl)


async def _check_exits(
    db: AsyncSession,
    client: KiteClient,
    positions: list[TradeExecution],
    force_close: bool = False,
    live: bool = False,
) -> None:
    """Trails the stop once a position is in profit, locking in gains if
    price pulls back before reaching target. The target still caps the
    trade - matches BacktestEngine's `_check_exit`, which explains why an
    uncapped version is unsafe (see its docstring); live polls far more
    often than the backtest's daily option snapshots so the argument is
    weaker here, but kept consistent until there's real evidence either way.

    `force_close=True` (past `eod_square_off_time`) skips stop/target/trail
    entirely and exits every position at the current market price - no
    carrying option positions overnight on a paper "intraday" strategy.

    `live=True` places a real sell order before marking the position
    closed - if that order fails, the position is left OPEN (retried next
    cycle) rather than marking a real position closed in our DB when the
    broker never actually closed it."""
    for position in positions:
        try:
            ltp = fetch_ltp(client, "NFO", position.symbol)
        except Exception as exc:  # noqa: BLE001 - one bad quote shouldn't stop the whole cycle
            logger.warning("live_exit_quote_failed", symbol=position.symbol, error=str(exc))
            continue

        exit_reason = "EOD_SQUAREOFF" if force_close else None
        if not force_close:
            entry_price = float(position.entry_price)
            original_stop_loss = stop_loss_from_percentage(entry_price, STOP_LOSS_PCT)
            current_stop_loss = float(position.stop_loss) if position.stop_loss is not None else original_stop_loss
            trail_step = entry_price * TRAIL_STEP_PCT
            new_stop_loss = trail_stop_loss(entry_price, ltp, current_stop_loss, trail_step)
            if new_stop_loss != current_stop_loss:
                position.stop_loss = new_stop_loss
            trailing_engaged = new_stop_loss > original_stop_loss

            if ltp <= new_stop_loss:
                exit_reason = "TRAILING_STOP" if trailing_engaged else "STOP_LOSS"
            elif position.target is not None and ltp >= float(position.target):
                exit_reason = "TARGET"

        if not exit_reason:
            continue

        exit_price = ltp
        if live:
            try:
                result = KiteOrderService(client).exit_position(position.symbol, position.quantity)
                exit_price = _fetch_fill_price(client, result.order_id, fallback=ltp)
            except Exception as exc:  # noqa: BLE001 - broker call can fail; don't mark closed if it did
                logger.error("live_exit_order_failed", symbol=position.symbol, error=str(exc))
                continue

        _close_position(position, exit_price, exit_reason)

    await db.commit()


async def _maybe_open_position(
    db: AsyncSession,
    client: KiteClient,
    settings: Settings,
    resolver: InstrumentResolver,
    snapshot: LiveSnapshot,
    risk_manager: RiskManager,
    open_positions: list[TradeExecution],
    mode: TradeMode,
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

    daily_pnl = await _daily_realized_pnl(db, mode)
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

    entry_price = snapshot.entry_price
    broker_order_id = None
    if mode == TradeMode.LIVE:
        try:
            result = KiteOrderService(client).buy_option(instrument.tradingsymbol, quantity)
        except Exception as exc:  # noqa: BLE001 - broker call failed; don't record a trade that never happened
            logger.error("live_order_placement_failed", symbol=instrument.tradingsymbol, error=str(exc))
            return
        broker_order_id = result.order_id
        entry_price = _fetch_fill_price(client, broker_order_id, fallback=snapshot.entry_price)

    trade = TradeExecution(
        order_id=uuid.uuid4(),
        signal_id=signal.signal_id,
        mode=mode,
        status=TradeStatus.OPEN,
        broker_order_id=broker_order_id,
        symbol=instrument.tradingsymbol,
        option_type=snapshot.suggested_option_type,
        quantity=quantity,
        entry_time=snapshot.as_of,
        entry_price=entry_price,
        stop_loss=snapshot.stop_loss,
        target=snapshot.target,
    )
    db.add(trade)
    await db.commit()
    logger.info(
        "live_position_opened" if mode == TradeMode.LIVE else "paper_position_opened",
        symbol=instrument.tradingsymbol,
        quantity=quantity,
        entry_price=entry_price,
        broker_order_id=broker_order_id,
        confidence=snapshot.decision.confidence_score,
    )


async def run_live_cycle(
    db: AsyncSession,
    client: KiteClient,
    resolver: InstrumentResolver,
    settings: Settings,
    signal_engine: SignalEngine,
) -> LiveSnapshot | None:
    """One iteration: check/close existing positions (paper or live,
    per `settings.paper_trading`) against live prices, then consider
    opening a new one if the Signal Engine currently says so and risk
    limits allow it. Returns the snapshot it computed (also useful for
    callers like `/live/status` that want the same read).

    At/after `settings.eod_square_off_time` (IST), every open position is
    force-closed at market price and no new one is opened this cycle -
    matches how a real intraday desk squares off before close."""
    snapshot = await compute_live_snapshot(db, client, resolver, settings, signal_engine)
    if snapshot is None:
        logger.warning("live_cycle_skipped_insufficient_history")
        return None

    mode = TradeMode.PAPER if settings.paper_trading else TradeMode.LIVE
    force_close = _is_past_square_off(datetime.now(UTC), settings.eod_square_off_time)
    open_positions = await _open_positions(db, mode)
    await _check_exits(db, client, open_positions, force_close=force_close, live=(mode == TradeMode.LIVE))

    if force_close:
        return snapshot

    remaining_open = await _open_positions(db, mode)
    risk_manager = RiskManager(
        RiskLimits(
            max_daily_loss=settings.max_daily_loss,
            max_trade_loss=settings.max_trade_loss,
            max_open_positions=settings.max_open_positions,
            capital=settings.paper_trading_capital,
            risk_per_trade_pct=settings.risk_per_trade_pct,
        )
    )
    await _maybe_open_position(db, client, settings, resolver, snapshot, risk_manager, remaining_open, mode)

    return snapshot
