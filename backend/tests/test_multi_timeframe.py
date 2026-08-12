"""Tests for multi-timeframe resampling and the insufficient-data guard."""

import numpy as np
import pandas as pd
import pytest

from app.services.market_analysis.multi_timeframe import analyze_timeframe, resample_ohlc


@pytest.fixture
def daily_df() -> pd.DataFrame:
    n = 400  # > 1 year of daily bars - enough for a real weekly/monthly trend read
    rng = np.random.default_rng(7)
    base = np.linspace(48000, 49000, n) + rng.normal(0, 20, n)
    return pd.DataFrame(
        {
            "open": base,
            "high": base + rng.uniform(5, 25, n),
            "low": base - rng.uniform(5, 25, n),
            "close": base + rng.normal(0, 5, n),
            "volume": rng.integers(1000, 5000, n),
        },
        index=pd.date_range("2025-01-01", periods=n, freq="D"),
    )


def test_resample_weekly_reduces_row_count(daily_df):
    weekly = resample_ohlc(daily_df, "W")
    assert 0 < len(weekly) < len(daily_df)


def test_resample_monthly_reduces_row_count_further(daily_df):
    monthly = resample_ohlc(daily_df, "ME")
    weekly = resample_ohlc(daily_df, "W")
    assert len(monthly) < len(weekly)


def test_resample_preserves_ohlc_semantics(daily_df):
    weekly = resample_ohlc(daily_df, "W")
    # Use the resampled bucket's own end date (pandas "W" buckets end on
    # Sunday, not aligned to the source's start day) to slice the matching
    # source rows, rather than assuming a fixed 7-row window.
    bucket_end = weekly.index[0]
    source_in_bucket = daily_df.loc[:bucket_end]
    first_week = weekly.iloc[0]
    assert first_week["high"] == pytest.approx(source_in_bucket["high"].max())
    assert first_week["low"] == pytest.approx(source_in_bucket["low"].min())
    assert first_week["high"] >= first_week["low"]
    assert first_week["high"] >= first_week["open"]
    assert first_week["high"] >= first_week["close"]


def test_analyze_timeframe_empty_df_is_insufficient():
    reading = analyze_timeframe(pd.DataFrame(), "1M")
    assert reading.insufficient_data is True
    assert reading.direction is None
    assert reading.bars_available == 0


def test_analyze_timeframe_few_bars_gives_support_resistance_but_no_direction():
    n = 12  # fewer than MIN_TREND_BARS (50)
    df = pd.DataFrame(
        {"open": 100, "high": 110, "low": 90, "close": 105, "volume": 1000},
        index=pd.date_range("2026-01-01", periods=n, freq="ME"),
    )
    reading = analyze_timeframe(df, "1M")
    assert reading.insufficient_data is True
    assert reading.direction is None
    assert reading.support is not None
    assert reading.resistance is not None


def test_analyze_timeframe_enough_bars_gives_a_direction(daily_df):
    reading = analyze_timeframe(daily_df, "1d")
    assert reading.insufficient_data is False
    assert reading.direction in {"BULLISH", "BEARISH", "NEUTRAL"}
    assert reading.support is not None
    assert reading.resistance is not None
