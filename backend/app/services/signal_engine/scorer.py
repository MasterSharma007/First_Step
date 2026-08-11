"""Signal Generation Engine (SRD §2, §6, §8).

Combines the Market Analysis + Option Chain engines' outputs into
`SignalFeatures`, scores them, and applies the SRD §6 entry thresholds to
decide whether to emit a CE/PE entry signal.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from app.ml.features import SignalFeatures
from app.ml.model import RuleBasedScorer, Scorer, verdict_for_score
from app.services.market_analysis import indicators as ind
from app.services.option_chain.analyzer import StrikeRow, put_call_ratio, writing_activity


@dataclass
class SignalDecision:
    signal_type: str  # CE_ENTRY, PE_ENTRY, NO_TRADE
    confidence_score: float
    verdict: str
    reasons: dict


class SignalEngine:
    def __init__(
        self,
        scorer: Scorer | None = None,
        ce_threshold: float = 70.0,
        pe_threshold: float = 30.0,
    ):
        self.scorer = scorer or RuleBasedScorer()
        self.ce_threshold = ce_threshold
        self.pe_threshold = pe_threshold

    def build_features(
        self,
        spot_df: pd.DataFrame,
        option_chain_rows: list[StrikeRow],
        spot_price: float,
        india_vix: float,
    ) -> SignalFeatures:
        enriched = ind.with_indicators(spot_df)
        last = enriched.iloc[-1]
        avg_volume = spot_df["volume"].tail(20).mean() or 1

        pcr = put_call_ratio(option_chain_rows)
        writing = writing_activity(option_chain_rows, spot_price=spot_price)

        return SignalFeatures(
            price_above_vwap=bool(last["close"] > last["vwap"]),
            ema9_gt_ema20=bool(last["ema9"] > last["ema20"]),
            ema20_gt_ema50=bool(last["ema20"] > last["ema50"]),
            higher_high_higher_low=ind.higher_high_higher_low(enriched),
            lower_high_lower_low=ind.lower_high_lower_low(enriched),
            pcr=pcr,
            ce_oi_change_near_atm=writing["ce_oi_change_near_atm"],
            pe_oi_change_near_atm=writing["pe_oi_change_near_atm"],
            volume_spike=ind.is_volume_spike(spot_df),
            relative_volume=float(spot_df["volume"].iloc[-1] / avg_volume),
            india_vix=india_vix,
            atr=float(last["atr"]),
        )

    def evaluate(
        self,
        spot_df: pd.DataFrame,
        option_chain_rows: list[StrikeRow],
        spot_price: float,
        india_vix: float,
    ) -> SignalDecision:
        features = self.build_features(spot_df, option_chain_rows, spot_price, india_vix)
        score = self.scorer.score(features)
        verdict = verdict_for_score(score, self.ce_threshold, self.pe_threshold)

        if verdict == "STRONG_CE":
            signal_type = "CE_ENTRY"
        elif verdict == "STRONG_PE":
            signal_type = "PE_ENTRY"
        else:
            signal_type = "NO_TRADE"

        return SignalDecision(
            signal_type=signal_type,
            confidence_score=score,
            verdict=verdict,
            reasons=features.as_dict(),
        )
