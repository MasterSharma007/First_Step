"""Backtesting Engine (SRD §2, §9).

Replays historical spot + option-chain data bar-by-bar through the same
`SignalEngine` and exit-rule functions used live, so backtest and live
behavior can't silently diverge. Deliberately simple (single position at a
time, next-bar fill) - extend as strategies get more sophisticated.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from app.services.backtesting.metrics import BacktestMetrics, TradeResult, compute_metrics
from app.services.option_chain.analyzer import StrikeRow
from app.services.signal_engine.exit_rules import compute_exit_levels
from app.services.signal_engine.scorer import SignalEngine

MIN_WARMUP_BARS = 50  # EMA50 needs history before it's meaningful


@dataclass
class BacktestTrade:
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    signal_type: str
    entry_price: float
    exit_price: float
    stop_loss: float
    target: float
    pnl: float
    exit_reason: str


@dataclass
class BacktestRun:
    trades: list[BacktestTrade]
    metrics: BacktestMetrics


class BacktestEngine:
    def __init__(
        self,
        signal_engine: SignalEngine | None = None,
        stop_loss_points: float = 20.0,
        risk_reward_ratio: float = 2.0,
        lot_size: int = 35,
    ):
        self.signal_engine = signal_engine or SignalEngine()
        self.stop_loss_points = stop_loss_points
        self.risk_reward_ratio = risk_reward_ratio
        self.lot_size = lot_size

    def run(
        self,
        spot_df: pd.DataFrame,
        option_chain_by_time: dict[pd.Timestamp, list[StrikeRow]],
        india_vix_by_time: dict[pd.Timestamp, float],
    ) -> BacktestRun:
        """`spot_df` indexed by datetime with open/high/low/close/volume.
        `option_chain_by_time`/`india_vix_by_time` keyed by the same
        timestamps as `spot_df.index` (nearest-available lookups are the
        caller's responsibility - keep this loop pure)."""
        trades: list[BacktestTrade] = []
        open_trade: dict | None = None

        for i in range(MIN_WARMUP_BARS, len(spot_df)):
            window = spot_df.iloc[: i + 1]
            ts = spot_df.index[i]
            bar = spot_df.iloc[i]

            if open_trade is not None:
                exit_price, exit_reason = self._check_exit(bar, open_trade)
                if exit_price is not None:
                    pnl = (exit_price - open_trade["entry_price"]) * self.lot_size
                    trades.append(
                        BacktestTrade(
                            entry_time=open_trade["entry_time"],
                            exit_time=ts,
                            signal_type=open_trade["signal_type"],
                            entry_price=open_trade["entry_price"],
                            exit_price=exit_price,
                            stop_loss=open_trade["stop_loss"],
                            target=open_trade["target"],
                            pnl=pnl,
                            exit_reason=exit_reason,
                        )
                    )
                    open_trade = None
                continue

            chain = option_chain_by_time.get(ts, [])
            vix = india_vix_by_time.get(ts, 15.0)
            if not chain:
                continue

            decision = self.signal_engine.evaluate(window, chain, float(bar["close"]), vix)
            if decision.signal_type == "NO_TRADE":
                continue

            levels = compute_exit_levels(float(bar["close"]), self.stop_loss_points, self.risk_reward_ratio)
            open_trade = {
                "entry_time": ts,
                "entry_price": float(bar["close"]),
                "signal_type": decision.signal_type,
                "stop_loss": levels.stop_loss,
                "target": levels.target,
            }

        metrics = compute_metrics([TradeResult(pnl=t.pnl) for t in trades])
        return BacktestRun(trades=trades, metrics=metrics)

    @staticmethod
    def _check_exit(bar: pd.Series, open_trade: dict) -> tuple[float | None, str]:
        if bar["low"] <= open_trade["stop_loss"]:
            return open_trade["stop_loss"], "STOP_LOSS"
        if bar["high"] >= open_trade["target"]:
            return open_trade["target"], "TARGET"
        return None, ""
