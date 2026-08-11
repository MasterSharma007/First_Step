"""Smoke tests for the core, DB-free engines: option chain analysis, signal
scoring, exit rules, risk management, and the backtest loop."""

import numpy as np
import pandas as pd
import pytest

from app.services.backtesting.engine import BacktestEngine
from app.services.option_chain.analyzer import StrikeRow, max_pain, put_call_ratio, writing_activity
from app.services.risk_management.manager import RiskLimits, RiskManager
from app.services.signal_engine.exit_rules import compute_exit_levels, trail_stop_loss
from app.services.signal_engine.scorer import SignalEngine


@pytest.fixture
def strike_rows() -> list[StrikeRow]:
    return [
        StrikeRow(strike=48000, ce_oi=100000, ce_oi_change=-8000, pe_oi=140000, pe_oi_change=15000, ce_ltp=250, pe_ltp=120),
        StrikeRow(strike=48100, ce_oi=90000, ce_oi_change=-5000, pe_oi=130000, pe_oi_change=12000, ce_ltp=200, pe_ltp=150),
        StrikeRow(strike=48200, ce_oi=80000, ce_oi_change=-4000, pe_oi=110000, pe_oi_change=9000, ce_ltp=160, pe_ltp=180),
    ]


@pytest.fixture
def uptrend_df() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    n = 120
    base = np.linspace(48000, 48800, n) + rng.normal(0, 15, n)
    df = pd.DataFrame(
        {
            "open": base,
            "high": base + rng.uniform(5, 25, n),
            "low": base - rng.uniform(5, 25, n),
            "close": base + rng.normal(0, 5, n),
            "volume": rng.integers(1000, 5000, n),
        },
        index=pd.date_range("2026-01-01 09:15", periods=n, freq="5min"),
    )
    df.loc[df.index[-1], "volume"] = 20000
    return df


def test_put_call_ratio(strike_rows):
    assert put_call_ratio(strike_rows) == pytest.approx(1.407, abs=1e-3)


def test_max_pain_is_a_listed_strike(strike_rows):
    assert max_pain(strike_rows) in {r.strike for r in strike_rows}


def test_writing_activity_detects_pe_writing(strike_rows):
    result = writing_activity(strike_rows, spot_price=48100)
    assert result["verdict"] == "PE_WRITING"
    assert result["pe_writing"] is True


def test_signal_engine_produces_ce_entry_on_bullish_setup(uptrend_df, strike_rows):
    engine = SignalEngine()
    decision = engine.evaluate(uptrend_df, strike_rows, spot_price=float(uptrend_df["close"].iloc[-1]), india_vix=13.5)
    assert decision.signal_type == "CE_ENTRY"
    assert 0 <= decision.confidence_score <= 100


def test_exit_levels_respect_risk_reward():
    levels = compute_exit_levels(entry_price=250, stop_loss_points=20, risk_reward_ratio=2.0)
    assert levels.stop_loss == 230
    assert levels.target == 290.0


def test_trailing_stop_never_moves_backward():
    sl = trail_stop_loss(entry_price=250, current_price=285, current_stop_loss=230)
    assert sl >= 250


def test_risk_manager_blocks_after_daily_loss_limit():
    rm = RiskManager(RiskLimits(max_daily_loss=1000, max_trade_loss=2000, max_open_positions=2, capital=100000))
    result = rm.can_open_new_trade(current_daily_pnl=-1000, open_positions=0)
    assert result.allowed is False


def test_backtest_engine_runs_and_produces_metrics(uptrend_df, strike_rows):
    engine = BacktestEngine()
    option_chain_by_time = {ts: strike_rows for ts in uptrend_df.index}
    vix_by_time = {ts: 13.5 for ts in uptrend_df.index}
    run = engine.run(uptrend_df, option_chain_by_time, vix_by_time)
    assert run.metrics.total_trades == len(run.trades)
    assert run.metrics.total_trades > 0
