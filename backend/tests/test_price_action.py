"""Tests for candle break, S/R break, and swing-point structure detection."""

import pandas as pd

from app.services.market_analysis.price_action import (
    analyze_price_action,
    detect_candle_break,
    detect_sr_break,
    detect_swing_points,
)


def _df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows, index=pd.date_range("2026-01-01 09:15", periods=len(rows), freq="5min"))


def test_candle_break_up_when_price_above_prior_high():
    df = _df(
        [
            {"open": 100, "high": 105, "low": 98, "close": 102, "volume": 0},
            {"open": 102, "high": 103, "low": 101, "close": 102.5, "volume": 0},  # forming bar, ignored
        ]
    )
    result = detect_candle_break(df, current_price=110)
    assert result.direction == "UP"
    assert result.reference_high == 105


def test_candle_break_down_when_price_below_prior_low():
    df = _df(
        [
            {"open": 100, "high": 105, "low": 98, "close": 102, "volume": 0},
            {"open": 102, "high": 103, "low": 101, "close": 102.5, "volume": 0},
        ]
    )
    result = detect_candle_break(df, current_price=90)
    assert result.direction == "DOWN"
    assert result.reference_low == 98


def test_candle_break_none_when_inside_range():
    df = _df(
        [
            {"open": 100, "high": 105, "low": 98, "close": 102, "volume": 0},
            {"open": 102, "high": 103, "low": 101, "close": 102.5, "volume": 0},
        ]
    )
    result = detect_candle_break(df, current_price=101)
    assert result.direction is None


def test_candle_break_none_with_fewer_than_two_bars():
    df = _df([{"open": 100, "high": 105, "low": 98, "close": 102, "volume": 0}])
    assert detect_candle_break(df, current_price=110) is None


def test_sr_break_detects_resistance_and_support():
    assert detect_sr_break(110, support=95, resistance=105) == "RESISTANCE_BREAK"
    assert detect_sr_break(90, support=95, resistance=105) == "SUPPORT_BREAK"
    assert detect_sr_break(100, support=95, resistance=105) is None


def test_swing_points_empty_when_too_few_bars():
    df = _df([{"open": 100, "high": 101, "low": 99, "close": 100, "volume": 0} for _ in range(5)])
    assert detect_swing_points(df, window=3) == []


def test_swing_points_detects_higher_high_and_higher_low():
    # A clear uptrend of pivots: swing low, swing high, higher swing low, higher swing high.
    highs = [100, 101, 99, 98, 110, 98, 99, 100, 90, 91, 92, 130, 92, 91, 90]
    lows = [h - 5 for h in highs]
    rows = [{"open": h - 2, "high": h, "low": low, "close": h - 1, "volume": 0} for h, low in zip(highs, lows)]
    df = _df(rows)
    points = detect_swing_points(df, window=3)
    assert len(points) > 0
    assert all(p.kind in {"HH", "LH", "HL", "LL"} for p in points)


def test_analyze_price_action_empty_df():
    reading = analyze_price_action(pd.DataFrame(), "5m", current_price=100, support=None, resistance=None)
    assert reading.candle_break is None
    assert reading.sr_break is None
    assert reading.swing_points == []
    assert reading.structure is None


def test_analyze_price_action_full_reading():
    df = _df(
        [
            {"open": 100, "high": 105, "low": 98, "close": 102, "volume": 0},
            {"open": 102, "high": 103, "low": 101, "close": 102.5, "volume": 0},
        ]
    )
    reading = analyze_price_action(df, "5m", current_price=110, support=95, resistance=104)
    assert reading.candle_break.direction == "UP"
    assert reading.sr_break == "RESISTANCE_BREAK"
    assert reading.support == 95
    assert reading.resistance == 104
