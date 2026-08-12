"""Tests for the backtest data-prep helpers that don't need a live DB:
building a per-strike option OHLC series and computing a real ATR from it."""

from datetime import UTC, date, datetime, timedelta

import pandas as pd

from app.models.option_ohlc import OptionOHLC
from app.services.backtesting.data_prep import build_option_series, option_atr_as_of


def _candle(minutes_ago: int, high: float, low: float, close: float) -> OptionOHLC:
    return OptionOHLC(
        underlying="BANKNIFTY",
        strike=48000,
        expiry=date(2026, 8, 25),
        option_type="CE",
        interval="1d",
        datetime_=datetime(2026, 1, 20, tzinfo=UTC) - timedelta(days=minutes_ago),
        open=close,
        high=high,
        low=low,
        close=close,
        volume=1000,
        oi=10000,
    )


def test_option_atr_as_of_returns_none_without_enough_history():
    candles = [_candle(i, 260, 240, 250) for i in range(5)]  # only 5, need period+1
    series = build_option_series(candles)
    as_of = pd.Timestamp(datetime(2026, 1, 20, tzinfo=UTC))
    assert option_atr_as_of(series, 48000, "CE", as_of, period=14) is None


def test_option_atr_as_of_computes_real_value_with_enough_history():
    candles = [_candle(i, 260, 240, 250) for i in range(20)]
    series = build_option_series(candles)
    as_of = pd.Timestamp(datetime(2026, 1, 20, tzinfo=UTC))
    atr_value = option_atr_as_of(series, 48000, "CE", as_of, period=14)
    assert atr_value is not None
    assert atr_value > 0


def test_option_atr_as_of_unknown_strike_returns_none():
    candles = [_candle(i, 260, 240, 250) for i in range(20)]
    series = build_option_series(candles)
    as_of = pd.Timestamp(datetime(2026, 1, 20, tzinfo=UTC))
    assert option_atr_as_of(series, 99999, "CE", as_of, period=14) is None
