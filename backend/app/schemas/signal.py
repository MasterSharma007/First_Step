from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.trade_signal import SignalType


class SignalScoreBreakdown(BaseModel):
    trend_score: float
    options_score: float
    volume_score: float
    volatility_score: float
    confidence_score: float
    verdict: str  # STRONG_CE, NO_TRADE, STRONG_PE


class TradeSignalOut(BaseModel):
    signal_id: UUID
    entry_time: datetime
    underlying: str
    strike: float | None = None
    expiry: date | None = None
    signal_type: SignalType
    entry_price: float
    stop_loss: float | None = None
    target: float | None = None
    confidence_score: float
    reasons: dict | None = None

    class Config:
        from_attributes = True
