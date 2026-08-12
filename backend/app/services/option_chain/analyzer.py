"""Option Chain Analysis Engine (SRD §2).

Operates on a single expiry's chain, expressed as a list of per-strike rows
with ce/pe OI, OI change, volume, LTP. Pure functions - no I/O - so they are
directly unit-testable and reusable from both the live pipeline and the
backtester.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class StrikeRow:
    strike: float
    ce_oi: int = 0
    ce_oi_change: int = 0
    ce_volume: int = 0
    ce_ltp: float = 0.0
    pe_oi: int = 0
    pe_oi_change: int = 0
    pe_volume: int = 0
    pe_ltp: float = 0.0


def put_call_ratio(rows: list[StrikeRow]) -> float:
    total_ce_oi = sum(r.ce_oi for r in rows)
    total_pe_oi = sum(r.pe_oi for r in rows)
    if total_ce_oi == 0:
        return 0.0
    return round(total_pe_oi / total_ce_oi, 3)


def max_pain(rows: list[StrikeRow]) -> float:
    """Strike at which total option-writer loss (== buyer payout) is minimized."""
    strikes = [r.strike for r in rows]
    best_strike = strikes[0] if strikes else 0.0
    lowest_payout = None

    for candidate in strikes:
        payout = 0.0
        for r in rows:
            if candidate > r.strike:
                payout += (candidate - r.strike) * r.ce_oi
            if candidate < r.strike:
                payout += (r.strike - candidate) * r.pe_oi
        if lowest_payout is None or payout < lowest_payout:
            lowest_payout = payout
            best_strike = candidate

    return best_strike


def atm_strike(rows: list[StrikeRow], spot_price: float) -> float:
    if not rows:
        return spot_price
    return min((r.strike for r in rows), key=lambda s: abs(s - spot_price))


# --- OI build-up classification (per strike, price vs. OI change) ---------
# Long Build Up:    price up   + OI up    -> fresh longs being added
# Short Build Up:   price down + OI up    -> fresh shorts being added
# Short Covering:   price up   + OI down  -> shorts closing out
# Long Unwinding:   price down + OI down  -> longs closing out


def classify_oi_buildup(price_change: float, oi_change: int) -> str:
    if price_change > 0 and oi_change > 0:
        return "LONG_BUILD_UP"
    if price_change < 0 and oi_change > 0:
        return "SHORT_BUILD_UP"
    if price_change > 0 and oi_change < 0:
        return "SHORT_COVERING"
    if price_change < 0 and oi_change < 0:
        return "LONG_UNWINDING"
    return "NEUTRAL"


def writing_activity(rows: list[StrikeRow], near_strikes: int = 5, spot_price: float | None = None) -> dict:
    """Classify CE/PE writing pressure around the ATM strikes.

    Writing = OI increasing while premium falls (sellers in control).
    Returns aggregate CE/PE OI-change near the money plus a verdict used by
    the Trend Detection Engine.
    """
    subset = rows
    if spot_price is not None and len(rows) > near_strikes:
        centered = sorted(rows, key=lambda r: abs(r.strike - spot_price))
        subset = centered[:near_strikes]

    ce_oi_change = sum(r.ce_oi_change for r in subset)
    pe_oi_change = sum(r.pe_oi_change for r in subset)

    ce_writing = ce_oi_change > 0 and ce_oi_change > pe_oi_change
    pe_writing = pe_oi_change > 0 and pe_oi_change > ce_oi_change

    if ce_writing:
        verdict = "CE_WRITING"
    elif pe_writing:
        verdict = "PE_WRITING"
    else:
        verdict = "NEUTRAL"

    return {
        "ce_oi_change_near_atm": ce_oi_change,
        "pe_oi_change_near_atm": pe_oi_change,
        "ce_writing": ce_writing,
        "pe_writing": pe_writing,
        "verdict": verdict,
    }


# Directional read per side. CE build-up is bullish (fresh call buying),
# PE build-up is bearish (fresh put buying) - puts and calls point opposite
# ways for the *underlying's* direction even though the classification
# itself (comparing an instrument's own price move to its own OI move) is
# symmetric.
_CE_BUILDUP_BIAS = {
    "LONG_BUILD_UP": 1.0,
    "SHORT_COVERING": 0.5,
    "SHORT_BUILD_UP": -1.0,
    "LONG_UNWINDING": -0.5,
    "NEUTRAL": 0.0,
}
_PE_BUILDUP_BIAS = {
    "LONG_BUILD_UP": -1.0,
    "SHORT_COVERING": -0.5,
    "SHORT_BUILD_UP": 1.0,
    "LONG_UNWINDING": 0.5,
    "NEUTRAL": 0.0,
}


def atm_oi_buildup_bias(
    chain: list[StrikeRow], previous_chain: list[StrikeRow] | None, spot_price: float
) -> float:
    """Net directional bias in [-1, 1] from classifying the ATM strike's
    own CE and PE build-up (`classify_oi_buildup`, price change of the
    *option's own premium* vs. its own OI change) - a real per-instrument
    read, not the crude "which side has more aggregate OI change" of
    `writing_activity`. Needs a previous poll/bar's chain to know premium
    change; returns 0.0 (no opinion) if that isn't available yet."""
    if not chain or previous_chain is None:
        return 0.0

    strike = atm_strike(chain, spot_price)
    current = next((r for r in chain if r.strike == strike), None)
    previous = next((r for r in previous_chain if r.strike == strike), None)
    if current is None or previous is None:
        return 0.0

    biases = []
    if current.ce_ltp > 0 and previous.ce_ltp > 0:
        ce_state = classify_oi_buildup(current.ce_ltp - previous.ce_ltp, current.ce_oi_change)
        biases.append(_CE_BUILDUP_BIAS[ce_state])
    if current.pe_ltp > 0 and previous.pe_ltp > 0:
        pe_state = classify_oi_buildup(current.pe_ltp - previous.pe_ltp, current.pe_oi_change)
        biases.append(_PE_BUILDUP_BIAS[pe_state])

    return sum(biases) / len(biases) if biases else 0.0


def pcr_bias(pcr: float, bullish_above: float = 1.2, bearish_below: float = 0.8) -> str:
    """Conventional PCR read: high PCR (more puts written) => bullish, and
    vice versa - contrarian to raw put/call volume."""
    if pcr >= bullish_above:
        return "BULLISH"
    if pcr <= bearish_below:
        return "BEARISH"
    return "NEUTRAL"
