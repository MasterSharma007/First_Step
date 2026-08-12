"""Computes the current live "cockpit" view (SRD §2): live price, trend +
support/resistance, live option chain read, and what the Signal Engine
would do right now - including which strike/side it's actually pointing
at and its live premium, not just an abstract score.

Shared by the live paper-trading loop (`app/workers/live_loop.py`, which
also persists data) and the read-only `GET /live/status` endpoint, so both
can never silently disagree about what "the current signal" is.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.logging import get_logger
from app.models.spot_ohlc import SpotOHLC
from app.services.kite.client import KiteClient
from app.services.kite.instruments import InstrumentResolver
from app.services.kite.live_quote import fetch_ltp, fetch_quotes, option_chain_from_quotes
from app.services.market_analysis import indicators as ind
from app.services.market_analysis.trend import TrendReading, detect_trend
from app.services.option_chain.analyzer import (
    StrikeRow,
    atm_strike,
    max_pain,
    put_call_ratio,
    writing_activity,
)
from app.services.signal_engine.exit_rules import compute_exit_levels
from app.services.signal_engine.scorer import SignalDecision, SignalEngine

logger = get_logger(__name__)

MIN_SPOT_BARS = 50
NEAR_ATM_STRIKES = 10  # each side, matches the backfill CLI default
STOP_LOSS_POINTS = 20.0  # premium points - same convention as BacktestEngine's default


@dataclass
class LiveSnapshot:
    as_of: datetime
    spot_price: float
    trend: TrendReading
    support: float
    resistance: float
    expiry: date | None
    atm_strike: float | None
    pcr: float | None
    max_pain: float | None
    oi_signal: str | None
    chain: list[StrikeRow]
    india_vix: float
    decision: SignalDecision | None
    suggested_strike: float | None = None
    suggested_option_type: str | None = None
    entry_price: float | None = None
    stop_loss: float | None = None
    target: float | None = None


async def _load_spot_df(db: AsyncSession, symbol: str, live_price: float) -> pd.DataFrame | None:
    stmt = (
        select(SpotOHLC)
        .where(SpotOHLC.symbol == symbol, SpotOHLC.interval == "5m")
        .order_by(SpotOHLC.datetime_.desc())
        .limit(100)
    )
    rows = list((await db.execute(stmt)).scalars().all())
    if len(rows) < MIN_SPOT_BARS:
        return None
    rows.reverse()

    df = pd.DataFrame(
        [
            {
                "datetime": r.datetime_,
                "open": float(r.open),
                "high": float(r.high),
                "low": float(r.low),
                "close": float(r.close),
                "volume": r.volume,
            }
            for r in rows
        ]
    ).set_index("datetime")
    # Splice the live tick in as the current bar's close so trend/EMA/S-R
    # react to right-now, not just the last completed 5m candle.
    df.loc[df.index[-1], "close"] = live_price
    return df


async def compute_live_snapshot(
    db: AsyncSession,
    client: KiteClient,
    resolver: InstrumentResolver,
    settings: Settings,
    signal_engine: SignalEngine,
) -> LiveSnapshot | None:
    """Returns None if there isn't enough spot history yet (needs >= 50
    bars, same floor as GET /market-data/trend) - run the backfill first."""
    spot_price = fetch_ltp(client, "NSE", settings.trading_symbol)

    df = await _load_spot_df(db, settings.trading_symbol, spot_price)
    if df is None:
        return None

    try:
        india_vix = fetch_ltp(client, "NSE", "INDIA VIX")
    except Exception as exc:  # noqa: BLE001 - best-effort fallback, any Kite failure here shouldn't sink the whole snapshot
        india_vix = 15.0
        logger.warning("live_vix_fetch_failed", error=str(exc))

    expiries = resolver.expiries(settings.nfo_underlying)
    expiry = expiries[0] if expiries else None

    chain: list[StrikeRow] = []
    if expiry is not None:
        option_instruments = resolver.options(settings.nfo_underlying, expiry)
        nearest = sorted(option_instruments, key=lambda i: abs(i.strike - spot_price))[: NEAR_ATM_STRIKES * 2]
        quotes = fetch_quotes(client, nearest)
        chain = option_chain_from_quotes(nearest, quotes)

    ce_writing = pe_writing = False
    pcr = max_pain_value = atm = oi_signal = None
    if chain:
        writing = writing_activity(chain, spot_price=spot_price)
        ce_writing, pe_writing = writing["ce_writing"], writing["pe_writing"]
        oi_signal = writing["verdict"]
        pcr = put_call_ratio(chain)
        max_pain_value = max_pain(chain)
        atm = atm_strike(chain, spot_price)

    trend = detect_trend(df, ce_writing=ce_writing, pe_writing=pe_writing)
    support, resistance = ind.support_resistance(df)

    decision = None
    suggested_strike = suggested_option_type = None
    entry_price = stop_loss = target = None
    if chain:
        decision = signal_engine.evaluate(df, chain, spot_price, india_vix)
        atm_row = next((r for r in chain if r.strike == atm), None)
        if decision.signal_type == "CE_ENTRY" and atm_row and atm_row.ce_ltp > 0:
            suggested_strike, suggested_option_type, entry_price = atm, "CE", atm_row.ce_ltp
        elif decision.signal_type == "PE_ENTRY" and atm_row and atm_row.pe_ltp > 0:
            suggested_strike, suggested_option_type, entry_price = atm, "PE", atm_row.pe_ltp

        if entry_price is not None:
            levels = compute_exit_levels(entry_price, STOP_LOSS_POINTS, settings.risk_reward_ratio)
            stop_loss, target = levels.stop_loss, levels.target

    return LiveSnapshot(
        as_of=datetime.now(UTC),
        spot_price=spot_price,
        trend=trend,
        support=support,
        resistance=resistance,
        expiry=expiry,
        atm_strike=atm,
        pcr=pcr,
        max_pain=max_pain_value,
        oi_signal=oi_signal,
        chain=chain,
        india_vix=india_vix,
        decision=decision,
        suggested_strike=suggested_strike,
        suggested_option_type=suggested_option_type,
        entry_price=entry_price,
        stop_loss=stop_loss,
        target=target,
    )
