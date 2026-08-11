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
    beyond that (SRD §7)."""
    if current_price <= entry_price:
        return current_stop_loss

    current_stop_loss = max(current_stop_loss, entry_price)

    profit_points = current_price - entry_price
    trail_increments = int(profit_points // trail_step_points)
    candidate_sl = entry_price + max(trail_increments - 1, 0) * trail_step_points

    return round(max(current_stop_loss, candidate_sl), 2)
