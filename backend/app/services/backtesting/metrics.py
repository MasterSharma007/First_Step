"""Backtest performance metrics (SRD §2, §9): win rate, profit factor,
drawdown, Sharpe ratio."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class TradeResult:
    pnl: float


@dataclass
class BacktestMetrics:
    total_trades: int
    win_rate: float
    profit_factor: float
    max_drawdown: float
    sharpe_ratio: float
    net_pnl: float


def compute_metrics(trades: list[TradeResult], risk_free_rate: float = 0.0) -> BacktestMetrics:
    if not trades:
        return BacktestMetrics(0, 0.0, 0.0, 0.0, 0.0, 0.0)

    pnls = np.array([t.pnl for t in trades], dtype=float)
    wins = pnls[pnls > 0]
    losses = pnls[pnls < 0]

    total_trades = len(pnls)
    win_rate = round(len(wins) / total_trades * 100, 2)

    gross_profit = wins.sum()
    gross_loss = abs(losses.sum())
    profit_factor = round(float(gross_profit / gross_loss), 2) if gross_loss > 0 else float("inf")

    equity_curve = np.cumsum(pnls)
    running_max = np.maximum.accumulate(equity_curve)
    drawdowns = running_max - equity_curve
    max_drawdown = round(float(drawdowns.max()), 2)

    returns_std = pnls.std(ddof=1) if total_trades > 1 else 0.0
    sharpe_ratio = (
        round(float((pnls.mean() - risk_free_rate) / returns_std * np.sqrt(total_trades)), 4)
        if returns_std > 0
        else 0.0
    )

    return BacktestMetrics(
        total_trades=total_trades,
        win_rate=win_rate,
        profit_factor=profit_factor,
        max_drawdown=max_drawdown,
        sharpe_ratio=sharpe_ratio,
        net_pnl=round(float(pnls.sum()), 2),
    )
