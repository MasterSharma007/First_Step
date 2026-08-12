"""Builds the as-of option-chain/VIX lookups `BacktestEngine.run()` needs
from whatever's actually in the DB (SRD §2, §9).

Option chain and VIX history are typically coarser than the spot bars
being backtested (e.g. daily option snapshots vs. 5m spot candles), so a
naive exact-timestamp match would find nothing. Instead we carry forward
the most recent snapshot at-or-before each spot bar's timestamp - the same
"as-of" semantics a live system has anyway (you trade on the last known
chain state, not a future one).
"""

from __future__ import annotations

import pandas as pd

from app.models.india_vix import IndiaVix
from app.models.option_ohlc import OptionOHLC
from app.services.market_analysis.indicators import atr as _atr
from app.services.option_chain.analyzer import StrikeRow


def _option_rows_to_chain(rows: list[OptionOHLC]) -> list[StrikeRow]:
    by_strike: dict[float, dict[str, OptionOHLC]] = {}
    for r in rows:
        by_strike.setdefault(float(r.strike), {})[r.option_type] = r

    chain = []
    for strike, sides in by_strike.items():
        ce, pe = sides.get("CE"), sides.get("PE")
        chain.append(
            StrikeRow(
                strike=strike,
                ce_oi=ce.oi if ce else 0,
                ce_oi_change=ce.oi_change if ce else 0,
                ce_volume=ce.volume if ce else 0,
                ce_ltp=float(ce.close) if ce else 0.0,
                pe_oi=pe.oi if pe else 0,
                pe_oi_change=pe.oi_change if pe else 0,
                pe_volume=pe.volume if pe else 0,
                pe_ltp=float(pe.close) if pe else 0.0,
            )
        )
    return chain


def build_option_chain_by_time(
    option_rows: list[OptionOHLC], spot_index: pd.DatetimeIndex
) -> dict[pd.Timestamp, list[StrikeRow]]:
    """`option_rows` need not be sorted or aligned to `spot_index` - this
    groups them into per-timestamp chain snapshots, then forward-fills onto
    every bar in `spot_index` from the latest snapshot at or before it."""
    by_ts: dict[pd.Timestamp, list[OptionOHLC]] = {}
    for r in option_rows:
        by_ts.setdefault(pd.Timestamp(r.datetime_), []).append(r)

    snapshot_times = sorted(by_ts.keys())
    if not snapshot_times:
        return {}

    chains_by_snapshot = {ts: _option_rows_to_chain(rows) for ts, rows in by_ts.items()}

    result: dict[pd.Timestamp, list[StrikeRow]] = {}
    idx = 0
    n = len(snapshot_times)
    for ts in spot_index:
        while idx + 1 < n and snapshot_times[idx + 1] <= ts:
            idx += 1
        if snapshot_times[idx] <= ts:
            result[ts] = chains_by_snapshot[snapshot_times[idx]]
    return result


def build_option_series(option_rows: list[OptionOHLC]) -> dict[tuple[float, str], list[OptionOHLC]]:
    """Groups option candles by (strike, option_type), sorted by time, so
    the engine can compute a real ATR from the specific instrument it's
    actually about to trade - not an approximation off the spot index,
    which is a different, much larger-scale series (see
    `app/services/backtesting/engine.py` for why that distinction matters)."""
    series: dict[tuple[float, str], list[OptionOHLC]] = {}
    for r in option_rows:
        series.setdefault((float(r.strike), r.option_type), []).append(r)
    for rows in series.values():
        rows.sort(key=lambda r: r.datetime_)
    return series


def option_atr_as_of(
    series: dict[tuple[float, str], list[OptionOHLC]],
    strike: float,
    option_type: str,
    as_of: pd.Timestamp,
    period: int = 14,
) -> float | None:
    """Real ATR of the option's own premium, using candles up to `as_of`.
    Returns None if there's not enough history yet for this instrument -
    callers should fall back to a percentage-based stop in that case."""
    rows = series.get((strike, option_type))
    if not rows:
        return None

    candles = [r for r in rows if pd.Timestamp(r.datetime_) <= as_of]
    if len(candles) < period + 1:
        return None

    candles = candles[-(period + 1) :]
    df = pd.DataFrame(
        {
            "high": [float(c.high) for c in candles],
            "low": [float(c.low) for c in candles],
            "close": [float(c.close) for c in candles],
        }
    )
    return float(_atr(df, period=period).iloc[-1])


def build_vix_by_time(vix_rows: list[IndiaVix], spot_index: pd.DatetimeIndex) -> dict[pd.Timestamp, float]:
    points = sorted((pd.Timestamp(r.datetime_), float(r.value)) for r in vix_rows)
    if not points:
        return {}

    result: dict[pd.Timestamp, float] = {}
    idx = 0
    n = len(points)
    for ts in spot_index:
        while idx + 1 < n and points[idx + 1][0] <= ts:
            idx += 1
        if points[idx][0] <= ts:
            result[ts] = points[idx][1]
    return result
