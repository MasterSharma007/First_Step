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
