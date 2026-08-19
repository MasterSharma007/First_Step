"""Estimated round-trip transaction costs for one options trade.

`trade_execution.charges` used to sit at its model default (0) forever -
nothing ever computed a real figure, so every P&L number in the app
(including the reports) was gross, ignoring the brokerage/STT/exchange
fees that apply to every entry and exit regardless of whether the trade
won or lost. Rates below model a typical discount-broker (Zerodha/Kite)
F&O options bill; all are configurable via `Settings` since exchange and
regulatory rates change over time.
"""

from __future__ import annotations

from app.core.config import Settings


def estimate_round_trip_charges(entry_price: float, exit_price: float, quantity: int, settings: Settings) -> float:
    buy_turnover = entry_price * quantity
    sell_turnover = exit_price * quantity

    brokerage = settings.brokerage_per_order * 2  # one order to enter, one to exit
    stt = sell_turnover * settings.stt_pct_on_sell
    exchange_txn = (buy_turnover + sell_turnover) * settings.exchange_txn_pct
    stamp_duty = buy_turnover * settings.stamp_duty_pct
    gst = (brokerage + exchange_txn) * settings.gst_pct

    return round(brokerage + stt + exchange_txn + stamp_duty + gst, 2)
