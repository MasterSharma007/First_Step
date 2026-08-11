from datetime import date
from uuid import UUID

from pydantic import BaseModel


class BacktestRequest(BaseModel):
    strategy_name: str = "default"
    start_date: date
    end_date: date
    underlying: str = "NIFTY BANK"
    initial_capital: float = 100000.0
    params: dict = {}


class BacktestResultOut(BaseModel):
    run_id: UUID
    strategy_name: str
    start_date: date
    end_date: date
    total_trades: int
    win_rate: float
    profit_factor: float
    max_drawdown: float
    sharpe_ratio: float
    net_pnl: float

    class Config:
        from_attributes = True
