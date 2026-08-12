from datetime import date, datetime

from pydantic import BaseModel


class SignalSuggestion(BaseModel):
    signal_type: str  # CE_ENTRY, PE_ENTRY, NO_TRADE
    verdict: str
    confidence_score: float
    strike: float | None = None
    option_type: str | None = None
    entry_price: float | None = None
    stop_loss: float | None = None
    target: float | None = None
    reasons: dict


class OpenPositionOut(BaseModel):
    order_id: str
    symbol: str
    option_type: str
    quantity: int
    entry_price: float
    current_price: float | None = None
    stop_loss: float | None = None
    target: float | None = None
    unrealized_pnl: float | None = None
    entry_time: datetime


class LiveStatusOut(BaseModel):
    as_of: datetime
    spot_price: float
    trend_direction: str
    trend_reasons: list[str]
    support: float
    resistance: float
    expiry: date | None = None
    atm_strike: float | None = None
    pcr: float | None = None
    max_pain: float | None = None
    oi_signal: str | None = None
    india_vix: float
    signal: SignalSuggestion
    open_positions: list[OpenPositionOut]
    today_realized_pnl: float
    today_trade_count: int
    live_loop_enabled: bool
