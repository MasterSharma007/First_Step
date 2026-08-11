"""AI Scoring Model interface (SRD §8).

`RuleBasedScorer` implements the weighted rule-based score described in the
SRD today - it needs no training data and is what `SignalEngine` uses out
of the box. `MLScorer` is the interface a trained scikit-learn/XGBoost/
LightGBM model should implement once enough labelled trade outcomes exist
to train on (see docs/SRD.md §11 Phase 2). Swapping one for the other is a
one-line change in `app.services.signal_engine.scorer`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from app.ml.features import SignalFeatures


class Scorer(Protocol):
    def score(self, features: SignalFeatures) -> float:
        """Return a confidence score in [0, 100]. 0-30 Strong PE, 30-70 No
        Trade, 70-100 Strong CE (SRD §8)."""
        ...


class RuleBasedScorer:
    """Weighted-sum scorer over the four SRD §8 feature groups.

    Each group contributes up to 25 points toward a bullish (CE) score;
    the same signals pushed the other way contribute toward a bearish (PE)
    read. Final score is centered at 50 (no trade).
    """

    def score(self, features: SignalFeatures) -> float:
        score = 50.0

        # Trend group (+/- 25)
        trend_points = 0
        trend_points += 1 if features.price_above_vwap else -1
        trend_points += 1 if features.ema9_gt_ema20 else -1
        trend_points += 1 if features.ema20_gt_ema50 else -1
        trend_points += 1 if features.higher_high_higher_low else 0
        trend_points -= 1 if features.lower_high_lower_low else 0
        score += (trend_points / 4) * 25

        # Options group (+/- 25): high PCR + PE writing => bullish
        options_points = 0.0
        if features.pcr >= 1.2:
            options_points += 1
        elif features.pcr <= 0.8:
            options_points -= 1
        if features.pe_oi_change_near_atm > features.ce_oi_change_near_atm:
            options_points += 1
        elif features.ce_oi_change_near_atm > features.pe_oi_change_near_atm:
            options_points -= 1
        score += (options_points / 2) * 25

        # Volume group (+/- 15): a spike amplifies whatever direction trend+options already lean
        if features.volume_spike:
            score += 15 if score >= 50 else -15
        score += min(max(features.relative_volume - 1, -1), 1) * 5

        # Volatility group (dampener, not directional): high VIX pulls toward "no trade"
        if features.india_vix > 20:
            score += (50 - score) * 0.2

        return round(min(max(score, 0.0), 100.0), 2)


def verdict_for_score(score: float, ce_threshold: float = 70.0, pe_threshold: float = 30.0) -> str:
    if score >= ce_threshold:
        return "STRONG_CE"
    if score <= pe_threshold:
        return "STRONG_PE"
    return "NO_TRADE"


class MLScorer:
    """Loads a trained model artifact (joblib/pickle) and scores features
    through it. Not wired up until a model has been trained via the
    Backtesting Engine's trade history - see docs/SRD.md §11 Phase 2."""

    def __init__(self, model_path: Path):
        if not model_path.exists():
            raise FileNotFoundError(
                f"No trained model at {model_path}. Train one first (Phase 2) or use RuleBasedScorer."
            )
        import joblib

        self._model = joblib.load(model_path)

    def score(self, features: SignalFeatures) -> float:
        proba = self._model.predict_proba([list(features.as_dict().values())])[0]
        # Assumes binary classifier where class 1 == bullish; scale to 0-100.
        return round(float(proba[1]) * 100, 2)
