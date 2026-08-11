"""Price-action indicators used by the Market Analysis Engine (SRD §2).

All functions take/return `pandas` Series or DataFrames indexed by time,
operating on OHLCV columns named open/high/low/close/volume.
"""

from __future__ import annotations

import pandas as pd


def vwap(df: pd.DataFrame) -> pd.Series:
    """Volume-weighted average price. Index instruments (e.g. NIFTY BANK
    spot) always report zero volume from Kite - true VWAP is undefined
    there, so bars with no cumulative volume fall back to the cumulative
    mean typical price instead of propagating NaN into every downstream
    comparison (which raises on truthiness checks)."""
    typical_price = (df["high"] + df["low"] + df["close"]) / 3
    cumulative_pv = (typical_price * df["volume"]).cumsum()
    cumulative_vol = df["volume"].cumsum().replace(0, float("nan"))
    volume_weighted = cumulative_pv / cumulative_vol
    return volume_weighted.fillna(typical_price.expanding().mean())


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    true_range = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return true_range.ewm(span=period, adjust=False).mean()


def support_resistance(df: pd.DataFrame, lookback: int = 20) -> tuple[float, float]:
    """Simple rolling-window support/resistance from recent swing low/high."""
    window = df.tail(lookback)
    return float(window["low"].min()), float(window["high"].max())


def is_breakout_candle(df: pd.DataFrame, resistance: float, volume_multiplier: float = 1.5) -> bool:
    last = df.iloc[-1]
    avg_volume = df["volume"].tail(20).mean()
    return bool(last["close"] > resistance and last["volume"] > avg_volume * volume_multiplier)


def is_breakdown_candle(df: pd.DataFrame, support: float, volume_multiplier: float = 1.5) -> bool:
    last = df.iloc[-1]
    avg_volume = df["volume"].tail(20).mean()
    return bool(last["close"] < support and last["volume"] > avg_volume * volume_multiplier)


def is_volume_spike(df: pd.DataFrame, lookback: int = 20, multiplier: float = 1.5) -> bool:
    avg_volume = df["volume"].tail(lookback).mean()
    if not avg_volume:
        return False
    return bool(df["volume"].iloc[-1] > avg_volume * multiplier)


def higher_high_higher_low(df: pd.DataFrame, lookback: int = 3) -> bool:
    highs = df["high"].tail(lookback)
    lows = df["low"].tail(lookback)
    return bool(highs.is_monotonic_increasing and lows.is_monotonic_increasing)


def lower_high_lower_low(df: pd.DataFrame, lookback: int = 3) -> bool:
    highs = df["high"].tail(lookback)
    lows = df["low"].tail(lookback)
    return bool(highs.is_monotonic_decreasing and lows.is_monotonic_decreasing)


def with_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of `df` with vwap/ema9/ema20/ema50/atr columns attached."""
    out = df.copy()
    out["vwap"] = vwap(out)
    out["ema9"] = ema(out["close"], 9)
    out["ema20"] = ema(out["close"], 20)
    out["ema50"] = ema(out["close"], 50)
    out["atr"] = atr(out)
    return out
