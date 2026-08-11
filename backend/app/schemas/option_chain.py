from datetime import date, datetime

from pydantic import BaseModel


class OptionChainRow(BaseModel):
    strike: float
    ce_ltp: float | None = None
    ce_oi: int = 0
    ce_oi_change: int = 0
    ce_volume: int = 0
    ce_iv: float | None = None
    pe_ltp: float | None = None
    pe_oi: int = 0
    pe_oi_change: int = 0
    pe_volume: int = 0
    pe_iv: float | None = None


class OptionChainAnalysis(BaseModel):
    underlying: str
    expiry: date
    as_of: datetime
    spot_price: float
    atm_strike: float
    pcr: float
    max_pain: float
    total_ce_oi: int
    total_pe_oi: int
    rows: list[OptionChainRow]
    oi_signal: str  # e.g. CE_WRITING, PE_WRITING, SHORT_COVERING, LONG_BUILD_UP, ...
