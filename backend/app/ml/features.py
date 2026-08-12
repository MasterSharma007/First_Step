"""Feature extraction for the AI Scoring Model (SRD §8).

Produces a flat, model-ready feature dict from the same inputs the
rule-based Signal Engine consumes, so both can be compared/blended and the
trained model (see `app/ml/model.py`) can eventually replace the rule-based
scorer without changing callers.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SignalFeatures:
    # Trend features
    price_above_vwap: bool
    ema9_gt_ema20: bool
    ema20_gt_ema50: bool
    higher_high_higher_low: bool
    lower_high_lower_low: bool

    # Options features
    pcr: float
    ce_oi_change_near_atm: int
    pe_oi_change_near_atm: int
    oi_buildup_bias: float  # -1 (bearish) .. +1 (bullish), from classify_oi_buildup on the ATM strike

    # Volume features
    volume_spike: bool
    relative_volume: float

    # Volatility features
    india_vix: float
    atr: float

    def as_dict(self) -> dict:
        return {
            "price_above_vwap": int(self.price_above_vwap),
            "ema9_gt_ema20": int(self.ema9_gt_ema20),
            "ema20_gt_ema50": int(self.ema20_gt_ema50),
            "higher_high_higher_low": int(self.higher_high_higher_low),
            "lower_high_lower_low": int(self.lower_high_lower_low),
            "pcr": self.pcr,
            "ce_oi_change_near_atm": self.ce_oi_change_near_atm,
            "pe_oi_change_near_atm": self.pe_oi_change_near_atm,
            "oi_buildup_bias": self.oi_buildup_bias,
            "volume_spike": int(self.volume_spike),
            "relative_volume": self.relative_volume,
            "india_vix": self.india_vix,
            "atr": self.atr,
        }
