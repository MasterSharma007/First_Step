"""Trend Detection Engine (SRD §2).

Combines price-action indicators with option-chain writing activity to
classify the prevailing trend as bullish, bearish, or neutral. Also used
for the ~08:30 pre-market directional guess against the previous session's
levels plus the current futures/VIX read.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from app.services.market_analysis import indicators as ind


@dataclass
class TrendReading:
    direction: str  # BULLISH, BEARISH, NEUTRAL
    reasons: list[str] = field(default_factory=list)


def detect_trend(df: pd.DataFrame, ce_writing: bool, pe_writing: bool) -> TrendReading:
    """`df` must have close/high/low/volume with at least 50 rows for EMA50."""
    enriched = ind.with_indicators(df)
    last = enriched.iloc[-1]

    bullish_reasons: list[str] = []
    bearish_reasons: list[str] = []

    if last["close"] > last["vwap"]:
        bullish_reasons.append("Price Above VWAP")
    else:
        bearish_reasons.append("Price Below VWAP")

    if last["ema9"] > last["ema20"] > last["ema50"]:
        bullish_reasons.append("EMA Alignment Bullish (9>20>50)")
    elif last["ema9"] < last["ema20"] < last["ema50"]:
        bearish_reasons.append("EMA Alignment Bearish (9<20<50)")

    if pe_writing:
        bullish_reasons.append("PE Writing")
    if ce_writing:
        bearish_reasons.append("CE Writing")

    if ind.higher_high_higher_low(enriched):
        bullish_reasons.append("Higher High Higher Low")
    if ind.lower_high_lower_low(enriched):
        bearish_reasons.append("Lower High Lower Low")

    if len(bullish_reasons) > len(bearish_reasons):
        return TrendReading("BULLISH", bullish_reasons)
    if len(bearish_reasons) > len(bullish_reasons):
        return TrendReading("BEARISH", bearish_reasons)
    return TrendReading("NEUTRAL", bullish_reasons + bearish_reasons)


def premarket_guess(
    prev_close: float,
    prev_high: float,
    prev_low: float,
    sgx_nifty_change_pct: float | None,
    india_vix: float | None,
    india_vix_prev: float | None,
) -> TrendReading:
    """Rough pre-market (~08:30) directional guess.

    Best-effort heuristic only - real market open frequently deviates from
    pre-market futures. Treat the output as a prior to be confirmed by the
    Trend Detection Engine once the first live candles form, not a signal.
    """
    reasons: list[str] = []
    score = 0

    if sgx_nifty_change_pct is not None:
        if sgx_nifty_change_pct > 0.15:
            score += 1
            reasons.append(f"Futures indicating gap-up ({sgx_nifty_change_pct:+.2f}%)")
        elif sgx_nifty_change_pct < -0.15:
            score -= 1
            reasons.append(f"Futures indicating gap-down ({sgx_nifty_change_pct:+.2f}%)")

    if india_vix is not None and india_vix_prev is not None:
        vix_change = india_vix - india_vix_prev
        if vix_change > 0.5:
            score -= 1
            reasons.append(f"VIX rising ({vix_change:+.2f}) - risk-off bias")
        elif vix_change < -0.5:
            score += 1
            reasons.append(f"VIX falling ({vix_change:+.2f}) - risk-on bias")

    direction = "BULLISH" if score > 0 else "BEARISH" if score < 0 else "NEUTRAL"
    return TrendReading(direction, reasons)
