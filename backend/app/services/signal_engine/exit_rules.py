"""Exit Rules (SRD §7): target, stop loss, and trailing stop loss."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ExitLevels:
    stop_loss: float
    target: float


def compute_exit_levels(
    entry_price: float,
    stop_loss_points: float,
    risk_reward_ratio: float = 2.0,
) -> ExitLevels:
    """Risk:Reward target/SL, e.g. risk=20pts, RR=2 -> target=40pts (SRD §7)."""
    stop_loss = entry_price - stop_loss_points
    target = entry_price + stop_loss_points * risk_reward_ratio
    return ExitLevels(stop_loss=round(stop_loss, 2), target=round(target, 2))


ATM_DELTA_APPROX = 0.5  # rough near-ATM option delta - premium moves roughly
# half as many points as the underlying. Good enough for a target cap since
# this system only ever trades the ATM strike (see live/snapshot.py); not a
# real Greek (would need IV/time-to-expiry for that).


def sr_capped_target(
    entry_price: float,
    rr_target: float,
    spot_price: float,
    sr_level: float,
    option_type: str,
) -> float:
    """Caps the flat risk:reward target at whatever the option premium would
    be if spot reached the nearest resistance (for a CE) or support (for a
    PE), so the plan never expects a bigger spot move than the level in
    front of it. If spot has already broken through `sr_level` there's no
    ceiling left to cap against, so the flat RR target is used unchanged.
    """
    spot_headroom = (sr_level - spot_price) if option_type == "CE" else (spot_price - sr_level)
    if spot_headroom <= 0:
        return rr_target

    sr_target = round(entry_price + spot_headroom * ATM_DELTA_APPROX, 2)
    return min(rr_target, sr_target)


def stop_loss_from_previous_candle(previous_candle_low: float, buffer_points: float = 0.0) -> float:
    return round(previous_candle_low - buffer_points, 2)


def stop_loss_from_atr(entry_price: float, atr_value: float, multiplier: float = 1.5) -> float:
    return round(entry_price - atr_value * multiplier, 2)


def stop_loss_from_percentage(entry_price: float, pct: float = 0.15) -> float:
    return round(entry_price * (1 - pct), 2)


def trail_stop_loss(
    entry_price: float,
    current_price: float,
    current_stop_loss: float,
    trail_step_points: float = 10.0,
) -> float:
    """Move SL to cost once in profit, then trail every `trail_step_points`
    beyond that (SRD §7).

    Tried requiring a full trail_step of profit before engaging (theory:
    instant breakeven-snap on noisy 5m data turns routine wiggle into
    realized small losses). Backtest evidence said otherwise: win rate
    improved (17.78% -> 26.67% on the same range) but net P&L got *worse*
    (-27,878 -> -57,771) and profit factor dropped (0.67 -> 0.52) - the
    early snap was cutting losers small; removing it let them develop into
    bigger losses before the wider stop caught them. Reverted. Recorded
    here so the same "improvement" doesn't get re-tried without re-testing
    against real data first.
    """
    if current_price <= entry_price:
        return current_stop_loss

    current_stop_loss = max(current_stop_loss, entry_price)

    profit_points = current_price - entry_price
    trail_increments = int(profit_points // trail_step_points)
    candidate_sl = entry_price + max(trail_increments - 1, 0) * trail_step_points

    return round(max(current_stop_loss, candidate_sl), 2)
