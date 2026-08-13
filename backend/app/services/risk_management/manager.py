"""Risk Management Engine (SRD §2).

Stateless checks the Signal/Trading engines must pass before opening or
sizing a new position. Callers own persistence of the running totals
(daily P&L, open position count); this module only evaluates policy.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RiskLimits:
    max_daily_loss: float
    max_trade_loss: float
    max_open_positions: int
    capital: float
    risk_per_trade_pct: float = 1.0  # % of capital risked per trade
    min_reward_risk_ratio: float = 0.5  # reject trades offering less reward than this multiple of their risk


@dataclass
class RiskCheckResult:
    allowed: bool
    reason: str = ""


class RiskManager:
    def __init__(self, limits: RiskLimits):
        self.limits = limits

    def can_open_new_trade(self, current_daily_pnl: float, open_positions: int) -> RiskCheckResult:
        if current_daily_pnl <= -abs(self.limits.max_daily_loss):
            return RiskCheckResult(False, "Maximum daily loss reached")
        if open_positions >= self.limits.max_open_positions:
            return RiskCheckResult(False, "Maximum open positions reached")
        return RiskCheckResult(True)

    def validate_trade_risk(
        self, entry_price: float, stop_loss: float, lot_size: int, target: float | None = None
    ) -> RiskCheckResult:
        risk_per_lot = abs(entry_price - stop_loss) * lot_size
        if risk_per_lot > self.limits.max_trade_loss:
            return RiskCheckResult(
                False,
                f"Trade risk {risk_per_lot:.2f} exceeds max trade loss {self.limits.max_trade_loss:.2f}",
            )

        if target is not None:
            risk_points = abs(entry_price - stop_loss)
            reward_points = abs(target - entry_price)
            if risk_points > 0 and reward_points / risk_points < self.limits.min_reward_risk_ratio:
                return RiskCheckResult(
                    False,
                    f"Reward:risk {reward_points / risk_points:.2f} below minimum "
                    f"{self.limits.min_reward_risk_ratio:.2f} (risk {risk_points:.2f}, reward {reward_points:.2f})",
                )

        return RiskCheckResult(True)

    def position_size(self, entry_price: float, stop_loss: float, lot_size: int) -> int:
        """Number of lots sized to `risk_per_trade_pct` of capital, capped
        by `max_trade_loss` (SRD §2 Position Sizing / Capital Allocation)."""
        risk_amount = min(
            self.limits.capital * (self.limits.risk_per_trade_pct / 100),
            self.limits.max_trade_loss,
        )
        risk_per_lot = abs(entry_price - stop_loss) * lot_size
        if risk_per_lot <= 0:
            return 0
        return max(int(risk_amount // risk_per_lot), 0)
