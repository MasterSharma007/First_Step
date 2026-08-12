"""Multi-timeframe trend + support/resistance (15m/1h/1d/1w/1M).

Only 5m/15m and 1d candles are ever fetched from Kite. 1h is resampled
from 15m, 1w/1M are resampled from 1d - standard practice, avoids extra
API calls, and stays in sync with whatever's already live (see
app/workers/live_aggregation.py) instead of needing its own backfill.

Weekly/monthly readings are honest about not having enough history: a
year of daily bars is only ~52 weekly candles and ~12 monthly ones, and
detect_trend()'s EMA50 needs 50 bars to mean anything - with less than
that, `insufficient_data=True` and only support/resistance (much lower
bar requirement) is returned, no direction is guessed.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from app.services.market_analysis import indicators as ind
from app.services.market_analysis.trend import detect_trend

MIN_TREND_BARS = 50  # EMA50 needs this much history to be meaningful
RESAMPLE_AGG = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}


def resample_ohlc(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    if df.empty:
        return df
    return df.resample(rule).agg(RESAMPLE_AGG).dropna(subset=["open"])


@dataclass
class TimeframeReading:
    timeframe: str
    bars_available: int
    insufficient_data: bool
    support: float | None = None
    resistance: float | None = None
    direction: str | None = None
    reasons: list[str] | None = None


def analyze_timeframe(
    df: pd.DataFrame, timeframe: str, ce_writing: bool = False, pe_writing: bool = False
) -> TimeframeReading:
    if df.empty:
        return TimeframeReading(timeframe=timeframe, bars_available=0, insufficient_data=True)

    lookback = min(20, len(df))
    support, resistance = ind.support_resistance(df, lookback=lookback)

    if len(df) < MIN_TREND_BARS:
        return TimeframeReading(
            timeframe=timeframe,
            bars_available=len(df),
            insufficient_data=True,
            support=support,
            resistance=resistance,
        )

    reading = detect_trend(df, ce_writing=ce_writing, pe_writing=pe_writing)
    return TimeframeReading(
        timeframe=timeframe,
        bars_available=len(df),
        insufficient_data=False,
        support=support,
        resistance=resistance,
        direction=reading.direction,
        reasons=reading.reasons,
    )
