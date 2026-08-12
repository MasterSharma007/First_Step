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
from app.services.option_chain.analyzer import StrikeRow, atm_strike
from app.services.signal_engine.exit_rules import compute_exit_levels, stop_loss_from_percentage
from app.services.signal_engine.scorer import SignalEngine

MIN_WARMUP_BARS = 50  # EMA50 needs history before it's meaningful


@dataclass
class BacktestTrade:
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    signal_type: str
    strike: float
    option_type: str
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
        stop_loss_pct: float = 0.15,
        risk_reward_ratio: float = 2.0,
        lot_size: int = 35,
    ):
        self.signal_engine = signal_engine or SignalEngine()
        self.stop_loss_pct = stop_loss_pct
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
        caller's responsibility - keep this loop pure).

        Trades are entered/exited at the actual option premium (looked up
        from `option_chain_by_time` for the ATM strike's CE/PE side), not
        the spot index level - a fixed points-based stop on the *spot*
        while pricing P&L off it produces a wildly mismatched stop
        distance (tens of index points vs. hundreds of premium points),
        which is nonsensical and mostly just noise-stops. Since only a
        point-in-time premium snapshot is available per bar (no option
        intrabar high/low in this dataset), exits check the snapshot LTP
        rather than bar high/low.

        Re-entry into the *same* signal that was just stopped out/targeted
        is blocked until the Signal Engine actually says something
        different (NO_TRADE, or a flip to the opposite side) - otherwise a
        persistent trend reopens the identical trade every single bar it
        stays in force, and the Signal Engine emitting "still CE_ENTRY" for
        the 40th consecutive bar isn't 40 new signals. A genuine reversal
        (CE closed -> PE now firing) is a distinct event and isn't blocked.
        """
        trades: list[BacktestTrade] = []
        open_trade: dict | None = None
        blocked_signal_type: str | None = None

        for i in range(MIN_WARMUP_BARS, len(spot_df)):
            window = spot_df.iloc[: i + 1]
            ts = spot_df.index[i]
            bar = spot_df.iloc[i]
            chain = option_chain_by_time.get(ts, [])

            if open_trade is not None:
                current_price = self._current_premium(chain, open_trade["strike"], open_trade["option_type"])
                if current_price is None:
                    continue  # no snapshot for this strike at this bar - hold and re-check next bar

                exit_price, exit_reason = self._check_exit(current_price, open_trade)
                if exit_price is not None:
                    pnl = (exit_price - open_trade["entry_price"]) * self.lot_size
                    trades.append(
                        BacktestTrade(
                            entry_time=open_trade["entry_time"],
                            exit_time=ts,
                            signal_type=open_trade["signal_type"],
                            strike=open_trade["strike"],
                            option_type=open_trade["option_type"],
                            entry_price=open_trade["entry_price"],
                            exit_price=exit_price,
                            stop_loss=open_trade["stop_loss"],
                            target=open_trade["target"],
                            pnl=pnl,
                            exit_reason=exit_reason,
                        )
                    )
                    blocked_signal_type = open_trade["signal_type"]
                    open_trade = None
                continue

            vix = india_vix_by_time.get(ts, 15.0)
            if not chain:
                continue

            decision = self.signal_engine.evaluate(window, chain, float(bar["close"]), vix)

            if decision.signal_type == blocked_signal_type:
                continue  # identical signal that just got stopped/targeted out - wait for it to change
            blocked_signal_type = None
            if decision.signal_type == "NO_TRADE":
                continue

            strike = atm_strike(chain, float(bar["close"]))
            option_type = "CE" if decision.signal_type == "CE_ENTRY" else "PE"
            entry_price = self._current_premium(chain, strike, option_type)
            if not entry_price:
                continue  # no valid premium to trade at this bar

            stop_loss = stop_loss_from_percentage(entry_price, self.stop_loss_pct)
            levels = compute_exit_levels(entry_price, entry_price - stop_loss, self.risk_reward_ratio)
            open_trade = {
                "entry_time": ts,
                "entry_price": entry_price,
                "signal_type": decision.signal_type,
                "strike": strike,
                "option_type": option_type,
                "stop_loss": levels.stop_loss,
                "target": levels.target,
            }

        metrics = compute_metrics([TradeResult(pnl=t.pnl) for t in trades])
        return BacktestRun(trades=trades, metrics=metrics)

    @staticmethod
    def _current_premium(chain: list[StrikeRow], strike: float, option_type: str) -> float | None:
        row = next((r for r in chain if r.strike == strike), None)
        if row is None:
            return None
        premium = row.ce_ltp if option_type == "CE" else row.pe_ltp
        return premium if premium > 0 else None

    @staticmethod
    def _check_exit(current_price: float, open_trade: dict) -> tuple[float | None, str]:
        if current_price <= open_trade["stop_loss"]:
            return current_price, "STOP_LOSS"
        if current_price >= open_trade["target"]:
            return current_price, "TARGET"
        return None, ""
