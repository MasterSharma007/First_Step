"""Live price-action reads: candle breakout/breakdown, support/resistance
breaks, and swing-point market structure (HH/LH/HL/LL) - the kind of
levels a discretionary intraday trader watches candle by candle, on top
of the higher-timeframe trend/S-R already in multi_timeframe.py.

Swing points use real pivot detection (a bar whose high/low is the most
extreme within `SWING_WINDOW` bars on each side), not the crude "last 3
bars monotonic" check in indicators.py::higher_high_higher_low - that
one feeds the EMA/VWAP trend score and stays as-is; this one is for a
dedicated structure display.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

SWING_WINDOW = 3  # bars required on each side to confirm a pivot high/low
MAX_SWING_POINTS = 10  # plenty for a UI list/mini-chart


@dataclass
class CandleBreak:
    direction: str | None  # "UP", "DOWN", or None (still inside the prior candle's range)
    reference_high: float
    reference_low: float
    reference_time: str


@dataclass
class SwingPoint:
    kind: str  # "HH", "LH", "HL", "LL"
    price: float
    time: str


@dataclass
class PriceAction:
    timeframe: str
    current_price: float
    candle_break: CandleBreak | None = None
    sr_break: str | None = None  # "SUPPORT_BREAK", "RESISTANCE_BREAK", or None
    support: float | None = None
    resistance: float | None = None
    swing_points: list[SwingPoint] = field(default_factory=list)
    structure: str | None = None  # kind of the most recent confirmed swing point


def detect_candle_break(df: pd.DataFrame, current_price: float) -> CandleBreak | None:
    """Break of the most recently CLOSED candle's high/low. The last row
    of `df` is treated as the still-forming live bar (see
    app/workers/live_aggregation.py), so the reference is `iloc[-2]`."""
    if len(df) < 2:
        return None
    prior = df.iloc[-2]
    direction = None
    if current_price > prior["high"]:
        direction = "UP"
    elif current_price < prior["low"]:
        direction = "DOWN"
    return CandleBreak(
        direction=direction,
        reference_high=float(prior["high"]),
        reference_low=float(prior["low"]),
        reference_time=str(df.index[-2]),
    )


def detect_sr_break(current_price: float, support: float | None, resistance: float | None) -> str | None:
    if resistance is not None and current_price > resistance:
        return "RESISTANCE_BREAK"
    if support is not None and current_price < support:
        return "SUPPORT_BREAK"
    return None


def detect_swing_points(df: pd.DataFrame, window: int = SWING_WINDOW) -> list[SwingPoint]:
    """Fractal pivot highs/lows, classified against the previous swing of
    the same kind. The most recent `window` bars can't be confirmed yet
    (need bars on both sides), so they're excluded."""
    if len(df) < window * 2 + 1:
        return []

    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()
    confirmed_end = len(df) - window

    raw_points: list[tuple[str, float, object]] = []
    for i in range(window, confirmed_end):
        if highs[i] == highs[i - window : i + window + 1].max():
            raw_points.append(("HIGH", float(highs[i]), df.index[i]))
        if lows[i] == lows[i - window : i + window + 1].min():
            raw_points.append(("LOW", float(lows[i]), df.index[i]))
    raw_points.sort(key=lambda p: p[2])

    result: list[SwingPoint] = []
    last_high: float | None = None
    last_low: float | None = None
    for kind, price, ts in raw_points:
        if kind == "HIGH":
            label = None if last_high is None else ("HH" if price > last_high else "LH")
            last_high = price
        else:
            label = None if last_low is None else ("HL" if price > last_low else "LL")
            last_low = price
        if label is not None:
            result.append(SwingPoint(kind=label, price=price, time=str(ts)))

    return result[-MAX_SWING_POINTS:]


def analyze_price_action(
    df: pd.DataFrame,
    timeframe: str,
    current_price: float,
    support: float | None,
    resistance: float | None,
) -> PriceAction:
    if df.empty:
        return PriceAction(timeframe=timeframe, current_price=current_price)

    swing_points = detect_swing_points(df)
    return PriceAction(
        timeframe=timeframe,
        current_price=current_price,
        candle_break=detect_candle_break(df, current_price),
        sr_break=detect_sr_break(current_price, support, resistance),
        support=support,
        resistance=resistance,
        swing_points=swing_points,
        structure=swing_points[-1].kind if swing_points else None,
    )
