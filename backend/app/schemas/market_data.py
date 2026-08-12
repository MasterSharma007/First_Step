from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class SpotOHLCOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    symbol: str
    interval: str
    datetime_: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


class OptionOHLCOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    underlying: str
    strike: float
    expiry: date
    option_type: str
    interval: str
    datetime_: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    oi: int
    oi_change: int
    iv: float | None = None


class TickOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    timestamp: datetime
    symbol: str
    price: float
    volume: int
    bid: float | None = None
    ask: float | None = None
    oi: int | None = None


class IndiaVixOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    interval: str
    datetime_: datetime
    value: float


class TrendOut(BaseModel):
    symbol: str
    interval: str
    as_of: datetime
    direction: str  # BULLISH, BEARISH, NEUTRAL
    reasons: list[str]
    support: float
    resistance: float
    current_price: float


class TimeframeReadingOut(BaseModel):
    timeframe: str  # 15m, 1h, 1d, 1w, 1M
    bars_available: int
    insufficient_data: bool
    support: float | None = None
    resistance: float | None = None
    direction: str | None = None  # BULLISH, BEARISH, NEUTRAL - None if insufficient_data
    reasons: list[str] | None = None


class MultiTimeframeOut(BaseModel):
    symbol: str
    current_price: float
    timeframes: list[TimeframeReadingOut]


class CandleBreakOut(BaseModel):
    direction: str | None  # "UP", "DOWN", or None
    reference_high: float
    reference_low: float
    reference_time: str


class SwingPointOut(BaseModel):
    kind: str  # HH, LH, HL, LL
    price: float
    time: str


class PriceActionReadingOut(BaseModel):
    timeframe: str  # 5m, 15m
    current_price: float
    candle_break: CandleBreakOut | None = None
    sr_break: str | None = None  # "SUPPORT_BREAK", "RESISTANCE_BREAK", or None
    support: float | None = None
    resistance: float | None = None
    swing_points: list[SwingPointOut] = []
    structure: str | None = None  # kind of the most recent confirmed swing point


class PriceActionOut(BaseModel):
    symbol: str
    current_price: float
    timeframes: list[PriceActionReadingOut]
