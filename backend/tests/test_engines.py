"""Smoke tests for the core, DB-free engines: option chain analysis, signal
scoring, exit rules, risk management, and the backtest loop."""

import numpy as np
import pandas as pd
import pytest

from app.services.backtesting.engine import BacktestEngine
from app.services.market_analysis.indicators import vwap
from app.services.option_chain.analyzer import (
    StrikeRow,
    atm_oi_buildup_bias,
    classify_oi_buildup,
    max_pain,
    put_call_ratio,
    writing_activity,
)
from app.services.risk_management.manager import RiskLimits, RiskManager
from app.services.signal_engine.exit_rules import (
    compute_exit_levels,
    sr_capped_target,
    trail_stop_loss,
)
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


def test_classify_oi_buildup_four_states():
    assert classify_oi_buildup(price_change=5, oi_change=100) == "LONG_BUILD_UP"
    assert classify_oi_buildup(price_change=-5, oi_change=100) == "SHORT_BUILD_UP"
    assert classify_oi_buildup(price_change=5, oi_change=-100) == "SHORT_COVERING"
    assert classify_oi_buildup(price_change=-5, oi_change=-100) == "LONG_UNWINDING"
    assert classify_oi_buildup(price_change=0, oi_change=0) == "NEUTRAL"


def test_atm_oi_buildup_bias_no_previous_chain_is_neutral(strike_rows):
    assert atm_oi_buildup_bias(strike_rows, None, spot_price=48000) == 0.0


def test_atm_oi_buildup_bias_bullish_on_fresh_call_buying():
    # ATM strike 48000: CE premium rose (250->260) with OI up -> LONG_BUILD_UP (bullish).
    # PE premium fell (120->110) with OI down -> LONG_UNWINDING (mildly bullish for PE too).
    previous = [StrikeRow(strike=48000, ce_oi=90000, ce_ltp=250, pe_oi=145000, pe_ltp=120)]
    current = [StrikeRow(strike=48000, ce_oi=100000, ce_oi_change=10000, ce_ltp=260, pe_oi=140000, pe_oi_change=-5000, pe_ltp=110)]
    bias = atm_oi_buildup_bias(current, previous, spot_price=48000)
    assert bias > 0


def test_atm_oi_buildup_bias_bearish_on_fresh_put_buying():
    # PE premium rose with OI up -> LONG_BUILD_UP on puts (bearish).
    previous = [StrikeRow(strike=48000, ce_oi=100000, ce_ltp=250, pe_oi=130000, pe_ltp=120)]
    current = [StrikeRow(strike=48000, ce_oi=100000, ce_oi_change=0, ce_ltp=250, pe_oi=145000, pe_oi_change=15000, pe_ltp=140)]
    bias = atm_oi_buildup_bias(current, previous, spot_price=48000)
    assert bias < 0


def test_vwap_handles_zero_volume_index_data():
    # NIFTY BANK spot is an index - Kite's historical API always reports
    # volume=0 for it, which used to blow up VWAP's divide-by-zero guard
    # (NaN propagated into every downstream `>` comparison and crashed).
    df = pd.DataFrame(
        {
            "high": [100.0, 101.0, 102.0],
            "low": [98.0, 99.0, 100.0],
            "close": [99.0, 100.0, 101.0],
            "volume": [0, 0, 0],
        }
    )
    result = vwap(df)
    assert result.notna().all()
    assert (result > 0).all()


def test_signal_engine_handles_zero_volume_index_data(strike_rows):
    df = pd.DataFrame(
        {
            "open": np.linspace(48000, 48500, 60),
            "high": np.linspace(48010, 48510, 60),
            "low": np.linspace(47990, 48490, 60),
            "close": np.linspace(48005, 48505, 60),
            "volume": 0,
        },
        index=pd.date_range("2026-01-01 09:15", periods=60, freq="5min"),
    )
    engine = SignalEngine()
    decision = engine.evaluate(df, strike_rows, spot_price=float(df["close"].iloc[-1]), india_vix=13.5)
    assert decision.signal_type in {"CE_ENTRY", "PE_ENTRY", "NO_TRADE"}


