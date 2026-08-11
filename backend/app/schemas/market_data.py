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