def test_signal_engine_produces_ce_entry_on_bullish_setup(uptrend_df, strike_rows):
    engine = SignalEngine()
    decision = engine.evaluate(uptrend_df, strike_rows, spot_price=float(uptrend_df["close"].iloc[-1]), india_vix=13.5)
    assert decision.signal_type == "CE_ENTRY"
    assert 0 <= decision.confidence_score <= 100


def test_exit_levels_respect_risk_reward():
    levels = compute_exit_levels(entry_price=250, stop_loss_points=20, risk_reward_ratio=2.0)
    assert levels.stop_loss == 230
    assert levels.target == 290.0


def test_sr_capped_target_caps_ce_target_at_resistance():
    # Flat RR target (845.59) is far past what spot reaching resistance
    # would imply for the premium (~0.5 delta approximation).
    capped = sr_capped_target(entry_price=650.45, rr_target=845.59, spot_price=57500, sr_level=57560, option_type="CE")
    assert capped == pytest.approx(650.45 + (57560 - 57500) * 0.5)
    assert capped < 845.59


def test_sr_capped_target_caps_pe_target_at_support():
    capped = sr_capped_target(entry_price=400, rr_target=480, spot_price=57500, sr_level=57440, option_type="PE")
    assert capped == pytest.approx(400 + (57500 - 57440) * 0.5)
    assert capped < 480


def test_sr_capped_target_falls_back_to_rr_target_when_level_already_broken():
    # Spot already past resistance - no ceiling left to cap against.
    capped = sr_capped_target(entry_price=650.45, rr_target=845.59, spot_price=57600, sr_level=57560, option_type="CE")
    assert capped == 845.59


def test_sr_capped_target_never_exceeds_rr_target_even_with_huge_headroom():
    capped = sr_capped_target(entry_price=650.45, rr_target=845.59, spot_price=57500, sr_level=60000, option_type="CE")
    assert capped == 845.59


def test_trailing_stop_never_moves_backward():
    sl = trail_stop_loss(entry_price=250, current_price=285, current_stop_loss=230)
    assert sl >= 250


def test_risk_manager_blocks_after_daily_loss_limit():
    rm = RiskManager(RiskLimits(max_daily_loss=1000, max_trade_loss=2000, max_open_positions=2, capital=100000))
    result = rm.can_open_new_trade(current_daily_pnl=-1000, open_positions=0)
    assert result.allowed is False


def test_trailing_stop_locks_in_gains_but_target_still_caps():
    # Target still caps the trade (see engine.py docstring for why - daily
    # option-snapshot granularity makes an uncapped trailing exit unsafe).
    open_trade = {"entry_price": 250.0, "stop_loss": 212.5, "original_stop_loss": 212.5, "target": 325.0}
    trail_step = 250.0 * 0.05
    open_trade["stop_loss"] = trail_stop_loss(250.0, 300.0, open_trade["stop_loss"], trail_step)
    assert open_trade["stop_loss"] > open_trade["original_stop_loss"]

    exit_price, exit_reason = BacktestEngine._check_exit(open_trade["target"], open_trade)
    assert exit_price == open_trade["target"]
    assert exit_reason == "TARGET"

    # But a pullback to the trailed stop before reaching target exits early,
    # locking in more than the original stop-loss would have.
    exit_price, exit_reason = BacktestEngine._check_exit(open_trade["stop_loss"], open_trade)
    assert exit_price == open_trade["stop_loss"]
    assert exit_reason == "TRAILING_STOP"


def test_backtest_engine_runs_and_produces_metrics(uptrend_df, strike_rows):
    engine = BacktestEngine()
    base_close = uptrend_df["close"].iloc[0]
    # A static chain never moves the option premium, so nothing would ever
    # hit stop/target - track the 48000 CE premium against the underlying's
    # move (a rough stand-in for delta) so the trade can actually resolve.
    option_chain_by_time = {}
    for ts, close in uptrend_df["close"].items():
        moved = [StrikeRow(**r.__dict__) for r in strike_rows]
        for row, original in zip(moved, strike_rows, strict=True):
            row.ce_ltp = original.ce_ltp + (close - base_close) * 0.5
        option_chain_by_time[ts] = moved
    vix_by_time = {ts: 13.5 for ts in uptrend_df.index}

    run = engine.run(uptrend_df, option_chain_by_time, vix_by_time)
    assert run.metrics.total_trades == len(run.trades)
    assert run.metrics.total_trades > 0
